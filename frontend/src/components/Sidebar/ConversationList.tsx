import React from 'react';
import ConversationItem from './ConversationItem';

interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface ConversationListProps {
  conversations: Conversation[];
  currentConversation: number | null;
  onSelectConversation: (id: number) => void;
  formatConversationTitle: (conversation: Conversation) => string;
}

const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  currentConversation,
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
        />
      ))}
    </div>
  );
};

export default ConversationList;