import React from 'react';
import { Conversation } from '@/types';
import ConversationItem from './ConversationItem';

interface ConversationListProps {
  conversations: Conversation[];
  currentConversation: number | null;
  isCollapsed: boolean;
  onSelectConversation: (id: number) => void;
  formatConversationTitle: (conversation: Conversation) => string;
}

const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  currentConversation,
  isCollapsed,  
  onSelectConversation,
  formatConversationTitle
}) => {
  return (
    <div className="flex-1 overflow-y-auto">
      {conversations.map((conversation) => (
        <ConversationItem
          key={conversation.id}
          conversation={conversation}
          isActive={currentConversation === conversation.id}
          onSelect={onSelectConversation}
          formatTitle={formatConversationTitle}
          isCollapsed={isCollapsed}  
        />
      ))}
    </div>
  );
};

export default ConversationList;