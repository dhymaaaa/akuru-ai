import { useState, useEffect } from 'react';
import { UserData } from '@/types';

export const useAuth = () => {
  const [userData, setUserData] = useState<UserData>({ name: '', email: '' });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isGuestMode, setIsGuestMode] = useState<boolean>(false);

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Check if explicitly in guest mode
        const guestModeFlag = localStorage.getItem('guestMode');
        if (guestModeFlag === 'true') {
          console.log('Guest mode detected - skipping auth check');
          setUserData({ name: 'Guest', email: 'Guest session' });
          setIsAuthenticated(false);
          setIsGuestMode(true);
          setIsLoading(false);
          return;
        }
        
        // Check if token exists
        const token = localStorage.getItem('token');
        if (!token) {
          console.log('No token found - setting guest mode');
          setUserData({ name: 'Guest', email: 'Guest account' });
          setIsAuthenticated(false);
          setIsGuestMode(true);
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
              localStorage.removeItem('guestMode'); // Clear guest mode flag too
              setUserData({ name: 'Guest', email: 'Guest account' });
              setIsAuthenticated(false);
              setIsGuestMode(true);
              setIsLoading(false);
              return;
            }

            // For other errors (server errors, etc.), keep the token but show as authenticated with error
            const errorText = await response.text();
            console.error('API response not OK:', response.status, response.statusText, errorText);
            setError(`Server error: ${response.status} ${response.statusText}`);
            // IMPORTANT: Still set as authenticated since token exists and it's just a server error
            setUserData({ name: 'User', email: 'Loading...' });
            setIsAuthenticated(true); // Changed from false to true
            setIsGuestMode(false); // Changed from not setting to false
            setIsLoading(false);
            return;
          }

          const responseText = await response.text();
          if (!responseText.trim()) {
            // Empty response - keep authenticated state since token is valid
            setError('Empty response from server');
            setUserData({ name: 'User', email: 'Loading...' });
            setIsAuthenticated(true); // Changed from false to true
            setIsGuestMode(false); // Changed from not setting to false
            setIsLoading(false);
            return;
          }

          const data = JSON.parse(responseText);
          if (!data || typeof data !== 'object') {
            // Invalid data format - keep authenticated state since token is valid
            setError('Invalid data format received');
            setUserData({ name: 'User', email: 'Loading...' });
            setIsAuthenticated(true); // Changed from false to true
            setIsGuestMode(false); // Changed from not setting to false
            setIsLoading(false);
            return;
          }

          // Successfully authenticated
          setUserData({
            name: data.name || 'User',
            email: data.email || 'user@example.com'
          });
          setIsAuthenticated(true);
          setIsGuestMode(false);

        } catch (fetchError) {
          console.error('Fetch error:', fetchError);
          
          // For network errors, keep authenticated state since token exists
          if (fetchError instanceof TypeError && fetchError.message.includes('fetch')) {
            // Network error - keep token and show as authenticated
            setError('Network error. Please check your connection.');
            setUserData({ name: 'User', email: 'Connection error' });
            setIsAuthenticated(true); // Keep authenticated
            setIsGuestMode(false);
          } else {
            // Other fetch errors (parsing, etc.) - keep token and authenticated state
            setError(`Connection failed: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}`);
            setUserData({ name: 'User', email: 'Connection error' });
            setIsAuthenticated(true); // Keep authenticated
            setIsGuestMode(false);
          }
        }

      } catch (error) {
        console.error('Error in overall fetchUserData function:', error);
        
        // For unexpected errors, if token exists, keep authenticated state
        const token = localStorage.getItem('token');
        if (token) {
          setError(`Authentication check failed: ${error instanceof Error ? error.message : String(error)}`);
          setUserData({ name: 'User', email: 'Error occurred' });
          setIsAuthenticated(true); // Keep authenticated if token exists
          setIsGuestMode(false);
        } else {
          // No token and error occurred, set guest mode
          setUserData({ name: 'Guest', email: 'Guest account' });
          setIsAuthenticated(false);
          setIsGuestMode(true);
        }
        
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserData();
  }, []);

  const handleSignUp = () => {
    // Clear guest mode when going to signup
    localStorage.removeItem('guestMode');
    window.location.href = '/signup';
  };

  const handleLogin = () => {
    // Clear guest mode when going to login
    localStorage.removeItem('guestMode');
    window.location.href = '/login';
  };

  const handleTryFirst = () => {
    // Clear any existing token and set explicit guest mode
    localStorage.removeItem('token');
    localStorage.setItem('guestMode', 'true');
    setUserData({ name: 'Guest', email: 'Guest session' });
    setIsAuthenticated(false);
    setIsGuestMode(true);
    setError(null);
    return true;
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('guestMode');
    setIsAuthenticated(false);
    setUserData({ name: 'Guest', email: 'Guest account' });
    setIsGuestMode(true);
    setError(null);
  };

  // Add a method to manually refresh auth state (useful after login)
  const refreshAuthState = async () => {
    setIsLoading(true);
    // Remove guest mode flag and re-run the auth check
    localStorage.removeItem('guestMode');
    
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const response = await fetch('/api/user', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          setUserData({
            name: data.name || 'User',
            email: data.email || 'user@example.com'
          });
          setIsAuthenticated(true);
          setIsGuestMode(false);
          setError(null);
        } else {
          // Token is invalid
          localStorage.removeItem('token');
          setIsAuthenticated(false);
          setIsGuestMode(true);
          setUserData({ name: 'Guest', email: 'Guest account' });
        }
      } catch (error) {
        console.error('Error refreshing auth state:', error);
        // Keep current state on error
      }
    } else {
      setIsAuthenticated(false);
      setIsGuestMode(true);
      setUserData({ name: 'Guest', email: 'Guest account' });
    }
    setIsLoading(false);
  };

  return {
    userData,
    isLoading,
    error,
    isAuthenticated,
    isGuestMode,
    handleSignUp,
    handleLogin,
    handleTryFirst,
    handleLogout,
    refreshAuthState // Add this new method
  };
};