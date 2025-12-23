/**
 * Authentication Context
 * ======================
 * Provides authentication state and methods throughout the app
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { supabase, signIn, signUp, signOut, resetPassword } from '../services/supabaseClient';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState(null);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const value = {
    user,
    session,
    loading,
    signUp: async (email, password, username) => {
      try {
        const data = await signUp(email, password, username);
        return { data, error: null };
      } catch (error) {
        return { data: null, error };
      }
    },
    signIn: async (email, password) => {
      try {
        const data = await signIn(email, password);
        return { data, error: null };
      } catch (error) {
        return { data: null, error };
      }
    },
    signOut: async () => {
      try {
        await signOut();
        return { error: null };
      } catch (error) {
        return { error };
      }
    },
    resetPassword: async (email) => {
      try {
        await resetPassword(email);
        return { error: null };
      } catch (error) {
        return { error };
      }
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
