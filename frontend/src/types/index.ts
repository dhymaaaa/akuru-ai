// User-related types
export interface UserData {
  name: string;
  email: string;
}

// Message-related types
export interface Message {
  id?: number;
  role: 'user' | 'akuru';
  content: string;
  created_at?: string;
}

// Conversation-related types
export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}