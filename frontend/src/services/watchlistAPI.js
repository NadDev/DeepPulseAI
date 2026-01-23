/**
 * Watchlist API Service
 * Manages persistent watchlist in Railway PostgreSQL database
 * Uses Supabase JWT for authentication
 */

import { supabase } from './supabaseClient';
import { config } from '../config';

const API_BASE_URL = config.API_URL + '/api';

// Get auth headers with Supabase JWT token
const getAuthHeaders = async () => {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    throw new Error('Not authenticated');
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`
  };
};

export const watchlistAPI = {
  // Get user's watchlist
  getWatchlist: async (activeOnly = false) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE_URL}/watchlist?active_only=${activeOnly}`,
        { headers }
      );
      if (!response.ok) throw new Error('Failed to fetch watchlist');
      return response.json();
    } catch (error) {
      console.error('Error fetching watchlist:', error);
      throw error;
    }
  },

  // Add single symbol to watchlist
  addSymbol: async (symbol, notes = null, priority = 0) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE_URL}/watchlist`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ symbol, notes, priority })
        }
      );
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add symbol');
      }
      return response.json();
    } catch (error) {
      console.error('Error adding symbol:', error);
      throw error;
    }
  },

  // Add multiple symbols at once
  bulkAdd: async (symbols) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE_URL}/watchlist/bulk`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ symbols })
        }
      );
      if (!response.ok) throw new Error('Failed to add symbols');
      return response.json();
    } catch (error) {
      console.error('Error bulk adding symbols:', error);
      throw error;
    }
  },

  // Remove symbol from watchlist
  removeSymbol: async (itemId) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE_URL}/watchlist/${itemId}`,
        {
          method: 'DELETE',
          headers
        }
      );
      if (!response.ok) throw new Error('Failed to remove symbol');
      return response.json();
    } catch (error) {
      console.error('Error removing symbol:', error);
      throw error;
    }
  },

  // Update watchlist item
  updateItem: async (itemId, updates) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE_URL}/watchlist/${itemId}`,
        {
          method: 'PUT',
          headers,
          body: JSON.stringify(updates)
        }
      );
      if (!response.ok) throw new Error('Failed to update item');
      return response.json();
    } catch (error) {
      console.error('Error updating item:', error);
      throw error;
    }
  },

  // Toggle item active status
  toggleItem: async (itemId) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE_URL}/watchlist/${itemId}/toggle`,
        {
          method: 'POST',
          headers
        }
      );
      if (!response.ok) throw new Error('Failed to toggle item');
      return response.json();
    } catch (error) {
      console.error('Error toggling item:', error);
      throw error;
    }
  },

  // Get popular symbols
  getPopular: async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(
        `${API_BASE_URL}/watchlist/popular`,
        { headers }
      );
      if (!response.ok) throw new Error('Failed to fetch popular symbols');
      return response.json();
    } catch (error) {
      console.error('Error fetching popular symbols:', error);
      throw error;
    }
  }
};
