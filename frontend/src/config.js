// Configuration - reads from environment variables
// For production, use Railway API URL
// NEVER commit real credentials - always use environment variables
const isDev = import.meta.env.MODE === 'development';

export const config = {
  API_URL: isDev 
    ? 'http://127.0.0.1:8002/api'
    : 'https://deeppulseai-production.up.railway.app/api',
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
