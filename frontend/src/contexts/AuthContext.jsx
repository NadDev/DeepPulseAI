/**
 * Authentication Context
 * ======================
 * Provides authentication state and methods throughout the app
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  login,
  register,
  logout,
  getCurrentUser,
  resetPassword,
  isAuthenticated,
} from '../services/authService';

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
    // Get initial user from backend
    const loadUser = async () => {
      try {
        if (isAuthenticated()) {
          const currentUser = await getCurrentUser();
          setUser(currentUser);
          setSession(currentUser ? { user: currentUser } : null);
        }
      } catch (error) {
        console.error('Failed to load user:', error);
        setUser(null);
        setSession(null);
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  const value = {
    user,
    session,
    loading,
    signUp: async (email, password, username) => {
      try {
        const data = await register(email, password, username);
        setUser(data.user);
        setSession({ user: data.user });
        return { data, error: null };
      } catch (error) {
        console.error('Sign up error:', error);
        return { data: null, error };
      }
    },
    signIn: async (email, password) => {
      try {
        const data = await login(email, password);
        setUser(data.user);
        setSession({ user: data.user });
        return { data, error: null };
      } catch (error) {
        console.error('Sign in error:', error);
        return { data: null, error };
      }
    },
    signOut: async () => {
      try {
        await logout();
        setUser(null);
        setSession(null);
        return { error: null };
      } catch (error) {
        console.error('Sign out error:', error);
        return { error };
      }
    },
    resetPassword: async (email) => {
      try {
        await resetPassword(email);
        return { error: null };
      } catch (error) {
        console.error('Reset password error:', error);
        return { error };
      }
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
