import React from 'react';
import NewChatButton from './NewChatButton';
import ConversationList from './ConversationList';
import UserProfile from './UserProfile';
import { Conversation } from '@/types';


interface SidebarProps {
  conversations: Conversation[];
  currentConversation: number | null;
  userData: {
    name: string;
    email: string;
  };
  onNewChat: () => void;
  onSelectConversation: (id: number) => void;
  formatConversationTitle: (conversation: Conversation) => string;
}

const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  currentConversation,
  userData,
  onNewChat,
  onSelectConversation,
  formatConversationTitle
}) => {
  return (
    <div className="h-full w-80 bg-[#1E1E1E] flex flex-col flex-shrink-0">
      <div className="p-4 flex items-center justify-between">
        <button className="p-2">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="#E9D8B5">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
      <NewChatButton onClick={onNewChat} />
      <div className="px-4 py-2 mt-2">
        <h3 className="text-sm font-medium text-white">Recents</h3>
      </div>
      <ConversationList
        conversations={conversations}
        currentConversation={currentConversation}
        onSelectConversation={onSelectConversation}
        formatConversationTitle={formatConversationTitle}
      />
      <UserProfile email={userData.email} />
    </div>
  );
};

export default Sidebar;