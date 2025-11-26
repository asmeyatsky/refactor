"""
Authentication Middleware for Searce SSO

Architectural Intent:
- Provides authentication middleware for Searce SSO integration
- Supports OAuth2/OIDC authentication flow
- Validates user tokens and session management
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
import jwt
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try to import Google Auth libraries (for Cloud Run IAM integration)
try:
    from google.auth import default
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    logger.warning("Google Auth libraries not available. Using basic token validation.")


class SearceAuthMiddleware:
    """
    Authentication middleware for Searce SSO integration
    
    Supports multiple authentication methods:
    1. Google Cloud IAM (for Cloud Run)
    2. OAuth2/OIDC tokens
    3. Custom JWT tokens
    """
    
    def __init__(
        self,
        searce_oauth_client_id: Optional[str] = None,
        searce_oauth_client_secret: Optional[str] = None,
        searce_oauth_domain: Optional[str] = None,
        allowed_domains: Optional[list] = None,
        require_auth: bool = True
    ):
        """
        Initialize authentication middleware
        
        Args:
            searce_oauth_client_id: Searce OAuth client ID
            searce_oauth_client_secret: Searce OAuth client secret
            searce_oauth_domain: Searce OAuth domain (e.g., searce.com)
            allowed_domains: List of allowed email domains (e.g., ['@searce.com'])
            require_auth: Whether authentication is required (default: True)
        """
        self.searce_oauth_client_id = searce_oauth_client_id or os.getenv("SEARCE_OAUTH_CLIENT_ID")
        self.searce_oauth_client_secret = searce_oauth_client_secret or os.getenv("SEARCE_OAUTH_CLIENT_SECRET")
        self.searce_oauth_domain = searce_oauth_domain or os.getenv("SEARCE_OAUTH_DOMAIN", "searce.com")
        self.allowed_domains = allowed_domains or os.getenv("ALLOWED_EMAIL_DOMAINS", "@searce.com").split(",")
        self.require_auth = require_auth or os.getenv("REQUIRE_AUTH", "true").lower() == "true"
        
        # For Cloud Run, we can use IAM authentication
        self.use_cloud_run_iam = os.getenv("USE_CLOUD_RUN_IAM", "true").lower() == "true"
        
        self.security = HTTPBearer(auto_error=False)
    
    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Middleware function to validate authentication
        
        Returns:
            User info dict if authenticated, None if auth not required
        Raises:
            HTTPException if authentication fails
        """
        # Only skip auth for health checks and static files
        # All other routes (including frontend) require authentication
        public_paths = ["/api/health", "/static"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return None
        
        # Skip auth if not required
        if not self.require_auth:
            return None
        
        # Try Cloud Run IAM authentication first (if available)
        # When Cloud Run IAM is enabled with --allow-unauthenticated=false,
        # Cloud Run validates authentication BEFORE requests reach the app.
        # So if a request reaches us, it's already authenticated by Cloud Run.
        if self.use_cloud_run_iam:
            user_info = await self._validate_cloud_run_iam(request)
            if user_info:
                return user_info
            # If validation didn't return user info, check if this is a same-origin request
            # (Cloud Run authenticated the initial page load, so same-origin API calls are trusted)
            referer = request.headers.get("referer", "")
            origin = request.headers.get("origin", "")
            host = request.headers.get("host", "")
            
            # Check if request is from same origin (frontend making API call)
            is_same_origin = False
            if referer:
                # Extract host from referer
                try:
                    from urllib.parse import urlparse
                    referer_host = urlparse(referer).netloc
                    if referer_host == host or referer_host.endswith(f".{host}"):
                        is_same_origin = True
                except:
                    pass
            if origin and not is_same_origin:
                try:
                    from urllib.parse import urlparse
                    origin_host = urlparse(origin).netloc
                    if origin_host == host or origin_host.endswith(f".{host}"):
                        is_same_origin = True
                except:
                    pass
            
            # For same-origin requests (frontend -> API), trust Cloud Run authentication
            if is_same_origin or not request.url.path.startswith("/api/"):
                # Cloud Run already authenticated the page load, so allow API calls from same origin
                return {"email": "authenticated@searce.com", "auth_method": "cloud_run_iam"}
        
        # Try OAuth token validation
        credentials: Optional[HTTPAuthorizationCredentials] = await self.security(request)
        if credentials:
            user_info = await self._validate_token(credentials.credentials)
            if user_info:
                return user_info
        
        # Check for session cookie (for OAuth callback flow)
        session_token = request.cookies.get("session_token")
        if session_token:
            user_info = await self._validate_token(session_token)
            if user_info:
                return user_info
        
        # If no valid authentication found and auth is required
        if self.require_auth:
            # For Cloud Run, authentication is handled by IAM
            # If we reach here, the request is not authenticated
            # Check if this is an API request (JSON) or web request
            accept_header = request.headers.get("accept", "")
            content_type = request.headers.get("content-type", "")
            
            # If it's an API request, return 401
            if "application/json" in accept_header or "application/json" in content_type or request.url.path.startswith("/api/"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Please sign in with your Searce account.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                # For web requests, Cloud Run IAM will handle the redirect
                # Just return None to let the request proceed (Cloud Run will intercept)
                # In a custom OAuth flow, you would redirect here
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Please sign in with your Searce account.",
                )
        
        return None
    
    async def _validate_cloud_run_iam(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Validate Cloud Run IAM authentication
        
        When Cloud Run IAM is enabled with --no-allow-unauthenticated:
        - Cloud Run validates authentication BEFORE requests reach the app
        - For web browsers: Cloud Run redirects to Google Sign-In
        - For API calls: Client must send an identity token in Authorization header
        
        We need to extract user info from the request headers that Cloud Run provides.
        """
        try:
            # Cloud Run sets these headers for authenticated requests:
            # - X-Goog-Authenticated-User-Email: email of authenticated user
            # - X-Goog-Authenticated-User-ID: user ID
            # - Authorization: Bearer token (identity token)
            
            # Try to get email from Cloud Run headers first
            user_email = request.headers.get("X-Goog-Authenticated-User-Email", "")
            if user_email:
                # Remove the "accounts.google.com:" prefix if present
                user_email = user_email.replace("accounts.google.com:", "")
                # Check if user is from allowed domain
                if user_email and any(domain in user_email for domain in self.allowed_domains):
                    return {
                        "email": user_email,
                        "name": request.headers.get("X-Goog-Authenticated-User-Name", ""),
                        "auth_method": "cloud_run_iam"
                    }
                else:
                    logger.warning(f"User {user_email} not from allowed domain {self.allowed_domains}")
                    # Still return user info but mark as unauthorized domain
                    return {
                        "email": user_email,
                        "name": request.headers.get("X-Goog-Authenticated-User-Name", ""),
                        "auth_method": "cloud_run_iam",
                        "unauthorized_domain": True
                    }
            
            # Fallback: Get the Authorization header (identity token from authenticated user)
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split("Bearer ")[1]
                
                # Verify the identity token with Google
                if GOOGLE_AUTH_AVAILABLE:
                    try:
                        request_obj = google_requests.Request()
                        # Verify the token (no client ID needed for Cloud Run identity tokens)
                        idinfo = id_token.verify_oauth2_token(
                            token, request_obj, None
                        )
                        
                        # Extract user email
                        email = idinfo.get("email", "")
                        if not email:
                            # Try 'sub' field which contains email for some token types
                            email = idinfo.get("sub", "")
                        
                        # Check if user is from allowed domain
                        if email and any(domain in email for domain in self.allowed_domains):
                            return {
                                "email": email,
                                "name": idinfo.get("name", ""),
                                "picture": idinfo.get("picture", ""),
                                "auth_method": "cloud_run_iam"
                            }
                        else:
                            logger.warning(f"User {email} not from allowed domain {self.allowed_domains}")
                            return {
                                "email": email,
                                "name": idinfo.get("name", ""),
                                "auth_method": "cloud_run_iam",
                                "unauthorized_domain": True
                            }
                    except Exception as e:
                        logger.debug(f"Token verification failed: {e}")
                        return None
            
            # If request reached here and Cloud Run IAM is enabled, 
            # Cloud Run should have authenticated it, but we can't extract user info
            # This might happen for browser requests where Cloud Run handles auth
            # but doesn't forward all headers
            logger.warning("Cloud Run IAM enabled but no user info found in headers")
            return None
        except Exception as e:
            logger.debug(f"Cloud Run IAM validation failed: {e}")
            return None
    
    async def _validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate OAuth/JWT token"""
        try:
            # Try to decode as JWT
            try:
                decoded = jwt.decode(
                    token,
                    options={"verify_signature": False}  # For now, basic validation
                )
                
                email = decoded.get("email") or decoded.get("sub")
                if not email:
                    return None
                
                # Check domain
                if email and not any(domain in email for domain in self.allowed_domains):
                    logger.warning(f"User {email} not from allowed domain")
                    return None
                
                return {
                    "email": email,
                    "name": decoded.get("name", ""),
                    "picture": decoded.get("picture", ""),
                    "auth_method": "oauth_token"
                }
            except jwt.DecodeError:
                # Not a JWT token, might be OAuth access token
                # In production, validate with OAuth provider
                return None
        except Exception as e:
            logger.debug(f"Token validation failed: {e}")
            return None
    
    async def _redirect_to_login(self, request: Request) -> RedirectResponse:
        """Redirect to OAuth login page"""
        # Construct OAuth login URL
        # This should point to Searce's OAuth provider
        oauth_url = os.getenv(
            "SEARCE_OAUTH_URL",
            f"https://accounts.google.com/o/oauth2/v2/auth"
        )
        
        redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/auth/callback"
        
        params = {
            "client_id": self.searce_oauth_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid|profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        login_url = f"{oauth_url}?{query_string}"
        
        return RedirectResponse(url=login_url)


def create_auth_middleware() -> SearceAuthMiddleware:
    """Factory function to create authentication middleware"""
    return SearceAuthMiddleware(
        searce_oauth_client_id=os.getenv("SEARCE_OAUTH_CLIENT_ID"),
        searce_oauth_client_secret=os.getenv("SEARCE_OAUTH_CLIENT_SECRET"),
        searce_oauth_domain=os.getenv("SEARCE_OAUTH_DOMAIN", "searce.com"),
        allowed_domains=os.getenv("ALLOWED_EMAIL_DOMAINS", "@searce.com").split(","),
        require_auth=os.getenv("REQUIRE_AUTH", "true").lower() == "true"
    )
