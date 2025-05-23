// hooks/useConversations.ts
import { useState, useCallback } from 'react';
import { Conversation } from '@/types';

export const useConversations = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch conversations from API
  const fetchConversations = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const token = localStorage.getItem('token');
      if (!token) {
        setError('No authentication token found');
        return;
      }

      console.log('Fetching conversations with token:', token);

      const response = await fetch('/api/conversations', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      // Get both status text and response body for better error information
      const responseBody = await response.text();
      console.log('Response from fetch conversations:', response.status, responseBody);
      
      let jsonData;
      try {
        jsonData = responseBody ? JSON.parse(responseBody) : null;
      } catch {
        console.error('Error parsing response:', responseBody);
      }
      
      if (!response.ok) {
        const errorMessage = jsonData?.message || response.statusText || `Error ${response.status}`;
        throw new Error(`Failed to fetch conversations: ${errorMessage}`);
      }

      setConversations(jsonData || []);
    } catch (err) {
      console.error('Error fetching conversations:', err);
      setError(`Error fetching conversations: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Create a new conversation with improved error handling
  const createConversation = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const token = localStorage.getItem('token');
      if (!token) {
        setError('No authentication token found');
        return null;
      }

      console.log('Creating conversation with token:', token);

      // First attempt
      let response = await fetch('/api/conversations', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title: 'New Conversation' })
      });

      // Get both status text and response body for better error information
      let responseBody = await response.text();
      console.log('Response from create conversation:', response.status, responseBody);
      
      // If we got a 500 error, try one more time
      if (response.status === 500) {
        console.log('Received 500 error, retrying conversation creation...');
        
        // Wait 1 second before retry
        await new Promise(r => setTimeout(r, 1000));
        
        response = await fetch('/api/conversations', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ title: 'New Conversation' })
        });
        
        responseBody = await response.text();
        console.log('Retry response:', response.status, responseBody);
      }
      
      let jsonData;
      try {
        jsonData = responseBody ? JSON.parse(responseBody) : null;
        console.log('Parsed response:', jsonData);
      } catch {
        console.error('Error parsing response:', responseBody);
      }
      
      if (!response.ok) {
        // If we still have an error, fall back to mock data in development
        if (process.env.NODE_ENV === 'development') {
          console.warn('Using mock conversation due to server error');
          const mockId = Date.now(); // Use timestamp as temporary ID
          const mockConversation = {
            id: mockId,
            title: 'New Conversation (Mock)',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            message_count: 0
          };
          setConversations(prev => [mockConversation, ...prev]);
          setCurrentConversation(mockId);
          return mockId;
        } else {
          const errorMessage = jsonData?.message || response.statusText || `Error ${response.status}`;
          throw new Error(`Failed to create conversation: ${errorMessage}`);
        }
      }

      if (!jsonData || !jsonData.id) {
        throw new Error('Invalid response format: missing conversation ID');
      }

      // CRITICAL FIX: Set current conversation FIRST, then update conversations list
      // This prevents the race condition in Home component
      setCurrentConversation(jsonData.id);
      
      // Small delay to ensure state update is processed
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Then add to conversations list
      setConversations(prev => [jsonData, ...prev]);

      console.log('✅ Conversation created and set as current:', jsonData.id);
      return jsonData.id;
    } catch (err) {
      console.error('Error creating conversation:', err);
      setError(`Error creating conversation: ${err instanceof Error ? err.message : String(err)}`);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle conversation selection
  const selectConversation = useCallback((conversationId: number) => {
    setCurrentConversation(conversationId);
  }, []);

  // Handle new chat button
  const handleNewChat = useCallback(() => {
    setCurrentConversation(null);
  }, []);

  // Format conversation title for display
  const formatConversationTitle = useCallback((conversation: Conversation) => {
    if (conversation.title && conversation.title !== 'New Conversation') {
      return conversation.title;
    }

    // If no meaningful title, use the first message or default
    return `New conversation (${conversation.message_count} messages)`;
  }, []);

  return {
    conversations,
    currentConversation,
    isLoading,
    error,
    fetchConversations,
    createConversation,
    selectConversation,
    handleNewChat,
    formatConversationTitle
  };
};

export default useConversations;