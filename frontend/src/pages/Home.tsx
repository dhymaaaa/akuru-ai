// pages/Home.tsx
import React, { useState, useEffect, useCallback } from 'react';
import AuthModal from '../components/Auth/AuthModal';
import ChatLayout from '../components/Layout/ChatLayout';
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
      <button 
        className="ml-3 font-bold text-xl"
        onClick={onClose}
      >
        &times;
      </button>
    </div>
  </div>
);


const Home: React.FC = () => {
  // Auth state
  const {
    userData,
    isLoading: authLoading,
    error: authError,
    isAuthenticated,
    handleSignUp,
    handleLogin,
    handleTryFirst
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

  // Conversation state
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
    sendMessage,
    clearMessages
  } = useChatMessages(currentConversation, createConversation, handleError);

  // UI state
  const [showAuthModal, setShowAuthModal] = useState<boolean>(true);
  const [isTryingFirst, setIsTryingFirst] = useState<boolean>(false);
  
  // Consolidate errors from all sources
  useEffect(() => {
    const firstError = authError || conversationsError || messagesError;
    if (firstError) {
      handleError(firstError);
    }
  }, [authError, conversationsError, messagesError, handleError]);

  // Fetch conversations when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      fetchConversations().catch((err) => {
        handleError(`Failed to load conversations: ${err instanceof Error ? err.message : String(err)}`);
      });
    }
  }, [isAuthenticated, fetchConversations, handleError]);

  // Fetch messages when conversation is selected
  useEffect(() => {
    if (currentConversation) {
      fetchMessages(currentConversation).catch((err) => {
        handleError(`Failed to load messages: ${err instanceof Error ? err.message : String(err)}`);
      });
    } else {
      clearMessages();
    }
  }, [currentConversation, fetchMessages, clearMessages, handleError]);

  // Auth modal handlers
  const handleAuthSignUp = useCallback(() => {
    handleSignUp();
  }, [handleSignUp]);

  const handleAuthLogin = useCallback(() => {
    handleLogin();
  }, [handleLogin]);

  const handleAuthTryFirst = useCallback(() => {
    const success = handleTryFirst();
    if (success) {
      setShowAuthModal(false);
      setIsTryingFirst(true);
    }
  }, [handleTryFirst]);

  const handleCloseModal = useCallback(() => {
    setShowAuthModal(false);
  }, []);

  // Message handlers
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(message, isTryingFirst).catch((err) => {
      handleError(`Failed to send message: ${err instanceof Error ? err.message : String(err)}`);
    });
  }, [message, isTryingFirst, sendMessage, handleError]);

  // Conversation handlers
  const handleSelectConversation = useCallback((id: number) => {
    selectConversation(id);
  }, [selectConversation]);

  return (
    <>
      {/* Error Alert */}
      {errorAlert && (
        <ErrorAlert 
          message={errorAlert} 
          onClose={() => setErrorAlert(null)} 
        />
      )}
      
      {/* Auth Modal */}
      {!isAuthenticated && showAuthModal && !isTryingFirst && (
        <AuthModal
          isAuthenticated={isAuthenticated}
          onClose={handleCloseModal}
          onSignUp={handleAuthSignUp}
          onLogin={handleAuthLogin}
          onTryFirst={handleAuthTryFirst}
        />
      )}
      
      {/* Main Layout */}
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
            {isAuthenticated || isTryingFirst ? (
              messages.length === 0 ? (
                // Empty state for chat
                <EmptyChat 
                  isAuthenticated={true}
                  userData={userData}
                  isLoading={authLoading}
                  error={null} // Using the alert for errors instead
                />
              ) : (
                // Chat messages
                <ChatMessages
                  messages={messages}
                  messagesEndRef={messagesEndRef as RefObject<HTMLDivElement>}
                />
              )
            ) : (
              // Not authenticated view
              <EmptyChat 
                isAuthenticated={false}
                userData={userData}
                isLoading={authLoading}
                error={null} // Using the alert for errors instead
              />
            )}
          </div>
        </div>

        {/* Fixed Bottom Input */}
        <ChatInput
          message={message}
          setMessage={setMessage}
          isAuthenticated={isAuthenticated || isTryingFirst}
          isProcessing={isProcessing}
          onSubmit={handleSubmit}
        />
      </ChatLayout>
    </>
  );
};

export default Home;