export interface UserData {
  name: string;
  email: string;
}

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
