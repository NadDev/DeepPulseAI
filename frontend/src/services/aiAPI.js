/**
 * AI Agent API Service
 * Handles all API calls to the backend AI Agent endpoints
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

export const aiAPI = {
  // Status and General Info
  getStatus: async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/ai-agent/status`, { headers });
      if (!response.ok) throw new Error('Failed to fetch AI status');
      return response.json();
    } catch (error) {
      console.error('Error fetching AI status:', error);
      throw error;
    }
  },

  // Analysis
  analyzeMarket: async (symbol) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/ai-agent/analyze`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ symbol })
      });
      if (!response.ok) throw new Error('Failed to analyze market');
      return response.json();
    } catch (error) {
      console.error('Error analyzing market:', error);
      throw error;
    }
  },

  // Chat Interface
  chat: async (message) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/ai-agent/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message })
      });
      if (!response.ok) throw new Error('Failed to send chat message');
      return response.json();
    } catch (error) {
      console.error('Error in chat:', error);
      throw error;
    }
  },

  // Get Recommendations
  getRecommendations: async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/ai-agent/recommendations`, { headers });
      if (!response.ok) throw new Error('Failed to fetch recommendations');
      return response.json();
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      throw error;
    }
  },

  // Analyze Watchlist - NEW ENDPOINT
  analyzeWatchlist: async (limit = 10, minConfidence = 50) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE_URL}/ai-agent/analyze-watchlist?limit=${limit}&min_confidence=${minConfidence}`, 
        { 
          method: 'POST',
          headers 
        }
      );
      if (!response.ok) throw new Error('Failed to analyze watchlist');
      return response.json();
    } catch (error) {
      console.error('Error analyzing watchlist:', error);
      throw error;
    }
  },

  // Get Decision History
  getDecisionHistory: async (filters = {}) => {
    try {
      const headers = await getAuthHeaders();
      const params = new URLSearchParams();
      if (filters.symbol) params.append('symbol', filters.symbol);
      if (filters.action) params.append('action', filters.action);
      if (filters.executed !== undefined) params.append('executed', filters.executed);

      const url = `${API_BASE_URL}/ai-agent/decisions?${params}`;
      const response = await fetch(url, { headers });
      if (!response.ok) throw new Error('Failed to fetch decision history');
      return response.json();
    } catch (error) {
      console.error('Error fetching decision history:', error);
      throw error;
    }
  },

  // Get Decision Statistics
  getDecisionStats: async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/ai-agent/decisions/stats`, { headers });
      if (!response.ok) throw new Error('Failed to fetch decision stats');
      return response.json();
    } catch (error) {
      console.error('Error fetching decision stats:', error);
      throw error;
    }
  },

  // Get AI-managed Bots
  getActiveBots: async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/ai-agent/bots`, { headers });
      if (!response.ok) throw new Error('Failed to fetch active bots');
      return response.json();
    } catch (error) {
      console.error('Error fetching active bots:', error);
      throw error;
    }
  },

  // Toggle AI Mode
  toggleMode: async (mode) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/ai-agent/toggle`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ mode })
      });
      if (!response.ok) throw new Error('Failed to toggle AI mode');
      return response.json();
    } catch (error) {
      console.error('Error toggling AI mode:', error);
      throw error;
    }
  },

  // Get Configuration
  getConfig: async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/ai-agent/config`, { headers });
      if (!response.ok) throw new Error('Failed to fetch configuration');
      return response.json();
    } catch (error) {
      console.error('Error fetching config:', error);
      throw error;
    }
  },

  // Update Configuration
  updateConfig: async (configUpdates) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/ai-agent/config`, {
        method: 'POST',
        headers,
        body: JSON.stringify(configUpdates)
      });
      if (!response.ok) throw new Error('Failed to update configuration');
      return response.json();
    } catch (error) {
      console.error('Error updating config:', error);
      throw error;
    }
  }
};
