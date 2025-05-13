import React, { useState } from 'react';
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
  onLogout?: () => Promise<void> | void; 
  loginPageUrl?: string; 
}

const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  currentConversation,
  userData,
  onNewChat,
  onSelectConversation,
  formatConversationTitle,
  onLogout = async () => {
    localStorage.removeItem('authToken'); 
    sessionStorage.clear(); 
  },
  loginPageUrl = '/login'
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false); // Default to expanded state
  const [isProfileExpanded, setIsProfileExpanded] = useState(false); // Track profile expanded state
 
  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed);
  };
  
  const expandSidebar = () => {
    setIsCollapsed(false);
  };
 
  const handleProfileToggle = (expanded: boolean) => {
    setIsProfileExpanded(expanded);
  };
 
  return (
    <div
      className={`h-full ${isCollapsed ? 'w-16' : 'w-80'} bg-[#1E1E1E] flex flex-col flex-shrink-0 transition-all duration-300`}
    >
      <div className='flex flex-col h-full'>
        <div className={`p-5 flex items-center ${isCollapsed ? 'justify-center' : 'justify-between'} ${isProfileExpanded ? 'blur' : ''}`}>
          <button className="p-1" onClick={toggleSidebar}>
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="#E9D8B5">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
        <div className={`${isProfileExpanded ? 'blur' : ''}`}>
          <NewChatButton onClick={onNewChat} isCollapsed={isCollapsed} />
        </div>
        {/* Conversation list - only visible when expanded */}
        {!isCollapsed ? (
          <>
            <div className={`px-4 py-2 mt-2 ${isProfileExpanded ? 'blur' : ''}`}>
              <h3 className="text-sm font-medium text-white">Recents</h3>
            </div>
            <div className={`flex-1 overflow-y-auto ${isProfileExpanded ? 'blur' : ''}`}>
              <ConversationList
                conversations={conversations}
                currentConversation={currentConversation}
                onSelectConversation={onSelectConversation}
                formatConversationTitle={formatConversationTitle}
                isCollapsed={isCollapsed}
              />
            </div>
          </>
        ) : (
          <div className="flex-grow"></div>
        )}
        <UserProfile
          email={userData.email}
          isCollapsed={isCollapsed}
          onProfileToggle={handleProfileToggle}
          onExpandSidebar={expandSidebar}
          onLogout={onLogout}
          loginPageUrl={loginPageUrl}
        />
      </div>
    </div>
  );
};

export default Sidebar;