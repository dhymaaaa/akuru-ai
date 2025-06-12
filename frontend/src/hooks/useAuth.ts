import { useState, useEffect } from 'react';
import { UserData } from '@/types';

export const useAuth = () => {
  const [userData, setUserData] = useState<UserData>({ name: '', email: '' });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Check if token exists
        const token = localStorage.getItem('token');
        if (!token) {
          console.log('No token found - setting guest mode');
          setUserData({ name: 'Guest', email: 'Guest account' });
          setIsAuthenticated(false);
          setIsLoading(false);
          return;
        }

        console.log('Token found, attempting to fetch user data');
        
        try {
          const response = await fetch('/api/user', {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });

          if (!response.ok) {
            // Handle different error scenarios
            if (response.status === 401 || response.status === 403) {
              // Token is invalid/expired - clean up and set guest mode
              console.warn('Token is invalid or expired, removing from localStorage');
              localStorage.removeItem('token');
              setUserData({ name: 'Guest', email: 'Guest account' });
              setIsAuthenticated(false);
              setIsLoading(false);
              return;
            }

            const errorText = await response.text();
            console.error('API response not OK:', response.status, response.statusText, errorText);
            throw new Error(`Server error: ${response.status} ${response.statusText}`);
          }

          const responseText = await response.text();
          if (!responseText.trim()) {
            throw new Error('Empty response from server');
          }

          const data = JSON.parse(responseText);
          if (!data || typeof data !== 'object') {
            throw new Error('Invalid data format received');
          }

          // Successfully authenticated
          setUserData({
            name: data.name || 'User',
            email: data.email || 'user@example.com'
          });
          setIsAuthenticated(true);

        } catch (fetchError) {
          console.error('Fetch error:', fetchError);
          
          // If it's a network error or server error, don't clear auth state
          // but show error message
          if (fetchError instanceof TypeError && fetchError.message.includes('fetch')) {
            // Network error - keep token but show error
            setError('Network error. Please check your connection.');
            setUserData({ name: 'User', email: 'Connection error' });
          } else {
            // Other errors - clear token and set guest mode
            localStorage.removeItem('token');
            setUserData({ name: 'Guest', email: 'Guest account' });
            setIsAuthenticated(false);
            setError(`Authentication failed: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}`);
          }
        }

      } catch (error) {
        console.error('Error in overall fetchUserData function:', error);
        
        // On any unexpected error, clear token and set guest mode
        localStorage.removeItem('token');
        setUserData({ name: 'Guest', email: 'Guest account' });
        setIsAuthenticated(false);
        setError(`Authentication error: ${error instanceof Error ? error.message : String(error)}`);
        
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserData();
  }, []);

  const handleSignUp = () => {
    window.location.href = '/signup';
  };

  const handleLogin = () => {
    window.location.href = '/login';
  };

  const handleTryFirst = () => {
    // Clear any existing token and set guest mode
    localStorage.removeItem('token');
    setUserData({ name: 'Guest', email: 'Guest session' });
    setIsAuthenticated(false);
    setError(null);
    return true;
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUserData({ name: 'Guest', email: 'Guest account' });
    setError(null);
  };

  return {
    userData,
    isLoading,
    error,
    isAuthenticated,
    handleSignUp,
    handleLogin,
    handleTryFirst,
    handleLogout
  };
};