// hooks/useChatMessages.ts
import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchMessages, sendMessage } from '../lib/api';
import { Message } from '../types';

// The key is to type the return interface correctly to match what useRef actually returns
interface UseChatMessagesReturn {
  messages: Message[];
  messageInput: string;
  setMessageInput: (value: string) => void;
  isProcessing: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  loadMessages: (conversationId: number) => Promise<void>;
  handleSendMessage: (content: string, conversationId: number | null, createConversation: () => Promise<number | null>, isTryingFirst: boolean) => Promise<void>;
  scrollToBottom: () => void;
}

export const useChatMessages = (): UseChatMessagesReturn => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageInput, setMessageInput] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const loadMessages = useCallback(async (conversationId: number) => {
    try {
      const data = await fetchMessages(conversationId);
      setMessages(data);
      
      // Ensure we scroll to the bottom after loading messages
      scrollToBottom();
      // Additional delayed scroll to handle any rendering delays
      setTimeout(() => {
        scrollToBottom();
      }, 100);
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  }, [scrollToBottom]);

  const handleSendMessage = useCallback(async (
    content: string, 
    conversationId: number | null, 
    createConversation: () => Promise<number | null>,
    isTryingFirst: boolean
  ) => {
    if (!content.trim()) return;

    try {
      setIsProcessing(true);

      // Handle guest/try-first mode
      if (isTryingFirst) {
        // Add user message immediately
        const userMessage: Message = { role: 'user', content };
        setMessages(prev => [...prev, userMessage]);
        
        // Scroll to bottom after adding user message
        scrollToBottom();

        // Simulate AI response after delay
        setTimeout(() => {
          const aiMessage: Message = {
            role: 'akuru',
            content: "This is a demo version. Please sign up or log in to chat with Akuru AI's full capabilities."
          };
          setMessages(prev => [...prev, aiMessage]);
          scrollToBottom();
          setIsProcessing(false);
        }, 1000);

        // Clear input
        setMessageInput('');
        return;
      }

      // If no conversation is selected, create a new one
      let currentConvId = conversationId;
      if (!currentConvId) {
        currentConvId = await createConversation();
        if (!currentConvId) throw new Error('Failed to create conversation');
      }

      // Add user message immediately for better UX
      const userMessage: Message = { role: 'user', content };
      setMessages(prev => [...prev, userMessage]);
      
      // Scroll to bottom after adding user message
      scrollToBottom();

      // Clear input field
      setMessageInput('');

      // Send message to API
      const response = await sendMessage(currentConvId, content);

      // Add AI response if present
      if (response.ai_response) {
        const aiMessage: Message = {
          id: response.ai_response.id,
          role: 'akuru',
          content: response.ai_response.content
        };
        setMessages(prev => [...prev, aiMessage]);
        scrollToBottom();
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [scrollToBottom]);

  return {
    messages,
    messageInput,
    setMessageInput,
    isProcessing,
    messagesEndRef,
    loadMessages,
    handleSendMessage,
    scrollToBottom
  };
};