// API client for the Cloud Refactor Agent backend
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for repository operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Function to initiate a code snippet migration
export const migrateCodeSnippet = async ({ code, language, services, cloudProvider }) => {
  try {
    const response = await apiClient.post('/api/migrate', {
      code,
      language,
      services,
      cloud_provider: cloudProvider,
    });
    return response.data;
  } catch (error) {
    console.error('Migration error:', error);
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
    throw new Error(error.response?.data?.detail || error.message || 'Repository analysis failed');
  }
};

// Function to migrate a repository
export const migrateRepository = async ({ repositoryId, services, createPR = false, branchName = null, runTests = false }) => {
  try {
    const response = await apiClient.post(`/api/repository/${repositoryId}/migrate`, {
      services,
      create_pr: createPR,
      branch_name: branchName,
      run_tests: runTests,
    });
    return response.data;
  } catch (error) {
    console.error('Repository migration error:', error);
    throw new Error(error.response?.data?.detail || error.message || 'Repository migration failed');
  }
};

// Function to get migration status (for polling)
export const getMigrationStatus = async (migrationId) => {
  try {
    // Use a longer timeout for status polling since refactoring can take time
    const response = await axios.get(`${API_BASE_URL}/api/migration/${migrationId}`, {
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
