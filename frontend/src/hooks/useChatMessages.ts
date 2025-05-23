// hooks/useChatMessages.ts
import { useState, useRef, useCallback, RefObject, useEffect } from 'react';
import { Message } from '@/types';

export const useChatMessages = (
  currentConversationId: number | null, 
  createConversation: () => Promise<number | null>,
  onConversationError?: (error: string) => void
) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when messages change
  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => {
        scrollToBottom();
      }, 100);
    }
  }, [messages]);

  // Fetch messages for a conversation (authenticated users only)
  const fetchMessages = useCallback(async (conversationId: number) => {
    if (!conversationId) return;
    
    try {
      setIsProcessing(true);
      setError(null);
      
      const token = localStorage.getItem('token');
      if (!token) {
        setError('No authentication token found');
        return;
      }

      console.log(`Fetching messages for conversation ${conversationId}`);
      
      const response = await fetch(`/api/conversations/${conversationId}/messages`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      const responseBody = await response.text();
      console.log(`Messages response: ${response.status}`, responseBody.substring(0, 100) + (responseBody.length > 100 ? '...' : ''));
      
      let jsonData;
      try {
        jsonData = responseBody ? JSON.parse(responseBody) : null;
      } catch {
        console.error('Error parsing response:', responseBody);
      }

      if (!response.ok) {
        const errorMessage = jsonData?.message || response.statusText || `Error ${response.status}`;
        throw new Error(`Failed to fetch messages: ${errorMessage}`);
      }

      setMessages(jsonData || []);

      // Scroll to bottom after messages load
      setTimeout(() => {
        scrollToBottom();
      }, 100);
    } catch (err) {
      console.error('Error fetching messages:', err);
      setError(`Error fetching messages: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsProcessing(false);
    }
  }, []);

  // Fetch guest messages
  const fetchGuestMessages = useCallback(async () => {
    try {
      const response = await fetch('/api/guest/messages', {
        method: 'GET',
        credentials: 'include'
      });

      if (!response.ok) {
        // If no session exists, just start with empty messages
        if (response.status === 404) {
          setMessages([]);
          return;
        }
        throw new Error('Failed to fetch guest messages');
      }

      const guestMessages = await response.json();
      setMessages(guestMessages || []);
    } catch (err) {
      console.error('Error fetching guest messages:', err);
      // For guests, we don't show errors for missing sessions
      setMessages([]);
    }
  }, []);

  // Send a message and get AI response
  const sendMessage = useCallback(async (content: string, isAuthenticated: boolean = false) => {
    if (!content.trim()) return;

    try {
      setIsProcessing(true);
      setError(null);

      if (!isAuthenticated) {
        // GUEST USER FLOW
        console.log('Sending guest message:', content);
        
        const response = await fetch('/api/guest/messages', {
          method: 'POST',
          credentials: 'include', // Important for sessions!
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            content,
            role: 'user'
          })
        });

        if (!response.ok) {
          throw new Error('Failed to send guest message');
        }

        const data = await response.json();
        console.log('Guest message response:', data);

        // Add both user and AI messages to the UI
        const newMessages: Message[] = [];
        if (data.user_message) {
          newMessages.push(data.user_message);
        }
        if (data.ai_response) {
          newMessages.push(data.ai_response);
        }

        setMessages(prev => [...prev, ...newMessages]);
        setMessage(''); // Clear input
        
        // Scroll to bottom after DOM updates
        setTimeout(() => {
          scrollToBottom();
        }, 100);
        return;
      }

      // AUTHENTICATED USER FLOW
      // If no conversation is selected, create a new one
      let conversationId = currentConversationId;
      if (!conversationId) {
        console.log('No conversation selected, creating a new one');
        conversationId = await createConversation();
        
        if (!conversationId) {
          throw new Error('Failed to create conversation');
        }
        
        console.log('New conversation created with ID:', conversationId);
      }

      // Add user message to UI immediately for better UX
      const userMessage: Message = { role: 'user', content };
      setMessages(prev => [...prev, userMessage]);
      scrollToBottom();

      // Clear input field
      setMessage('');

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      console.log(`Sending message to conversation ${conversationId}: ${content.substring(0, 20)}...`);
      
      const response = await fetch(`/api/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          role: 'user',
          content
        })
      });

      const responseBody = await response.text();
      console.log(`Response from sending message: ${response.status}`, responseBody.substring(0, 100) + (responseBody.length > 100 ? '...' : ''));
      
      let jsonData;
      try {
        jsonData = responseBody ? JSON.parse(responseBody) : null;
      } catch {
        console.error('Error parsing response:', responseBody);
      }

      if (!response.ok) {
        const errorMessage = jsonData?.message || response.statusText || `Error ${response.status}`;
        throw new Error(`Failed to send message: ${errorMessage}`);
      }

      // If the response contains an AI response, add it to the messages
      if (jsonData && jsonData.ai_response) {
        const aiMessage: Message = {
          id: jsonData.ai_response.id,
          role: 'akuru',
          content: jsonData.ai_response.content
        };
        setMessages(prev => [...prev, aiMessage]);
        scrollToBottom();
      }
    } catch (err) {
      console.error('Error sending message:', err);
      const errorMessage = `Error sending message: ${err instanceof Error ? err.message : String(err)}`;
      setError(errorMessage);
      
      // Notify parent component about conversation creation errors
      if (err instanceof Error && 
          err.message.includes('Failed to create conversation') && 
          onConversationError) {
        onConversationError(err.message);
      }
    } finally {
      setIsProcessing(false);
    }
  }, [currentConversationId, createConversation, onConversationError]);

  // Scroll to bottom of messages
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end',
        inline: 'nearest'
      });
    }
  }, []);

  // Clear messages (and guest session if not authenticated)
  const clearMessages = useCallback(async (isAuthenticated: boolean = false) => {
    setMessages([]);
    setError(null);
    
    // If guest user, clear the session on the backend
    if (!isAuthenticated) {
      try {
        await fetch('/api/guest/new-chat', {
          method: 'POST',
          credentials: 'include'
        });
      } catch (err) {
        console.error('Error clearing guest session:', err);
      }
    }
  }, []);

  // Initialize guest session
  const initializeGuestSession = useCallback(async () => {
    try {
      await fetch('/api/guest/new-session', {
        method: 'POST',
        credentials: 'include'
      });
      console.log('Guest session initialized');
    } catch (err) {
      console.error('Error initializing guest session:', err);
    }
  }, []);

  return {
    messages,
    isProcessing,
    message,
    error,
    messagesEndRef: messagesEndRef as RefObject<HTMLDivElement>,
    setMessage,
    fetchMessages,
    fetchGuestMessages,
    sendMessage,
    clearMessages,
    scrollToBottom,
    initializeGuestSession
  };
};

export default useChatMessages;