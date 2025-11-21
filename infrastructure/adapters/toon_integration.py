"""
Toon Format Integration for Gemini API

Architectural Intent:
- Integrates TOON format for token optimization in Gemini API calls
- Converts structured data to TOON format before sending to Gemini
- Parses TOON responses from Gemini back to Python structures
"""

from typing import Any, Dict, List
from infrastructure.adapters.toon_serializer import ToonSerializer, to_toon, from_toon


class ToonGeminiIntegration:
    """
    Integration layer for using TOON format with Gemini API
    """
    
    @staticmethod
    def prepare_prompt_with_toon(prompt: str, structured_data: Dict[str, Any] = None) -> str:
        """
        Prepare prompt with TOON-formatted structured data
        
        Args:
            prompt: Base prompt text
            structured_data: Optional structured data to include in TOON format
            
        Returns:
            Enhanced prompt with TOON data
        """
        if not structured_data:
            return prompt
        
        toon_data = to_toon(structured_data)
        enhanced_prompt = f"""{prompt}

Structured Data (TOON format - optimized for tokens):
{toon_data}

Use TOON format in your response for any structured data to minimize token usage."""
        
        return enhanced_prompt
    
    @staticmethod
    def format_analysis_for_toon(analysis: Dict[str, Any]) -> str:
        """
        Format analysis data in TOON format for Gemini
        
        Args:
            analysis: Analysis dictionary
            
        Returns:
            TOON-formatted string
        """
        return to_toon(analysis)
    
    @staticmethod
    def format_service_mappings_for_toon(mappings: List[Dict[str, str]]) -> str:
        """
        Format service mappings in TOON tabular format (TOON's strength)
        
        Args:
            mappings: List of service mapping dictionaries
            
        Returns:
            TOON tabular format string
        """
        return to_toon(mappings)
    
    @staticmethod
    def parse_toon_response(response_text: str) -> Any:
        """
        Parse TOON-formatted response from Gemini
        
        Args:
            response_text: Response text that may contain TOON format
            
        Returns:
            Parsed Python data structure
        """
        # Check if response contains TOON format indicators
        if '|' in response_text and '\n' in response_text:
            # Likely TOON format
            try:
                return from_toon(response_text)
            except:
                # Fallback to text extraction
                return response_text
        
        return response_text
    
    @staticmethod
    def optimize_prompt_tokens(prompt: str, data: Dict[str, Any]) -> str:
        """
        Optimize prompt by converting structured data to TOON format
        
        Args:
            prompt: Original prompt
            data: Structured data to include
            
        Returns:
            Optimized prompt with TOON data
        """
        # Extract structured parts and convert to TOON
        toon_parts = []
        
        # Convert common structured data patterns
        if 'services' in data:
            toon_parts.append(f"Services: {to_toon(data['services'])}")
        if 'mappings' in data:
            toon_parts.append(f"Mappings:\n{to_toon(data['mappings'])}")
        if 'config' in data:
            toon_parts.append(f"Config:\n{to_toon(data['config'])}")
        
        if toon_parts:
            optimized = f"""{prompt}

{chr(10).join(toon_parts)}

Note: Data above is in TOON format for token optimization."""
            return optimized
        
        return prompt
