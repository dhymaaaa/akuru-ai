import { Conversation, Message, UserData } from '../types';

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
};

export const fetchUserData = async (): Promise<UserData> => {
  const response = await fetch('/api/user', {
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
};

export const fetchConversations = async (): Promise<Conversation[]> => {
  const response = await fetch('/api/conversations', {
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
  const response = await fetch('/api/conversations', {
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
  const response = await fetch(`/api/conversations/${conversationId}/messages`, {
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
  const response = await fetch(`/api/conversations/${conversationId}/messages`, {
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