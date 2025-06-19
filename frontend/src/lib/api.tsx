import {  UserData, AuthResponse, Message, Conversation } from '@/types';

// Base API URL - can be moved to .env file
const API_URL = 'http://localhost:5000/api';

// Helper function to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  console.log('Token retrieved from storage:', token ? 'exists' : 'missing');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
};

// Token refresh logic (commented out since your Flask doesn't have this endpoint)
const refreshToken = async (): Promise<string | null> => {
  try {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      console.log('No refresh token available');
      return null;
    }
    
    console.log('Attempting to refresh token...');
    // NOTE: Your Flask backend doesn't have /refresh endpoint
    // You may want to implement this or remove refresh logic
    const response = await fetch(`${API_URL}/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken })
    });
    
    if (!response.ok) {
      console.error('Token refresh failed with status:', response.status);
      return null;
    }
    
    const data = await response.json();
    localStorage.setItem('token', data.token);
    console.log('Token refreshed successfully');
    return data.token;
  } catch (error) {
    console.error('Token refresh error:', error);
    return null;
  }
};

// Enhanced fetch with automatic token refresh
const authFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  // Add auth headers to the provided options
  const fetchOptions = {
    ...options,
    headers: {
      ...options.headers,
      ...getAuthHeaders()
    }
  };
  
  // First attempt
  let response = await fetch(url, fetchOptions);
  
  // If unauthorized, try refresh (only if refresh endpoint exists)
  if (response.status === 401) {
    console.log('Received 401, attempting to refresh token...');
    const newToken = await refreshToken();
    
    if (newToken) {
      // Update headers with new token
      fetchOptions.headers = {
        ...fetchOptions.headers,
        'Authorization': `Bearer ${newToken}`
      };
      
      // Retry with new token
      console.log('Retrying request with new token...');
      response = await fetch(url, fetchOptions);
    } else {
      console.log('Token refresh failed, user needs to re-authenticate');
      // Handle authentication failure
      // Optional: Redirect to login
      // window.location.href = '/login';
    }
  }
  
  return response;
};

// Individual exported functions with enhanced auth
export const fetchUserData = async (): Promise<UserData> => {
  try {
    const response = await authFetch(`${API_URL}/user`); // Fixed: was /profile
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to fetch user data: ${response.status} - ${errorText}`);
    }
    
    const responseText = await response.text();
    if (!responseText.trim()) {
      throw new Error('Empty response from server');
    }
    
    const data = JSON.parse(responseText);
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid data format received');
    }
    
    return {
      name: data.name || 'User',
      email: data.email || 'user@example.com'
    };
  } catch (error) {
    console.error('Error fetching user data:', error);
    return {
      name: 'Guest',
      email: 'guest@example.com'
    };
  }
};

export const fetchConversations = async (): Promise<Conversation[]> => {
  console.log('Fetching conversations...');
  const response = await authFetch(`${API_URL}/conversations`);
  
  if (!response.ok) {
    const errorText = await response.text();
    console.error('Fetch conversations failed:', response.status, errorText);
    throw new Error(`Failed to fetch conversations: ${response.status} - ${errorText}`);
  }
  
  const data = await response.json();
  console.log(`Successfully fetched ${data.length} conversations`);
  return data;
};

export const createConversation = async (title: string = 'New Conversation'): Promise<Conversation> => {
  const response = await authFetch(`${API_URL}/conversations`, {
    method: 'POST',
    body: JSON.stringify({ title })
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to create conversation: ${response.status} - ${errorText}`);
  }
  
  return await response.json();
};

export const fetchMessages = async (conversationId: number): Promise<Message[]> => {
  const response = await authFetch(`${API_URL}/conversations/${conversationId}/messages`);
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch messages: ${response.status} - ${errorText}`);
  }
  
  return await response.json();
};

export const sendMessage = async (conversationId: number, content: string): Promise<{
  message: Message,
  ai_response?: Message
}> => {
  const response = await authFetch(`${API_URL}/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({
      role: 'user',
      content
    })
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to send message: ${response.status} - ${errorText}`);
  }
  
  return await response.json();
};

// Main API object with all functions
const api = {
  // AUTH ENDPOINTS
  signup: async (email: string, password: string, name: string): Promise<AuthResponse> => {
    // Updated to include name parameter that your Flask expects
    const response = await fetch(`${API_URL}/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, email, password }), // Added name field
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to sign up');
    }
    
    // Store the token if returned (your Flask signup now returns token)
    if (data.token) {
      localStorage.setItem('token', data.token);
      if (data.refreshToken) {
        localStorage.setItem('refreshToken', data.refreshToken);
      }
    }
    
    return data;
  },
  
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await fetch(`${API_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to log in');
    }
    
    // Store the token
    if (data.token) {
      localStorage.setItem('token', data.token);
      // If your API returns a refresh token, store it too
      if (data.refreshToken) {
        localStorage.setItem('refreshToken', data.refreshToken);
      }
    }
    
    return data;
  },
  
  getProfile: async (): Promise<UserData> => {
    // Fixed: changed from /profile to /user to match Flask backend
    const response = await authFetch(`${API_URL}/user`);
    
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `Failed to fetch profile: ${response.status}`);
    }
    
    return await response.json();
  },
  
  getUserData: fetchUserData,
  
  logout: (): void => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
  },
  
  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('token');
  },
  
  refreshToken,
  
  // CHAT ENDPOINTS
  getConversations: fetchConversations,
  createConversation,
  getMessages: fetchMessages,
  sendMessage
};

export default api;