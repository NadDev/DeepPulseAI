// Configuration - reads from environment variables
export const config = {
  API_URL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8002',
  SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL || '',
  SUPABASE_KEY: import.meta.env.VITE_SUPABASE_ANON_KEY || '',
};

console.log('Config loaded:', {
  API_URL: config.API_URL,
  SUPABASE_URL: config.SUPABASE_URL ? 'set' : 'not set',
  SUPABASE_KEY: config.SUPABASE_KEY ? 'set' : 'not set',
});
