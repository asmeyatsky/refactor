// API client for the Cloud Refactor Agent backend
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Function to initiate a migration
export const initiateMigration = async (code, language, services) => {
  try {
    const response = await apiClient.post('/api/migrate', {
      code,
      language,
      services,
    });
    return response.data;
  } catch (error) {
    console.error('Migration error:', error);
    throw error;
  }
};

// Function to get migration status
export const getMigrationStatus = async (migrationId) => {
  try {
    const response = await apiClient.get(`/api/migration/${migrationId}`);
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