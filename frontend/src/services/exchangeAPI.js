/**
 * Exchange API Service
 * Handles all API calls for exchange/broker configuration
 */

import { config } from '../config';
import { supabase } from './supabaseClient';

const API_BASE_URL = config.API_URL + '/api';

// Helper to get auth headers
const getAuthHeaders = async () => {
  const { data: { session } } = await supabase.auth.getSession();
  return {
    'Authorization': session?.access_token ? `Bearer ${session.access_token}` : '',
    'Content-Type': 'application/json'
  };
};

export const exchangeAPI = {
  /**
   * Get list of supported exchanges with their features
   */
  getSupportedExchanges: async () => {
    try {
      const headers = await getAuthHeaders();
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
      const headers = await getAuthHeaders();
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
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/exchange/configs`, {
        method: 'POST',
        headers,
        body: JSON.stringify(configData)
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create exchange config');
      }
      return response.json();
    } catch (error) {
      console.error('Error creating exchange config:', error);
      throw error;
    }
  },

  /**
   * Update an existing exchange configuration
   */
  updateConfig: async (configId, configData) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/exchange/configs/${configId}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(configData)
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update exchange config');
      }
      return response.json();
    } catch (error) {
      console.error('Error updating exchange config:', error);
      throw error;
    }
  },

  /**
   * Delete an exchange configuration
   */
  deleteConfig: async (configId) => {
    try {
      const headers = await getAuthHeaders();
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
      const headers = await getAuthHeaders();
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
      const headers = await getAuthHeaders();
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
