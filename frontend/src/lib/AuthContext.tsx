import { createContext, useContext } from 'react';
import { useAuth } from '@/hooks/useAuth';

// Create context - we'll infer the type from your useAuth hook
const AuthContext = createContext<ReturnType<typeof useAuth> | null>(null);

// Hook to use the context
export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;