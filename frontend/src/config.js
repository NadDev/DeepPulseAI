// Configuration - reads from environment variables
// For production, use Railway API URL
// NEVER commit real credentials - always use environment variables
const isDev = import.meta.env.MODE === 'development';

// Allow override via VITE_API_URL for staging/preview environments
const getApiUrl = () => {
  // 1. Check for explicit override (Vercel Preview with staging backend)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // 2. Dev mode -> localhost
  if (isDev) {
    return 'http://127.0.0.1:8002/api';
  }
  
  // 3. Production -> Railway production backend
  return 'https://deeppulseai-production.up.railway.app/api';
};

export const config = {
  API_URL: getApiUrl(),
  SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL,
  SUPABASE_KEY: import.meta.env.VITE_SUPABASE_ANON_KEY,
};

// Warn if Supabase is not configured
if (!config.SUPABASE_URL || !config.SUPABASE_KEY) {
  console.warn('⚠️ Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY environment variables.');
}

console.log('Config loaded:', {
  API_URL: config.API_URL,
  MODE: import.meta.env.MODE,
  SUPABASE_URL: config.SUPABASE_URL ? 'set' : 'NOT SET',
});
