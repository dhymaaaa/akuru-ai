import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import api from '@/lib/api';
import { UserData } from '@/types';


interface AuthContextType {
  user: UserData | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
  error: string | null;
  clearError: () => void;
}
// Create the context with default values
const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: false,
  isAuthenticated: false,
  login: async () => {},
  signup: async () => {},
  logout: () => {},
  error: null,
  clearError: () => {},
});
// Props for the AuthProvider component
interface AuthProviderProps {
  children: ReactNode;
}
// Provider component that wraps your app and makes auth available
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  // Check if user is already logged in (on app load)
  useEffect(() => {
    const checkAuth = async () => {
      if (api.isAuthenticated()) {
        try {
          const userData = await api.getProfile();
          setUser(userData);
        } catch (err: unknown) {
          // If token is invalid, clear it
          console.error('Invalid token:', err);
          api.logout();
          setUser(null);
        }
      }
      setIsLoading(false);
    };
    checkAuth();
  }, []);
  // Login function
  const login = async (email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.login(email, password);
      const userData = await api.getProfile();
      setUser(userData);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred during login');
      }
      throw err;
    } finally {
      setIsLoading(false);
    }
  };
  // Signup function
  const signup = async (email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.signup(email, password);
      // We don't log the user in automatically after signup
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred during signup');
      }
      throw err;
    } finally {
      setIsLoading(false);
    }
  };
  // Logout function
  const logout = () => {
    api.logout(); // This clears both access and refresh tokens
    setUser(null);
    setError(null); // Clear any existing errors
  };
  // Clear error function
  const clearError = () => {
    setError(null);
  };
  // Value object that will be passed to consumers
  const value = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    signup,
    logout,
    error,
    clearError,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
// Hook for components to get auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
export default AuthContext;