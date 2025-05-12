// User related types
export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface UserData {
  name: string;
  email: string;
}

export interface AuthResponse {
  token: string;
  message: string;
}

// Chat related types
export interface Message {
  id?: number;
  role: 'user' | 'akuru';
  content: string;
  created_at?: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

// API related types
export interface ApiError {
  error: string;
}