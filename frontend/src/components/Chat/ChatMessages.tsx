import React, { RefObject } from 'react';

interface Message {
  id?: number;
  role: 'user' | 'akuru';
  content: string;
  created_at?: string;
}

interface ChatMessagesProps {
  messages: Message[];
  // Change here to accept null in the type
  messagesEndRef: RefObject<HTMLDivElement | null>;
}

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages, messagesEndRef }) => {
  return (
    <div className="space-y-6">
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
  );
};

export default ChatMessages;