// pages/Home.tsx
import React, { useEffect, useRef } from 'react';
import AuthModal from '../components/Auth/AuthModal';
import ChatHeader from '../components/Chat/ChatHeader';
import ChatInput from '../components/Chat/ChatInput';
// import ChatMessages from '../components/Chat/ChatMessages';
import EmptyChat from '../components/Chat/EmptyChat';
import Sidebar from '../components/Sidebar/Sidebar';
import { useAuth } from '../hooks/useAuth';
import { useConversations } from '../hooks/useConversations';
import { useChatMessages } from '../hooks/useChatMessages';

const Home: React.FC = () => {
  // Custom hooks
  const {
    userData,
    isLoading,
    error,
    isAuthenticated,
    isTryingFirst,
    handleSignUp,
    handleLogin,
    handleTryFirst,
    handleCloseModal,
    showAuthModal
  } = useAuth();

  const {
    conversations,
    currentConversation,
    handleNewChat,
    handleSelectConversation,
    createNewConversation,
    refreshConversations,
    formatConversationTitle
  } = useConversations(isAuthenticated);

  const {
    messages,
    messageInput,
    setMessageInput,
    isProcessing,
    messagesEndRef,
    loadMessages,
    handleSendMessage,
    scrollToBottom
  } = useChatMessages();

  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Load messages when conversation changes
  useEffect(() => {
    if (currentConversation !== null) {
      loadMessages(currentConversation);
    }
  }, [currentConversation, loadMessages]);

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await handleSendMessage(messageInput, currentConversation, createNewConversation, isTryingFirst);
    
    // Refresh conversations list after sending a message
    if (isAuthenticated) {
      refreshConversations();
    }
  };

  // Render not authenticated state
  const renderNotAuthenticated = () => (
    <div className="flex flex-col items-center justify-center h-full">
      {isLoading ? (
        <h1 className="text-3xl font-medium mb-4">Loading...</h1>
      ) : (
        <>
          <h1 className="text-3xl font-medium mb-4">
            Hello, {userData.name}
          </h1>
          {error && (
            <div className="bg-red-500 bg-opacity-20 p-4 rounded-md mb-4">
              <p className="text-red-300">{error}</p>
            </div>
          )}
          <div className="text-center">
            <div className="text-gray-400 mb-4">
              <span className="whitespace-pre-wrap tracking-tight text-[#F9D8B5]">
                For a complete experience with saved conversations, please create an account or log in.
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );

  return (
    <>
      {!isAuthenticated && showAuthModal && !isTryingFirst && (
        <AuthModal
          isAuthenticated={isAuthenticated}
          onClose={handleCloseModal}
          onSignUp={handleSignUp}
          onLogin={handleLogin}
          onTryFirst={handleTryFirst}
        />
      )}
      
      <div className="flex h-screen bg-[#292929] text-white">
        {/* Sidebar */}
        <Sidebar
          userData={userData}
          conversations={conversations}
          currentConversation={currentConversation}
          handleNewChat={handleNewChat}
          handleSelectConversation={handleSelectConversation}
          formatConversationTitle={formatConversationTitle}
        />
        
        {/* Main content area */}
        <div className="flex-1 flex flex-col h-screen">
          {/* Fixed Header */}
          <ChatHeader />

          {/* Scrollable Middle Content */}
          <div className="flex-1 overflow-y-auto" ref={chatContainerRef}>
            <div className="h-full p-6 flex flex-col justify-end">
              {isAuthenticated ? (
                messages.length === 0 ? (
                  <EmptyChat />
                ) : (
                  <div className="space-y-6 min-h-0">
                    {messages.map((message, index) => (
                      <div
                        key={index}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[70%] rounded-lg p-4 ${message.role === 'user'
                            ? 'bg-[#E9D8B5] text-black'
                            : 'bg-[#1E1E1E] text-white'
                            }`}
                        >
                          {message.content}
                        </div>
                      </div>
                    ))}
                    {/* This div is used to scroll to bottom */}
                    <div ref={messagesEndRef} />
                  </div>
                )
              ) : (
                renderNotAuthenticated()
              )}
            </div>
          </div>

          {/* Fixed Bottom Input */}
          <ChatInput
            message={messageInput}
            setMessage={setMessageInput}
            handleSubmit={handleSubmit}
            isProcessing={isProcessing}
            isDisabled={!isAuthenticated || isProcessing}
          />
        </div>
      </div>
    </>
  );
};

export default Home;