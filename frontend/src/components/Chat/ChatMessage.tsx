import React from 'react';
import { Message } from '../../types';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  return (
    <div
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
  );
};

export default ChatMessage;