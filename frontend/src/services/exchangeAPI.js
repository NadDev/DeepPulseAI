/**
 * Exchange API Service
 * Handles all API calls for exchange/broker configuration
 */

import { config } from '../config';

const API_BASE_URL = config.API_URL;

// Helper to get auth headers from localStorage JWT token
const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  return {
    'Authorization': token ? `Bearer ${token}` : '',
    'Content-Type': 'application/json'
  };
};

export const exchangeAPI = {
  /**
   * Get list of supported exchanges with their features
   */
  getSupportedExchanges: async () => {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/exchange/supported`, { headers });
      if (!response.ok) throw new Error('Failed to fetch supported exchanges');
      return response.json();
    } catch (error) {
      console.error('Error fetching supported exchanges:', error);
      throw error;
    }
  },

  /**
   * Get all exchange configurations for current user
   */
  getConfigs: async () => {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/exchange/configs`, { headers });
      if (!response.ok) throw new Error('Failed to fetch exchange configs');
      return response.json();
    } catch (error) {
      console.error('Error fetching exchange configs:', error);
      throw error;
    }
  },

  /**
   * Create a new exchange configuration
   */
  createConfig: async (configData) => {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/exchange/configs`, {
        method: 'POST',
        headers,
        body: JSON.stringify(configData)
      });
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to create exchange config');
        } catch (parseError) {
          throw new Error(`HTTP ${response.status}: Failed to create exchange config`);
        }
      }
      return response.json();
    } catch (error) {
      console.error('Error creating exchange config:', error);
      throw new Error(error.message || 'Failed to create exchange config');
    }
  },

  /**
   * Update an existing exchange configuration
   */
  updateConfig: async (configId, configData) => {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/exchange/configs/${configId}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(configData)
      });
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to update exchange config');
        } catch (parseError) {
          throw new Error(`HTTP ${response.status}: Failed to update exchange config`);
        }
      }
      return response.json();
    } catch (error) {
      console.error('Error updating exchange config:', error);
      throw new Error(error.message || 'Failed to update exchange config');
    }
  },

  /**
   * Delete an exchange configuration
   */
  deleteConfig: async (configId) => {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/exchange/configs/${configId}`, {
        method: 'DELETE',
        headers
      });
      if (!response.ok) throw new Error('Failed to delete exchange config');
      return response.json();
    } catch (error) {
      console.error('Error deleting exchange config:', error);
      throw error;
    }
  },

  /**
   * Test connection to an exchange
   */
  testConnection: async (testData) => {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/exchange/test-connection`, {
        method: 'POST',
        headers,
        body: JSON.stringify(testData)
      });
      if (!response.ok) throw new Error('Failed to test connection');
      return response.json();
    } catch (error) {
      console.error('Error testing connection:', error);
      throw error;
    }
  },

  /**
   * Toggle exchange active status
   */
  toggleActive: async (configId) => {
    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/exchange/configs/${configId}/toggle`, {
        method: 'POST',
        headers
      });
      if (!response.ok) throw new Error('Failed to toggle exchange status');
      return response.json();
    } catch (error) {
      console.error('Error toggling exchange status:', error);
      throw error;
    }
  }
};
