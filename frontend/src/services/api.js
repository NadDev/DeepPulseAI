import axios from 'axios';

const API_BASE_URL = 'http://localhost:8002/api'; // Updated to match backend port and prefix

export const cryptoAPI = {
  // ML Engine Endpoints (ARCH 2)
  trainModel: async (symbol = 'BTCUSDT', days = 365) => {
    const response = await axios.post(`${API_BASE_URL}/ml/train`, null, {
      params: { symbol, days }
    });
    return response.data;
  },

  getTrainingStatus: async () => {
    const response = await axios.get(`${API_BASE_URL}/ml/status`);
    return response.data;
  },

  getPredictions: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/ml/predict/${symbol}`);
    return response.data;
  },

  getSignals: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/ml/signals/${symbol}`);
    return response.data;
  },

  getPatterns: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/ml/patterns/${symbol}`);
    return response.data;
  },

  // Trades
  getTrades: async (limit = 10) => {
    const response = await axios.get(`${API_BASE_URL}/trades/list`, {
      params: { limit }
    });
    return response.data;
  },

  // Bots
  getBots: async () => {
    const response = await axios.get(`${API_BASE_URL}/bots/list`);
    return response.data;
  },

  // Reports
  getEquityCurve: async (days = 30) => {
    const response = await axios.get(`${API_BASE_URL}/reports/equity-curve`, {
      params: { days }
    });
    return response.data;
  },

  // Get cryptocurrency prices (Top Markets)
  getPrices: async () => {
    const response = await axios.get(`${API_BASE_URL}/crypto/markets`);
    return response.data;
  },

  // Get detailed crypto data (Price, High, Low, Volume)
  getCryptoData: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/crypto/${symbol}/data`);
    return response.data;
  },

  // Get crypto analysis (Trend, Sentiment, Reputation)
  getCryptoAnalysis: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/crypto/${symbol}/analysis`);
    return response.data;
  },

  // Search cryptocurrencies
  searchCrypto: async (query) => {
    const response = await axios.get(`${API_BASE_URL}/crypto/search`, {
      params: { q: query }
    });
    return response.data;
  },

  // Get crypto details
  getCryptoDetails: async (coinId) => {
    const response = await axios.get(`${API_BASE_URL}/crypto/${coinId}`);
    return response.data;
  },

  // Get chart data
  getChartData: async (coinId, period = '7d') => {
    const response = await axios.get(`${API_BASE_URL}/crypto/${coinId}/chart`, {
      params: { period }
    });
    return response.data;
  },

  // Portfolio operations
  getPortfolio: async (userId = 'default') => {
    const response = await axios.get(`${API_BASE_URL}/portfolio/summary`, {
      params: { user_id: userId }
    });
    return response.data;
  },

  addToPortfolio: async (portfolioItem) => {
    const response = await axios.post(`${API_BASE_URL}/portfolio`, portfolioItem);
    return response.data;
  },

  removeFromPortfolio: async (itemId, userId = 'default') => {
    const response = await axios.delete(`${API_BASE_URL}/portfolio/${itemId}`, {
      params: { user_id: userId }
    });
    return response.data;
  },

  updatePortfolioItem: async (itemId, data, userId = 'default') => {
    const response = await axios.put(`${API_BASE_URL}/portfolio/${itemId}`, data, {
      params: { user_id: userId }
    });
    return response.data;
  },

  // ============ ARCH 1: TECHNICAL INDICATORS ============
  getRSI: async (symbol, period = 14) => {
    const response = await axios.get(`${API_BASE_URL}/indicators/${symbol}/rsi`, {
      params: { period }
    });
    return response.data;
  },

  getMACD: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/indicators/${symbol}/macd`);
    return response.data;
  },

  getBollingerBands: async (symbol, period = 20) => {
    const response = await axios.get(`${API_BASE_URL}/indicators/${symbol}/bollinger`, {
      params: { period }
    });
    return response.data;
  },

  getEMA: async (symbol, period = 50) => {
    const response = await axios.get(`${API_BASE_URL}/indicators/${symbol}/ema`, {
      params: { period }
    });
    return response.data;
  },

  getAllIndicators: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/indicators/${symbol}/all`);
    return response.data;
  },

  // ============ ARCH 1: SENTIMENT ANALYSIS ============
  getSentiment: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/sentiment/${symbol}`);
    return response.data;
  },

  getFearGreedIndex: async (symbol = 'BTC') => {
    const response = await axios.get(`${API_BASE_URL}/sentiment/${symbol}/fear-greed`);
    return response.data;
  },

  getWhaleAlerts: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/sentiment/${symbol}/whale-alerts`);
    return response.data;
  },

  // ============ SPRINT 2: ADVANCED TECHNICAL ANALYSIS ============
  getElliottWave: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/indicators/${symbol}/elliott-wave`);
    return response.data;
  },

  getFibonacci: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/indicators/${symbol}/fibonacci`);
    return response.data;
  },

  getIchimoku: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/indicators/${symbol}/ichimoku`);
    return response.data;
  },

  getAdvancedAnalysis: async (symbol) => {
    const response = await axios.get(`${API_BASE_URL}/indicators/${symbol}/advanced`);
    return response.data;
  },

  // ============ SPRINT 3: PORTFOLIO MANAGEMENT ============
  getPortfolioSummary: async () => {
    const response = await axios.get(`${API_BASE_URL}/portfolio/summary`);
    return response.data;
  },

  getPositions: async () => {
    const response = await axios.get(`${API_BASE_URL}/portfolio/positions`);
    return response.data;
  },

  getTrades: async (limit = 20, offset = 0) => {
    const response = await axios.get(`${API_BASE_URL}/trades`, {
      params: { limit, offset }
    });
    return response.data;
  },

  createOrder: async (orderData) => {
    const response = await axios.post(`${API_BASE_URL}/portfolio/orders`, orderData);
    return response.data;
  },

  // ============ SPRINT 4: BOT MANAGEMENT ============
  getStrategies: async () => {
    const response = await axios.get(`${API_BASE_URL}/bots/strategies`);
    return response.data;
  },

  createBot: async (botData) => {
    const response = await axios.post(`${API_BASE_URL}/bots/create`, botData);
    return response.data;
  },

  updateBot: async (botId, botData) => {
    const response = await axios.put(`${API_BASE_URL}/bots/${botId}`, botData);
    return response.data;
  },

  deleteBot: async (botId) => {
    const response = await axios.delete(`${API_BASE_URL}/bots/${botId}`);
    return response.data;
  },

  getBot: async (botId) => {
    const response = await axios.get(`${API_BASE_URL}/bots/${botId}`);
    return response.data;
  },

  startBot: async (botId) => {
    const response = await axios.post(`${API_BASE_URL}/bots/${botId}/start`);
    return response.data;
  },

  pauseBot: async (botId) => {
    const response = await axios.post(`${API_BASE_URL}/bots/${botId}/pause`);
    return response.data;
  },

  stopBot: async (botId) => {
    const response = await axios.post(`${API_BASE_URL}/bots/${botId}/stop`);
    return response.data;
  }
};
