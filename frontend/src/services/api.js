import axios from 'axios';
import { config } from '../config';
import { supabase } from './supabaseClient';

const API_BASE_URL = config.API_URL + '/api';

// Create axios instance with auth interceptor
const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

// Add JWT token to all requests
apiClient.interceptors.request.use(async (req) => {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      req.headers.Authorization = `Bearer ${session.access_token}`;
    }
  } catch (error) {
    console.error('Error getting session:', error);
  }
  return req;
});

export const cryptoAPI = {
  // ML Engine Endpoints (ARCH 2)
  trainModel: async (symbol = 'BTCUSDT', days = 365) => {
    const response = await apiClient.post(`/ml/train`, null, {
      params: { symbol, days }
    });
    return response.data;
  },

  getTrainingStatus: async () => {
    const response = await apiClient.get(`/ml/status`);
    return response.data;
  },

  getPredictions: async (symbol) => {
    const response = await apiClient.get(`/ml/predict/${symbol}`);
    return response.data;
  },

  getSignals: async (symbol) => {
    const response = await apiClient.get(`/ml/signals/${symbol}`);
    return response.data;
  },

  getPatterns: async (symbol) => {
    const response = await apiClient.get(`/ml/patterns/${symbol}`);
    return response.data;
  },

  // Trades
  getTrades: async (limit = 10) => {
    const response = await apiClient.get(`/trades/list`, {
      params: { limit }
    });
    return response.data;
  },

  // Bots
  getBots: async () => {
    const response = await apiClient.get(`/bots/list`);
    return response.data;
  },

  // Reports
  getEquityCurve: async (days = 30) => {
    const response = await apiClient.get(`/reports/equity-curve`, {
      params: { days }
    });
    return response.data;
  },

  // Get cryptocurrency prices (Top Markets)
  getPrices: async () => {
    const response = await apiClient.get(`/crypto/markets`);
    return response.data;
  },

  // Get detailed crypto data (Price, High, Low, Volume)
  getCryptoData: async (symbol) => {
    const response = await apiClient.get(`/crypto/${symbol}/data`);
    return response.data;
  },

  // Get crypto analysis (Trend, Sentiment, Reputation)
  getCryptoAnalysis: async (symbol) => {
    const response = await apiClient.get(`/crypto/${symbol}/analysis`);
    return response.data;
  },

  // Search cryptocurrencies
  searchCrypto: async (query) => {
    const response = await apiClient.get(`/crypto/search`, {
      params: { q: query }
    });
    return response.data;
  },

  // Get crypto details
  getCryptoDetails: async (coinId) => {
    const response = await apiClient.get(`/crypto/${coinId}`);
    return response.data;
  },

  // Get chart data
  getChartData: async (coinId, period = '7d') => {
    const response = await apiClient.get(`/crypto/${coinId}/chart`, {
      params: { period }
    });
    return response.data;
  },

  // Portfolio operations
  getPortfolio: async (userId = 'default') => {
    const response = await apiClient.get(`/portfolio/summary`, {
      params: { user_id: userId }
    });
    return response.data;
  },

  addToPortfolio: async (portfolioItem) => {
    const response = await apiClient.post(`/portfolio`, portfolioItem);
    return response.data;
  },

  removeFromPortfolio: async (itemId, userId = 'default') => {
    const response = await apiClient.delete(`/portfolio/${itemId}`, {
      params: { user_id: userId }
    });
    return response.data;
  },

  updatePortfolioItem: async (itemId, data, userId = 'default') => {
    const response = await apiClient.put(`/portfolio/${itemId}`, data, {
      params: { user_id: userId }
    });
    return response.data;
  },

  // ============ ARCH 1: TECHNICAL INDICATORS ============
  getRSI: async (symbol, period = 14) => {
    const response = await apiClient.get(`/indicators/${symbol}/rsi`, {
      params: { period }
    });
    return response.data;
  },

  getMACD: async (symbol) => {
    const response = await apiClient.get(`/indicators/${symbol}/macd`);
    return response.data;
  },

  getBollingerBands: async (symbol, period = 20) => {
    const response = await apiClient.get(`/indicators/${symbol}/bollinger`, {
      params: { period }
    });
    return response.data;
  },

  getEMA: async (symbol, period = 50) => {
    const response = await apiClient.get(`/indicators/${symbol}/ema`, {
      params: { period }
    });
    return response.data;
  },

  getAllIndicators: async (symbol) => {
    const response = await apiClient.get(`/indicators/${symbol}/all`);
    return response.data;
  },

  // ============ ARCH 1: SENTIMENT ANALYSIS ============
  getSentiment: async (symbol) => {
    const response = await apiClient.get(`/sentiment/${symbol}`);
    return response.data;
  },

  getFearGreedIndex: async (symbol = 'BTC') => {
    const response = await apiClient.get(`/sentiment/${symbol}/fear-greed`);
    return response.data;
  },

  getWhaleAlerts: async (symbol) => {
    const response = await apiClient.get(`/sentiment/${symbol}/whale-alerts`);
    return response.data;
  },

  // ============ SPRINT 2: ADVANCED TECHNICAL ANALYSIS ============
  getElliottWave: async (symbol) => {
    const response = await apiClient.get(`/indicators/${symbol}/elliott-wave`);
    return response.data;
  },

  getFibonacci: async (symbol) => {
    const response = await apiClient.get(`/indicators/${symbol}/fibonacci`);
    return response.data;
  },

  getIchimoku: async (symbol) => {
    const response = await apiClient.get(`/indicators/${symbol}/ichimoku`);
    return response.data;
  },

  getAdvancedAnalysis: async (symbol) => {
    const response = await apiClient.get(`/indicators/${symbol}/advanced`);
    return response.data;
  },

  // ============ SPRINT 3: PORTFOLIO MANAGEMENT ============
  getPortfolioSummary: async () => {
    const response = await apiClient.get(`/portfolio/summary`);
    return response.data;
  },

  getPositions: async () => {
    const response = await apiClient.get(`/portfolio/positions`);
    return response.data;
  },

  getTrades: async (limit = 20, offset = 0) => {
    const response = await apiClient.get(`/trades`, {
      params: { limit, offset }
    });
    return response.data;
  },

  createOrder: async (orderData) => {
    const response = await apiClient.post(`/portfolio/orders`, orderData);
    return response.data;
  },

  // ============ SPRINT 4: BOT MANAGEMENT ============
  getStrategies: async () => {
    const response = await apiClient.get(`/bots/strategies`);
    return response.data;
  },

  createBot: async (botData) => {
    const response = await apiClient.post(`/bots/create`, botData);
    return response.data;
  },

  updateBot: async (botId, botData) => {
    const response = await apiClient.put(`/bots/${botId}`, botData);
    return response.data;
  },

  deleteBot: async (botId) => {
    const response = await apiClient.delete(`/bots/${botId}`);
    return response.data;
  },

  getBot: async (botId) => {
    const response = await apiClient.get(`/bots/${botId}`);
    return response.data;
  },

  startBot: async (botId) => {
    const response = await apiClient.post(`/bots/${botId}/start`);
    return response.data;
  },

  pauseBot: async (botId) => {
    const response = await apiClient.post(`/bots/${botId}/pause`);
    return response.data;
  },

  stopBot: async (botId) => {
    const response = await apiClient.post(`/bots/${botId}/stop`);
    return response.data;
  }
};
