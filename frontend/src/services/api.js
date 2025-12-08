import axios from 'axios';

const API_BASE_URL = '/api';

export const cryptoAPI = {
  // Get cryptocurrency prices
  getPrices: async () => {
    const response = await axios.get(`${API_BASE_URL}/crypto/prices`);
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
  getChartData: async (coinId, days = 7) => {
    const response = await axios.get(`${API_BASE_URL}/crypto/${coinId}/chart`, {
      params: { days }
    });
    return response.data;
  },

  // Portfolio operations
  getPortfolio: async (userId = 'default') => {
    const response = await axios.get(`${API_BASE_URL}/portfolio`, {
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
  }
};
