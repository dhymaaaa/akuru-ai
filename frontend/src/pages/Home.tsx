// Updated Home component with fixed AuthModal logic
import React, { useState, useEffect, useCallback } from 'react';
import AuthModal from '../components/Auth/AuthModal';
import ChatLayout from '../components/Layout/ChatLayout';
import ChatMessages from '../components/Chat/ChatMessages';
import ChatInput from '../components/Chat/ChatInput';
import EmptyChat from '../components/Chat/EmptyChat';
import { RefObject } from 'react';
import NonAuthChatLayout from '@/components/Layout/NonAuthChatLayout';

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

  // UI state
  const [showAuthModal, setShowAuthModal] = useState<boolean>(true);
  const [isTryingFirst, setIsTryingFirst] = useState<boolean>(false);

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

  // Consolidated auth/access state - a user has access if they're authenticated or trying first
  const hasAccessToChat = isAuthenticated || isTryingFirst;

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
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      sendMessage(message, isTryingFirst).catch((err) => {
        handleError(`Failed to send message: ${err instanceof Error ? err.message : String(err)}`);
      });
    },
    [message, isTryingFirst, sendMessage, handleError]
  );

  // Conversation handlers
  const handleSelectConversation = useCallback(
    (id: number) => {
      selectConversation(id);
    },
    [selectConversation]
  );

  // Render the appropriate chat content based on authentication state
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

  // FIXED: Always render the AuthModal if not authenticated and not trying first
  // and showAuthModal is true
  const shouldShowAuthModal = !isAuthenticated && !isTryingFirst && showAuthModal;

  // FIXED: Show error alert in all cases
  const errorAlertComponent = errorAlert && (
    <ErrorAlert message={errorAlert} onClose={() => setErrorAlert(null)} />
  );

  // Main render logic - UPDATED
  if (!hasAccessToChat) {
    return (
      <>
        {errorAlertComponent}
        
        {shouldShowAuthModal && (
          <AuthModal
            isAuthenticated={isAuthenticated}
            onClose={handleCloseModal}
            onSignUp={handleAuthSignUp}
            onLogin={handleAuthLogin}
            onTryFirst={handleAuthTryFirst}
          />
        )}
        
        <NonAuthChatLayout
          onLogin={handleAuthLogin}
          onSignUp={handleAuthSignUp}
          onTryFirst={handleAuthTryFirst}
        >
          <EmptyChat
            isAuthenticated={false}
            userData={userData}
            isLoading={authLoading}
            error={null}
          />
        </NonAuthChatLayout>
      </>
    );
  }

  // UPDATED: Different layouts for 'try first' vs authenticated users
  if (isTryingFirst && !isAuthenticated) {
    // First image layout - "Try first" experience (simplified UI)
    return (
      <>
        {errorAlertComponent}
        
        <div className="flex flex-col h-screen bg-gray-900 text-white">
          {/* Header */}
          <header className="flex justify-between items-center p-4 border-b border-gray-700">
            <div className="flex items-center">
              <div className="mr-4">
                <svg className="w-6 h-6" /* SVG for the chat icon */ />
              </div>
              <div className="text-xl font-light">
                <img src="/logo.svg" alt="Akuru" className="h-8" />
              </div>
            </div>
            <div className="flex gap-2">
              <button 
                onClick={handleAuthLogin}
                className="px-4 py-2 rounded-md bg-gray-800 hover:bg-gray-700"
              >
                Login
              </button>
              <button 
                onClick={handleAuthSignUp}
                className="px-4 py-2 rounded-md bg-gray-800 hover:bg-gray-700"
              >
                Register
              </button>
            </div>
          </header>
          
          {/* Main content */}
          <div className="flex-1 flex flex-col justify-center items-center p-4">
            <h1 className="text-2xl mb-2">Hello, {'{name}'}</h1>
            <p className="text-xl mb-8 text-gray-400">{'{Dhivehi text}'}</p>
            
            {/* Chat input */}
            <div className="w-full max-w-xl">
              <form onSubmit={handleSubmit} className="relative">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Type your message..."
                  className="w-full p-4 pr-12 rounded-full bg-gray-800 border border-gray-700 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="submit"
                  disabled={isProcessing || !message.trim()}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 rounded-full"
                >
                  <svg 
                    className={`w-6 h-6 ${isProcessing ? 'text-gray-500' : 'text-blue-500'}`}
                    xmlns="http://www.w3.org/2000/svg" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="currentColor" 
                    strokeWidth="2" 
                    strokeLinecap="round" 
                    strokeLinejoin="round"
                  >
                    <path d="M22 2L11 13M22 2L15 22L11 13L2 9L22 2Z" />
                  </svg>
                </button>
              </form>
              <p className="text-center text-sm text-gray-500 mt-2">
                Akuru can make mistakes • {'{Dhivehi text}'}
              </p>
            </div>
          </div>
        </div>
      </>
    );
  }
  
  // Second image layout - Authenticated user experience (full UI with sidebar)
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
          isAuthenticated={hasAccessToChat}
          isProcessing={isProcessing}
          onSubmit={handleSubmit}
        />
      </ChatLayout>
    </>
  );
};

export default Home;