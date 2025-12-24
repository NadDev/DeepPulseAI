// Configuration - reads from environment variables
// For production, use Railway API URL
const isDev = import.meta.env.MODE === 'development';

export const config = {
  API_URL: isDev 
    ? 'http://127.0.0.1:8002'
    : 'https://deeppulseai-production.up.railway.app',
  SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL || 'https://opnouxerbecxofzekwpm.supabase.co',
  SUPABASE_KEY: import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_QKhstCwE2ToLugAu2gVt6w_vVO7a9nR',
};

console.log('Config loaded:', {
  API_URL: config.API_URL,
  MODE: import.meta.env.MODE,
  SUPABASE_URL: config.SUPABASE_URL ? 'set' : 'not set',
});
