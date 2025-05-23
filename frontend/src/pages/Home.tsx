// Updated Home component with guest support
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ChatLayout from '../components/Layout/ChatLayout';
import GuestChatLayout from '../components/Layout/GuestChatLayout';
import ChatMessages from '../components/Chat/ChatMessages';
import ChatInput from '../components/Chat/ChatInput';
import EmptyChat from '../components/Chat/EmptyChat';
import { RefObject } from 'react';

// Custom hooks
import { useAuth } from '../hooks/useAuth';
import { useConversations } from '../hooks/useConversations';
import { useChatMessages } from '../hooks/useChatMessages';

// Error Alert Component
const ErrorAlert: React.FC<{ message: string; onClose: () => void }> = ({ message, onClose }) => (
  <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50">
    <div className="bg-red-500 text-white px-4 py-2 rounded-md shadow-lg flex items-center">
      <span>{message}</span>
      <button className="ml-3 font-bold text-xl" onClick={onClose}>
        &times;
      </button>
    </div>
  </div>
);

const Home: React.FC = () => {
  const navigate = useNavigate();
  
  // Auth state
  const {
    userData,
    isLoading: authLoading,
    error: authError,
    isAuthenticated
  } = useAuth();

  // Error alert state
  const [errorAlert, setErrorAlert] = useState<string | null>(null);

  // Handle errors from any source
  const handleError = useCallback((errorMessage: string) => {
    console.log('Showing error alert:', errorMessage);
    setErrorAlert(errorMessage);
    // Auto-hide after 5 seconds
    setTimeout(() => setErrorAlert(null), 5000);
  }, []);

  // Conversation state (only for authenticated users)
  const {
    conversations,
    currentConversation,
    error: conversationsError,
    fetchConversations,
    createConversation,
    selectConversation,
    handleNewChat,
    formatConversationTitle
  } = useConversations();

  // Chat messages state
  const {
    messages,
    isProcessing,
    message,
    error: messagesError,
    messagesEndRef,
    setMessage,
    fetchMessages,
    fetchGuestMessages,
    sendMessage,
    clearMessages,
    initializeGuestSession
  } = useChatMessages(currentConversation, createConversation, handleError);

  // Consolidate errors from all sources
  useEffect(() => {
    const firstError = authError || conversationsError || messagesError;
    if (firstError) {
      handleError(firstError);
    }
  }, [authError, conversationsError, messagesError, handleError]);

  // Initialize based on authentication status
  useEffect(() => {
    if (isAuthenticated) {
      // Fetch conversations for authenticated users
      fetchConversations().catch((err) => {
        handleError(`Failed to load conversations: ${err instanceof Error ? err.message : String(err)}`);
      });
    } else {
      // Initialize guest session and fetch any existing messages
      initializeGuestSession().then(() => {
        fetchGuestMessages();
      }).catch((err) => {
        console.error('Error initializing guest session:', err);
      });
    }
  }, [isAuthenticated, fetchConversations, fetchGuestMessages, initializeGuestSession, handleError]);

  // Fetch messages when conversation is selected (authenticated users only)
  useEffect(() => {
    if (isAuthenticated && currentConversation) {
      fetchMessages(currentConversation).catch((err) => {
        handleError(`Failed to load messages: ${err instanceof Error ? err.message : String(err)}`);
      });
    } else if (isAuthenticated && !currentConversation) {
      // Clear messages when no conversation is selected for authenticated users
      clearMessages(true);
    }
  }, [currentConversation, fetchMessages, clearMessages, isAuthenticated, handleError]);

  // Navigation handlers
  const handleNavigateToLogin = useCallback(() => {
    navigate('/login');
  }, [navigate]);

  const handleNavigateToSignUp = useCallback(() => {
    navigate('/signup');
  }, [navigate]);

  // Message handlers
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      sendMessage(message, isAuthenticated).catch((err) => {
        handleError(`Failed to send message: ${err instanceof Error ? err.message : String(err)}`);
      });
    },
    [message, isAuthenticated, sendMessage, handleError]
  );

  // Conversation handlers
  const handleSelectConversation = useCallback(
    (id: number) => {
      selectConversation(id);
    },
    [selectConversation]
  );

  // New chat handler
  const handleNewChatClick = useCallback(() => {
    if (isAuthenticated) {
      handleNewChat();
    } else {
      // For guests, clear the session
      clearMessages(false);
    }
  }, [isAuthenticated, handleNewChat, clearMessages]);

  // Render the appropriate chat content
  const renderChatContent = () => {
    // If we have messages, show them
    if (messages.length > 0) {
      return (
        <ChatMessages
          messages={messages}
          messagesEndRef={messagesEndRef as RefObject<HTMLDivElement>}
        />
      );
    }
    
    // Otherwise show empty state
    return (
      <EmptyChat
        isAuthenticated={isAuthenticated}
        userData={userData}
        isLoading={authLoading}
        error={null}
      />
    );
  };

  // Error alert component
  const errorAlertComponent = errorAlert && (
    <ErrorAlert message={errorAlert} onClose={() => setErrorAlert(null)} />
  );

  // SIMPLIFIED: Only two states - Authenticated or Guest
  if (isAuthenticated) {
    // Authenticated user - Full experience with sidebar and DB storage
    return (
      <>
        {errorAlertComponent}
        
        <ChatLayout
          conversations={conversations}
          currentConversation={currentConversation}
          userData={userData}
          onNewChat={handleNewChat}
          onSelectConversation={handleSelectConversation}
          formatConversationTitle={formatConversationTitle}
        >
          {/* Scrollable Middle Content */}
          <div className="flex-1 overflow-y-auto">
            <div className="h-full p-6">
              {renderChatContent()}
            </div>
          </div>

          {/* Fixed Bottom Input */}
          <ChatInput
            message={message}
            setMessage={setMessage}
            isAuthenticated={isAuthenticated}
            isProcessing={isProcessing}
            onSubmit={handleSubmit}
          />
        </ChatLayout>
      </>
    );
  } else {
    // Guest user 
    return (
      <>
        {errorAlertComponent}
        
        <GuestChatLayout
          onLogin={handleNavigateToLogin}
          onSignUp={handleNavigateToSignUp}
          onNewChat={handleNewChatClick}
        >
          {/* Chat Content */}
          <div className="flex-1 overflow-y-auto">
            <div className="h-full p-6">
              {renderChatContent()}
            </div>
          </div>

          {/* Chat Input */}
          <ChatInput
            message={message}
            setMessage={setMessage}
            isAuthenticated={isAuthenticated}
            isProcessing={isProcessing}
            onSubmit={handleSubmit}
          />
        </GuestChatLayout>
      </>
    );
  }
};

export default Home;