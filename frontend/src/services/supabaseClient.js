/**
 * Supabase Client - STUB
 * =======================
 * This app uses local JWT authentication (backend/app/auth/local_auth.py).
 * Supabase is NOT used for auth. This stub replaces the real Supabase client
 * to prevent @supabase/supabase-js from firing token refresh requests.
 *
 * All auth is done via authService.js → /api/auth/* endpoints.
 */

// Clear any stale Supabase session keys that may exist in localStorage
// from previous versions of this app that used Supabase auth.
try {
  Object.keys(localStorage)
    .filter(k => k.startsWith('sb-') || k === 'crbot-auth' || k === '__supabase_disabled__')
    .forEach(k => localStorage.removeItem(k));
} catch (_) {}

// No-op stub — same API surface, does nothing
const noop = () => Promise.resolve({ data: null, error: null });
const noopObj = new Proxy({}, { get: () => noop });

export const supabase = {
  auth: noopObj,
  from: () => noopObj,
};

export const getCurrentUser = async () => null;
export const signUp = async () => ({ data: null, error: new Error('Use authService') });
export const signIn = async () => ({ data: null, error: new Error('Use authService') });
export const signOut = async () => {};
export const resetPassword = async () => {};
export const updatePassword = async () => {};
export const getAuthHeaders = async () => ({});

export default supabase;


/**
 * Get current authenticated user
 */
export const getCurrentUser = async () => {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error) throw error;
  return user;
};

/**
 * Sign up new user
 */
export const signUp = async (email, password, username) => {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        username,
      },
    },
  });
  if (error) throw error;
  return data;
};

/**
 * Sign in user
 */
export const signIn = async (email, password) => {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  if (error) throw error;
  return data;
};

/**
 * Sign out user
 */
export const signOut = async () => {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
};

/**
 * Reset password
 */
export const resetPassword = async (email) => {
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/reset-password`,
  });
  if (error) throw error;
};

/**
 * Update password
 */
export const updatePassword = async (newPassword) => {
  const { error } = await supabase.auth.updateUser({
    password: newPassword,
  });
  if (error) throw error;
};

/**
 * Get authentication headers for API requests
 */
export const getAuthHeaders = async () => {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    throw new Error('Not authenticated');
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`
  };
};

export default supabase;
