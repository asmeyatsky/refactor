// API client for the Cloud Refactor Agent backend
import axios from 'axios';

// Use relative URLs by default (works for both dev and production)
// Set REACT_APP_API_BASE_URL environment variable to override (e.g., for local dev)
// In development, proxy in package.json will forward /api/* requests to http://localhost:8000
// Default to localhost:8000 for local development if not set
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 
  (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');

// Log API base URL for debugging
if (process.env.NODE_ENV === 'development') {
  console.log('API Base URL:', API_BASE_URL || '(using proxy)');
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 minutes for long-running repository operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Function to initiate a code snippet migration
export const migrateCodeSnippet = async ({ code, language, services, cloudProvider = 'aws' }) => {
  try {
    const response = await apiClient.post('/api/migrate', {
      code,
      language,
      services,
      cloud_provider: cloudProvider, // 'aws' or 'azure'
    });
    return response.data;
  } catch (error) {
    console.error('Migration error:', error);
    // Provide more detailed error messages for network issues
    if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
      throw new Error('Cannot connect to API server. Please ensure the API server is running on http://localhost:8000');
    }
    throw new Error(error.response?.data?.detail || error.message || 'Migration failed');
  }
};

// Function to analyze a repository
export const analyzeRepository = async (repositoryUrl, branch = 'main', token = null) => {
  try {
    const response = await apiClient.post('/api/repository/analyze', {
      repository_url: repositoryUrl,
      branch,
      token,
    });
    return response.data;
  } catch (error) {
    console.error('Repository analysis error:', error);
    // Provide more detailed error messages for network issues
    if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
      throw new Error('Cannot connect to API server. Please ensure the API server is running on http://localhost:8000');
    }
    throw new Error(error.response?.data?.detail || error.message || 'Repository analysis failed');
  }
};

// Function to migrate a repository
export const migrateRepository = async ({ repositoryId, services, createPR = false, branchName = null, runTests = false }) => {
  try {
    // Use apiClient with extended timeout for repository migration (10 minutes)
    // Repository migrations with many services can take a long time
    const response = await apiClient.post(`/api/repository/${repositoryId}/migrate`, {
      services,
      create_pr: createPR,
      branch_name: branchName,
      run_tests: runTests,
    });
    return response.data;
  } catch (error) {
    console.error('Repository migration error:', error);
    // Provide more helpful error messages for timeout
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      throw new Error('Repository migration timed out. This can happen when migrating many services. Please try with fewer services or wait a bit longer.');
    }
    throw new Error(error.response?.data?.detail || error.message || 'Repository migration failed');
  }
};

// Function to get migration status (for polling)
export const getMigrationStatus = async (migrationId) => {
  try {
    // Use a longer timeout for status polling since refactoring can take time
    const response = await apiClient.get(`/api/migration/${migrationId}`, {
      timeout: 10000, // 10 seconds per poll request
    });
    return response.data;
  } catch (error) {
    console.error('Get migration status error:', error);
    throw error;
  }
};

// Function to get supported services
export const getSupportedServices = async () => {
  try {
    const response = await apiClient.get('/api/services');
    return response.data;
  } catch (error) {
    console.error('Get services error:', error);
    throw error;
  }
};

// Function to list analyzed repositories
export const listRepositories = async () => {
  try {
    const response = await apiClient.get('/api/repository/list');
    return response.data;
  } catch (error) {
    console.error('List repositories error:', error);
    throw error;
  }
};
