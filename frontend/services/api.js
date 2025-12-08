// =====================================================
// CRBOT - API Service Layer
// Centralized API calls for all frontend pages
// =====================================================

const API_BASE_URL = 'http://127.0.0.1:8001';

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
    const response = await fetch(`${API_BASE_URL}/api/portfolio/summary`);
    return handleResponse(response);
  },

  // Get trades with pagination
  async getTrades(limit = 20, offset = 0, status = null) {
    let url = `${API_BASE_URL}/api/trades?limit=${limit}&offset=${offset}`;
    if (status) url += `&status=${status}`;
    
    const response = await fetch(url);
    return handleResponse(response);
  },

  // Get equity curve data
  async getEquityCurve(days = 30) {
    const response = await fetch(`${API_BASE_URL}/api/portfolio/equity-curve?days=${days}`);
    return handleResponse(response);
  },
};

// ===================== BOTS ENDPOINTS =====================
export const bots = {
  // Get all bots
  async getList() {
    const response = await fetch(`${API_BASE_URL}/api/bots/list`);
    return handleResponse(response);
  },

  // Get specific bot details
  async getById(botId) {
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}`);
    return handleResponse(response);
  },

  // Get bot performance metrics
  async getPerformance(botId) {
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}/performance`);
    return handleResponse(response);
  },

  // Start a bot
  async start(botId) {
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  },

  // Pause a bot
  async pause(botId) {
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}/pause`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  },

  // Stop a bot
  async stop(botId) {
    const response = await fetch(`${API_BASE_URL}/api/bots/${botId}/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  },
};

// ===================== REPORTS ENDPOINTS =====================
export const reports = {
  // Get dashboard summary report
  async getDashboard() {
    const response = await fetch(`${API_BASE_URL}/api/reports/dashboard`);
    return handleResponse(response);
  },

  // Get detailed trades report
  async getTrades(limit = 50, days = 30) {
    const response = await fetch(`${API_BASE_URL}/api/reports/trades?limit=${limit}&days=${days}`);
    return handleResponse(response);
  },

  // Get strategies comparison report
  async getStrategies() {
    const response = await fetch(`${API_BASE_URL}/api/reports/strategies`);
    return handleResponse(response);
  },

  // Get overall performance metrics
  async getPerformance() {
    const response = await fetch(`${API_BASE_URL}/api/reports/performance`);
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
