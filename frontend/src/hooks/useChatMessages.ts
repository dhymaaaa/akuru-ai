import { useState, useRef, useCallback, RefObject, useEffect } from 'react';
import { Message } from '@/types';

export const useChatMessages = (
  currentConversationId: number | null,
  createConversation: () => Promise<number | null>,
  onConversationError?: (error: string) => void,
  onTitleUpdate?: (conversationId: number, newTitle: string) => void
) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isFetchingMessages, setIsFetchingMessages] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll when messages change
  useEffect(() => {
    if (messages.length > 0 || streamingMessage) {
      setTimeout(() => {
        scrollToBottom();
      }, 100);
    }
  }, [messages, streamingMessage]);

  // Fetch messages for a conversation (authenticated users only)
  const fetchMessages = useCallback(async (conversationId: number) => {
    if (!conversationId) return;

    try {
      console.log('Setting isFetchingMessages to true (fetchMessages)');
      setIsFetchingMessages(true);
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
      console.log('Setting isFetchingMessages to false (fetchMessages)');
      setIsFetchingMessages(false);
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
      setMessages([]);
    }
  }, []);

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

  // Stream AI response for authenticated users
  const streamAIResponse = useCallback(async (conversationId: number) => {
    try {
      setIsStreaming(true);
      setStreamingMessage('');

      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      console.log(`Starting stream for conversation ${conversationId}`);

      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          conversation_id: conversationId
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`Streaming failed: ${response.status} ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No readable stream available');
      }

      const decoder = new TextDecoder();
      let englishSection = '';
      let dhivehiSection = '';
      let currentSection = 'english';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.section_change && data.section === 'dhivehi') {
                  currentSection = 'dhivehi';
                  continue;
                }

                if (data.chunk) {
                  if (currentSection === 'english') {
                    englishSection += data.chunk;
                  } else {
                    dhivehiSection += data.chunk;
                  }

                  // Update the streaming message display
                  const displayText = englishSection + (dhivehiSection ? '\n\n' + dhivehiSection : '');
                  setStreamingMessage(displayText);

                  // Scroll to bottom as text streams in
                  setTimeout(() => scrollToBottom(), 10);
                }
              } catch (parseError) {
                console.error('Error parsing streaming data:', parseError);
              }
            }
          }
        }

        // When streaming is complete, save the final message
        const finalMessage = englishSection + (dhivehiSection ? '\n\n' + dhivehiSection : '');

        if (finalMessage.trim()) {
          // Save the AI response to backend
          const saveResponse = await fetch(`/api/conversations/${conversationId}/messages`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              role: 'akuru',
              content: finalMessage
            })
          });

          if (saveResponse.ok) {
            const saveData = await saveResponse.json();

            // Add the complete message to the messages array
            const aiMessage: Message = {
              id: saveData.id,
              role: 'akuru',
              content: finalMessage
            };

            setMessages(prev => [...prev, aiMessage]);
          }
        }

      } finally {
        reader.releaseLock();
      }

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Stream aborted by user');
      } else {
        console.error('Error in streaming:', err);
        setError(`Streaming error: ${err instanceof Error ? err.message : String(err)}`);
      }
    } finally {
      setIsStreaming(false);
      setStreamingMessage('');
      abortControllerRef.current = null;
    }
  }, [scrollToBottom]);

  // NEW: Stream AI response for guest users
  const streamGuestAIResponse = useCallback(async () => {
    try {
      setIsStreaming(true);
      setStreamingMessage('');

      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      console.log('Starting guest stream');

      const response = await fetch('/api/guest/stream', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`Guest streaming failed: ${response.status} ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No readable stream available');
      }

      const decoder = new TextDecoder();
      let englishSection = '';
      let dhivehiSection = '';
      let currentSection = 'english';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.section_change && data.section === 'dhivehi') {
                  currentSection = 'dhivehi';
                  continue;
                }

                if (data.chunk) {
                  if (currentSection === 'english') {
                    englishSection += data.chunk;
                  } else {
                    dhivehiSection += data.chunk;
                  }

                  // Update the streaming message display
                  const displayText = englishSection + (dhivehiSection ? '\n\n' + dhivehiSection : '');
                  setStreamingMessage(displayText);

                  // Scroll to bottom as text streams in
                  setTimeout(() => scrollToBottom(), 10);
                }
              } catch (parseError) {
                console.error('Error parsing streaming data:', parseError);
              }
            }
          }
        }

        // When streaming is complete, save the final message
        const finalMessage = englishSection + (dhivehiSection ? '\n\n' + dhivehiSection : '');

        if (finalMessage.trim()) {
          // Save the AI response to guest session
          const saveResponse = await fetch('/api/guest/save-response', {
            method: 'POST',
            credentials: 'include',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              role: 'akuru',
              content: finalMessage
            })
          });

          if (saveResponse.ok) {
            const saveData = await saveResponse.json();

            // Add the complete message to the messages array
            const aiMessage: Message = {
              id: saveData.id || Date.now(), // Use timestamp as fallback ID for guests
              role: 'akuru',
              content: finalMessage
            };

            setMessages(prev => [...prev, aiMessage]);
          }
        }

      } finally {
        reader.releaseLock();
      }

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Guest stream aborted by user');
      } else {
        console.error('Error in guest streaming:', err);
        setError(`Guest streaming error: ${err instanceof Error ? err.message : String(err)}`);
      }
    } finally {
      setIsStreaming(false);
      setStreamingMessage('');
      abortControllerRef.current = null;
    }
  }, [scrollToBottom]);

  // Stop streaming
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      setStreamingMessage('');
    }
  }, []);

  // UPDATED: Send a message and get AI response (now with guest streaming)
  const sendMessage = useCallback(async (content: string, isAuthenticated: boolean = false, useStreaming: boolean = true) => {
    if (!content.trim()) return;

    try {
      console.log('Setting isProcessing to true (sendMessage)', { isAuthenticated, useStreaming });
      setIsProcessing(true);
      setError(null);

      if (!isAuthenticated) {
        // UPDATED GUEST USER FLOW (with streaming support)
        console.log('Sending guest message with streaming:', content);

        // Add user message to UI immediately for better UX
        const userMessage: Message = { 
          id: Date.now(), 
          role: 'user', 
          content 
        };
        setMessages(prev => [...prev, userMessage]);
        setMessage('');
        scrollToBottom();

        // Save user message to guest session
        const response = await fetch('/api/guest/messages', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            content,
            role: 'user',
            use_streaming: useStreaming
          })
        });

        if (!response.ok) {
          throw new Error('Failed to send guest message');
        }

        const data = await response.json();
        console.log('Guest message response:', data);

        // Check if we should stream or use immediate response
        if (data.use_streaming !== false && useStreaming) {
          console.log('Starting guest streaming');
          await streamGuestAIResponse();
        } else if (data.ai_response) {
          // Fallback to immediate response if streaming not available
          console.log('Adding immediate guest AI response');
          const aiMessage: Message = {
            id: data.ai_response.id || Date.now() + 1,
            role: 'akuru',
            content: data.ai_response.content
          };
          setMessages(prev => [...prev, aiMessage]);
          setTimeout(() => scrollToBottom(), 100);
        }

        return;
      }

      // AUTHENTICATED USER FLOW (unchanged)
      console.log('Starting authenticated user flow');

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

      // Send the user message to backend first
      console.log(`Sending user message to conversation ${conversationId}: ${content.substring(0, 20)}...`);

      const response = await fetch(`/api/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          role: 'user',
          content,
          use_streaming: useStreaming
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      // Handle title update if returned from backend
      if (data.updated_title && data.conversation_id) {
        console.log(`Received title update: ${data.updated_title} for conversation ${data.conversation_id}`);
        onTitleUpdate?.(data.conversation_id, data.updated_title);
      }

      // If we have an immediate AI response (non-streaming), add it
      if (data.ai_response) {
        console.log('Adding immediate AI response');
        const aiMessage: Message = {
          id: data.ai_response.id,
          role: 'akuru',
          content: data.ai_response.content
        };
        setMessages(prev => [...prev, aiMessage]);
        scrollToBottom();
      } else {
        // Check if we should stream
        const shouldStream = data.use_streaming !== false && useStreaming;
        console.log('Should stream?', shouldStream, {
          'data.use_streaming': data.use_streaming,
          'frontend useStreaming': useStreaming
        });

        if (shouldStream) {
          console.log('Starting streaming');
          await streamAIResponse(conversationId);
        }
      }

    } catch (err) {
      console.error('Error sending message:', err);
      const errorMessage = `Error sending message: ${err instanceof Error ? err.message : String(err)}`;
      setError(errorMessage);

      if (err instanceof Error &&
        err.message.includes('Failed to create conversation') &&
        onConversationError) {
        onConversationError(err.message);
      }
    } finally {
      console.log('Setting isProcessing to false (sendMessage)', { isAuthenticated, useStreaming });
      setIsProcessing(false);
    }
  }, [currentConversationId, createConversation, onConversationError, onTitleUpdate, streamAIResponse, streamGuestAIResponse]);

  // Clear messages (and guest session if not authenticated)
  const clearMessages = useCallback(async (isAuthenticated: boolean = false) => {
    // Stop any ongoing streaming
    stopStreaming();

    setMessages([]);
    setError(null);
    setStreamingMessage('');

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
  }, [stopStreaming]);

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
    isFetchingMessages,
    message,
    error,
    streamingMessage,
    isStreaming,
    messagesEndRef: messagesEndRef as RefObject<HTMLDivElement>,
    setMessage,
    fetchMessages,
    fetchGuestMessages,
    sendMessage,
    clearMessages,
    scrollToBottom,
    initializeGuestSession,
    stopStreaming
  };
};