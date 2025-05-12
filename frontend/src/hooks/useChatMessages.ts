// hooks/useChatMessages.ts
import { useState, useRef, useCallback, RefObject } from 'react';
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

  // Fetch messages for a conversation
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

  // Send a message and get AI response
  const sendMessage = useCallback(async (content: string, isTryingFirst: boolean = false) => {
    if (!content.trim()) return;

    try {
      setIsProcessing(true);
      setError(null);

      // If in try-first mode, handle guest messages locally
      if (isTryingFirst) {
        // Add user message to UI
        const userMessage: Message = { role: 'user', content };
        setMessages(prev => [...prev, userMessage]);

        // Simulate AI response after short delay
        setTimeout(() => {
          const aiMessage: Message = {
            role: 'akuru',
            content: "This is a demo version. Please sign up or log in to chat with Akuru AI's full capabilities."
          };
          setMessages(prev => [...prev, aiMessage]);
          scrollToBottom();
          setIsProcessing(false);
        }, 1000);

        // Clear input field
        setMessage('');
        return;
      }

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
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isProcessing,
    message,
    error,
    messagesEndRef: messagesEndRef as RefObject<HTMLDivElement>,
    setMessage,
    fetchMessages,
    sendMessage,
    clearMessages,
    scrollToBottom
  };
};

export default useChatMessages;