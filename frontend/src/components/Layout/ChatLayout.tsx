import React, { ReactNode } from 'react';
import Sidebar from '../Sidebar/Sidebar';
import ChatHeader from '../Chat/ChatHeader';
import { Conversation } from '@/types';


interface ChatLayoutProps {
  conversations: Conversation[];
  currentConversation: number | null;
  userData: {
    name: string;
    email: string;
  };
  onNewChat: () => void;
  onSelectConversation: (id: number) => void;
  formatConversationTitle: (conversation: Conversation) => string;
  children: ReactNode;
}

const ChatLayout: React.FC<ChatLayoutProps> = ({
  conversations,
  currentConversation,
  userData,
  onNewChat,
  onSelectConversation,
  formatConversationTitle,
  children
}) => {
  return (
    <div className="flex h-screen bg-[#292929] text-white">
      {/* Sidebar */}
      <Sidebar
        conversations={conversations}
        currentConversation={currentConversation}
        userData={userData}
        onNewChat={onNewChat}
        onSelectConversation={onSelectConversation}
        formatConversationTitle={formatConversationTitle}
      />
      
      {/* Main content area */}
      <div className="flex-1 flex flex-col h-screen">
        {/* Header */}
        <ChatHeader />
        
        {/* Content */}
        {children}
      </div>
    </div>
  );
};

export default ChatLayout;