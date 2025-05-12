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
          console.warn('No token found in localStorage');
          setUserData({ name: 'Guest', email: 'Guest account' });
          setIsAuthenticated(false);
          setIsLoading(false);
          return;
        }

        console.log('Token found, attempting to fetch user data');
        setIsAuthenticated(true);

        try {
          const response = await fetch('/api/user', {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });

          if (!response.ok) {
            const errorText = await response.text();
            console.error('API response not OK:', response.status, response.statusText, errorText);
            throw new Error(`Failed to fetch user data: ${response.status}`);
          }

          const responseText = await response.text();

          if (!responseText.trim()) {
            throw new Error('Empty response from server');
          }

          const data = JSON.parse(responseText);

          if (!data || typeof data !== 'object') {
            throw new Error('Invalid data format received');
          }

          setUserData({
            name: data.name || 'User',
            email: data.email || 'user@example.com'
          });
        } catch (fetchError) {
          console.error('Fetch error:', fetchError);
          setUserData({ name: 'User', email: 'Error fetching data' });
          setError(`Fetch error: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}`);
        }
      } catch (error) {
        console.error('Error in overall fetchUserData function:', error);
        setUserData({ name: 'Guest', email: 'Error occurred' });
        setError(`Global error: ${error instanceof Error ? error.message : String(error)}`);
        setIsAuthenticated(false);
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
    // Set guest mode
    setUserData({ name: 'Guest', email: 'Guest session' });
    return true;
  };
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUserData({ name: 'Guest', email: 'Guest account' });
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