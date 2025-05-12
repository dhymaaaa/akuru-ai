// lib/api.ts - Unified API service for authentication and chat functionality
import { User, UserData, AuthResponse, Message, Conversation } from '../types';

// Base API URL - can be moved to .env file
const API_URL = 'http://localhost:5000/api';

// Helper function to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
};

// Individual exported functions for backwards compatibility
export const fetchUserData = async (): Promise<UserData> => {
  try {
    const response = await fetch(`${API_URL}/user`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
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
  const response = await fetch(`${API_URL}/conversations`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch conversations: ${response.status} - ${errorText}`);
  }
  
  return await response.json();
};

export const createConversation = async (title: string = 'New Conversation'): Promise<Conversation> => {
  const response = await fetch(`${API_URL}/conversations`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ title })
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to create conversation: ${response.status} - ${errorText}`);
  }
  
  return await response.json();
};

export const fetchMessages = async (conversationId: number): Promise<Message[]> => {
  const response = await fetch(`${API_URL}/conversations/${conversationId}/messages`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  
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
  const response = await fetch(`${API_URL}/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: getAuthHeaders(),
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
  signup: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await fetch(`${API_URL}/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to sign up');
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
    
    return data;
  },
  
  getProfile: async (): Promise<User> => {
    const token = localStorage.getItem('token');
    
    if (!token) {
      throw new Error('No authentication token found');
    }
    
    const response = await fetch(`${API_URL}/profile`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to fetch profile');
    }
    
    return data;
  },
  
  getUserData: fetchUserData,
  logout: (): void => {
    localStorage.removeItem('token');
  },
  
  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('token');
  },
  
  // CHAT ENDPOINTS
  getConversations: fetchConversations,
  createConversation,
  getMessages: fetchMessages,
  sendMessage
};

export default api;