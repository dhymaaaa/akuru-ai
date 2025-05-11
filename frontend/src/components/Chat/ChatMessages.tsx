import React from 'react';
import { Message } from '../../types';
import ChatMessage from './ChatMessage';
import EmptyChat from './EmptyChat';

interface ChatMessagesProps {
  messages: Message[];
  messagesEndRef: React.RefObject<HTMLDivElement>;
}

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages, messagesEndRef }) => {
  if (messages.length === 0) {
    return <EmptyChat />;
  }

  return (
    <div className="space-y-6 min-h-0">
      {messages.map((message, index) => (
        <ChatMessage key={index} message={message} />
      ))}
      {/* This div is used to scroll to bottom */}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;