import React from 'react';
import Icon from '@mdi/react';
import { mdiAccountCircle } from '@mdi/js';
import { Conversation, UserData } from '../../types';
import NewChatButton from './NewChatButton';
import ConversationItem from './ConversationItem';

interface SidebarProps {
  userData: UserData;
  conversations: Conversation[];
  currentConversation: number | null;
  handleNewChat: () => void;
  handleSelectConversation: (id: number) => void;
  formatConversationTitle: (conversation: Conversation) => string;
}

const Sidebar: React.FC<SidebarProps> = ({
  userData,
  conversations,
  currentConversation,
  handleNewChat,
  handleSelectConversation,
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
      
      <NewChatButton onClick={handleNewChat} />
      
      <div className="px-4 py-2 mt-2">
        <h3 className="text-sm font-medium text-white">Recents</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {conversations.map((conversation) => (
          <ConversationItem
            key={conversation.id}
            conversation={conversation}
            isActive={currentConversation === conversation.id}
            onClick={() => handleSelectConversation(conversation.id)}
            title={formatConversationTitle(conversation)}
          />
        ))}
      </div>
      
      <div className="p-4 border-t border-[#292929] flex items-center">
        <Icon path={mdiAccountCircle} size={1} className='text-[#E9D8B5]' />
        <span className="text-sm ml-3">{userData.email || 'Loading...'}</span>
      </div>
    </div>
  );
};

export default Sidebar;