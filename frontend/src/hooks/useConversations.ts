import { useState, useEffect, useCallback } from 'react';
import { Conversation } from '../types';
import { fetchConversations, createConversation } from '../services/api';

interface UseConversationsReturn {
  conversations: Conversation[];
  currentConversation: number | null;
  isLoading: boolean;
  error: string | null;
  handleNewChat: () => void;
  handleSelectConversation: (conversationId: number) => void;
  createNewConversation: () => Promise<number | null>;
  refreshConversations: () => Promise<void>;
  formatConversationTitle: (conversation: Conversation) => string;
}

export const useConversations = (isAuthenticated: boolean): UseConversationsReturn => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const refreshConversations = useCallback(async () => {
    if (!isAuthenticated) return;
    
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchConversations();
      setConversations(data);
    } catch (error) {
      console.error('Error fetching conversations:', error);
      setError(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      refreshConversations();
    }
  }, [isAuthenticated, refreshConversations]);

  const handleNewChat = useCallback(() => {
    setCurrentConversation(null);
  }, []);

  const handleSelectConversation = useCallback((conversationId: number) => {
    setCurrentConversation(conversationId);
  }, []);

  const createNewConversation = useCallback(async (): Promise<number | null> => {
    if (!isAuthenticated) return null;
    
    try {
      setIsLoading(true);
      const data = await createConversation();
      
      // Add to conversations list and set as current
      setConversations(prev => [data, ...prev]);
      setCurrentConversation(data.id);
      
      return data.id;
    } catch (error) {
      console.error('Error creating conversation:', error);
      setError(`Error: ${error instanceof Error ? error.message : String(error)}`);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const formatConversationTitle = useCallback((conversation: Conversation): string => {
    if (conversation.title && conversation.title !== 'New Conversation') {
      return conversation.title;
    }
    return `New conversation (${conversation.message_count} messages)`;
  }, []);

  return {
    conversations,
    currentConversation,
    isLoading,
    error,
    handleNewChat,
    handleSelectConversation,
    createNewConversation,
    refreshConversations,
    formatConversationTitle
  };
};