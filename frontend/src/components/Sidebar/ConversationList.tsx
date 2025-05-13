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
  isCollapsed: boolean;
}

const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  currentConversation,
  onSelectConversation,
  formatConversationTitle,
  isCollapsed  // Make sure to include this in the destructuring
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
          isCollapsed={isCollapsed}  // Pass the prop to ConversationItem
        />
      ))}
    </div>
  );
};

export default ConversationList;