import { useState, useEffect } from 'react';
import { UserData } from '../types';
import { fetchUserData } from '../services/api';

interface UseAuthReturn {
  userData: UserData;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  isTryingFirst: boolean;
  handleSignUp: () => void;
  handleLogin: () => void;
  handleTryFirst: () => void;
  handleCloseModal: () => void;
  showAuthModal: boolean;
}

export const useAuth = (): UseAuthReturn => {
  const [userData, setUserData] = useState<UserData>({ name: '', email: '' });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [showAuthModal, setShowAuthModal] = useState<boolean>(true);
  const [isTryingFirst, setIsTryingFirst] = useState<boolean>(false);

  useEffect(() => {
    const initAuth = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const token = localStorage.getItem('token');
        if (!token) {
          console.warn('No token found in localStorage');
          setUserData({ name: 'Guest', email: 'Guest account' });
          setIsAuthenticated(false);
          setIsLoading(false);
          return;
        }

        console.log('Token found, attempting to fetch user data');
        setIsAuthenticated(true);

        try {
          const userData = await fetchUserData();
          setUserData(userData);
        } catch (fetchError) {
          console.error('Fetch error:', fetchError);
          setUserData({ name: 'User', email: 'Error fetching data' });
          setError(`Fetch error: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}`);
        }
      } catch (error) {
        console.error('Error in overall auth initialization:', error);
        setUserData({ name: 'Guest', email: 'Error occurred' });
        setError(`Global error: ${error instanceof Error ? error.message : String(error)}`);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const handleSignUp = () => {
    window.location.href = '/signup';
  };

  const handleLogin = () => {
    window.location.href = '/login';
  };

  const handleTryFirst = () => {
    setShowAuthModal(false);
    setIsTryingFirst(true);
    setUserData({ name: 'Guest', email: 'Guest session' });
  };

  const handleCloseModal = () => {
    setShowAuthModal(false);
  };

  return {
    userData,
    isLoading,
    error,
    isAuthenticated,
    isTryingFirst,
    handleSignUp,
    handleLogin,
    handleTryFirst,
    handleCloseModal,
    showAuthModal
  };
};