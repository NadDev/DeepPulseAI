/**
 * Auth Service - Backend API Integration
 * ========================================
 * Communicates with backend /api/auth endpoints for authentication
 * Uses JWT tokens stored in localStorage
 * 
 * Version: 1.0.1 - Updated with password reset support
 */

import { config } from '../config';

// Use base URL without /api since endpoints are /api/auth/...
const API_BASE_URL = config.API_URL.replace('/api', '');

/**
 * Register a new user
 */
export const register = async (email, password, username) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        username: username || email.split('@')[0],
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `Registration failed: ${response.status}`);
    }

    // Store tokens in localStorage
    if (data.access_token) {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('token_type', data.token_type || 'bearer');
    }
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token);
    }

    return {
      user: data.user,
      access_token: data.access_token,
      refresh_token: data.refresh_token,
    };
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
};

/**
 * Login user
 */
export const login = async (email, password) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `Login failed: ${response.status}`);
    }

    // Store tokens in localStorage
    if (data.access_token) {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('token_type', data.token_type || 'bearer');
    }
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token);
    }

    return {
      user: data.user,
      access_token: data.access_token,
      refresh_token: data.refresh_token,
    };
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

/**
 * Logout user
 */
export const logout = async () => {
  try {
    const token = localStorage.getItem('access_token');
    
    // Call backend logout endpoint if token exists
    if (token) {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
    }

    // Clear localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_type');
  } catch (error) {
    console.error('Logout error:', error);
    // Still clear localStorage even if API call fails
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_type');
  }
};

/**
 * Get current user from localStorage/API
 */
export const getCurrentUser = async () => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      return null;
    }

    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      // Token may be expired, clear it
      if (response.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error('Error getting current user:', error);
    return null;
  }
};

/**
 * Refresh access token
 */
export const refreshAccessToken = async () => {
  try {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      throw new Error(data.detail || 'Token refresh failed');
    }

    // Store new tokens
    localStorage.setItem('access_token', data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token);
    }

    return data.access_token;
  } catch (error) {
    console.error('Token refresh error:', error);
    throw error;
  }
};

/**
 * Reset password - set a new password for existing users or forgot password
 */
export const resetPassword = async (email, newPassword) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/password-reset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        email,
        new_password: newPassword
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Password reset failed');
    }

    return data;
  } catch (error) {
    console.error('Password reset error:', error);
    throw error;
  }
};

/**
 * Get Authorization header for API requests
 */
export const getAuthHeader = () => {
  const token = localStorage.getItem('access_token');
  const tokenType = localStorage.getItem('token_type') || 'bearer';

  if (!token) {
    return null;
  }

  return {
    'Authorization': `${tokenType} ${token}`,
  };
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = () => {
  const token = localStorage.getItem('access_token');
  return !!token;
};
