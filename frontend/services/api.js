// =====================================================
// CRBOT - API Service Layer
// Centralized API calls for all frontend pages
// =====================================================

import { supabase } from '../src/services/supabaseClient';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8002';

// ===================== AUTHENTICATION HELPER =====================
async function getAuthHeaders() {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = { 'Content-Type': 'application/json' };
  
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`;
  }
  
  return headers;
}

// ===================== ERROR HANDLING =====================
class APIError extends Error {
  constructor(status, message, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function handleResponse(response) {
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new APIError(response.status, `API Error: ${response.statusText}`, data);
  }
  return response.json();
}

// ===================== PORTFOLIO ENDPOINTS =====================
export const portfolio = {
  // Get portfolio summary (KPIs)
  async getSummary() {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/portfolio/summary`, { headers });
    return handleResponse(response);
  },

  // Get trades with pagination
  async getTrades(limit = 20, offset = 0, status = null) {
    let url = `${API_BASE_URL}/api/trades?limit=${limit}&offset=${offset}`;
    if (status) url += `&status=${status}`;
    
    const headers = await getAuthHeaders();
    const response = await fetch(url, { headers });
    return handleResponse(response);
  },

  // Get equity curve data
  async getEquityCurve(days = 30) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/portfolio/equity-curve?days=${days}`, { headers });
    return handleResponse(response);
  },
};

// ===================== BOTS ENDPOINTS =====================
export const bots = {
  // Get all bots
  async getList() {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/list`, { headers });
    return handleResponse(response);
  },

  // Get specific bot details
  async getById(botId) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}`, { headers });
    return handleResponse(response);
  },

  // Get bot performance metrics
  async getPerformance(botId) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}/performance`, { headers });
    return handleResponse(response);
  },

  // Get available strategies
  async getStrategies() {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/strategies`, { headers });
    return handleResponse(response);
  },

  // Create a new bot
  async create(botData) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/create`, {
      method: 'POST',
      headers,
      body: JSON.stringify(botData),
    });
    return handleResponse(response);
  },

  // Update a bot
  async update(botId, botData) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(botData),
    });
    return handleResponse(response);
  },

  // Delete a bot
  async delete(botId) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}`, {
      method: 'DELETE',
      headers,
    });
    return handleResponse(response);
  },

  // Start a bot
  async start(botId) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}/start`, {
      method: 'POST',
      headers,
    });
    return handleResponse(response);
  },

  // Pause a bot
  async pause(botId) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}/pause`, {
      method: 'POST',
      headers,
    });
    return handleResponse(response);
  },

  // Stop a bot
  async stop(botId) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}/stop`, {
      method: 'POST',
      headers,
    });
    return handleResponse(response);
  },
};

// ===================== REPORTS ENDPOINTS =====================
export const reports = {
  // Get dashboard summary report
  async getDashboard() {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/reports/dashboard`, { headers });
    return handleResponse(response);
  },

  // Get detailed trades report
  async getTrades(limit = 50, days = 30) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/reports/trades?limit=${limit}&days=${days}`, { headers });
    return handleResponse(response);
  },

  // Get strategies comparison report
  async getStrategies() {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/reports/strategies`, { headers });
    return handleResponse(response);
  },

  // Get overall performance metrics
  async getPerformance() {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/api/reports/performance`, { headers });
    return handleResponse(response);
  },
};

// ===================== CRYPTO ENDPOINTS =====================
export const crypto = {
  // Get crypto prices
  async getPrices(symbol = null) {
    let url = `${API_BASE_URL}/api/crypto/prices`;
    if (symbol) url += `?symbol=${symbol}`;
    
    const response = await fetch(url);
    return handleResponse(response);
  },
};

// ===================== HEALTH CHECK =====================
export const health = {
  async check() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return response.ok;
    } catch {
      return false;
    }
  },
};

// ===================== UTILITY FUNCTIONS =====================
export function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value) {
  return `${(value).toFixed(2)}%`;
}

export function formatDate(date) {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

export default {
  portfolio,
  bots,
  reports,
  crypto,
  health,
  formatCurrency,
  formatPercent,
  formatDate,
};
