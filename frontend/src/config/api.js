/**
 * API Configuration
 * Manages backend API endpoint based on environment
 */

// Get backend URL from environment or use relative path as fallback
const getBackendUrl = () => {
  // Check for environment variable first (set in Vercel)
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  
  // Development: use localhost
  if (process.env.NODE_ENV === 'development') {
    return 'http://localhost:8000';
  }
  
  // Production: try to use Railway backend URL or relative path
  // You MUST set REACT_APP_API_URL in Vercel environment variables!
  // For now, return relative path as fallback
  return '';
};

export const API_BASE_URL = getBackendUrl();

export const apiClient = {
  get: (endpoint) => {
    const url = API_BASE_URL ? `${API_BASE_URL}${endpoint}` : endpoint;
    console.log(`🔗 GET ${url}`);
    return url;
  },
  
  post: (endpoint) => {
    const url = API_BASE_URL ? `${API_BASE_URL}${endpoint}` : endpoint;
    console.log(`🔗 POST ${url}`);
    return url;
  }
};

export default API_BASE_URL;
