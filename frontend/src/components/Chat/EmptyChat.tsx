import React from 'react';

const EmptyChat: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center h-full">
      <h1 className="text-3xl font-medium mb-4">
        Welcome to Akuru AI
      </h1>
      <div className="text-gray-400 mb-4 text-center">
        <span className="whitespace-pre-wrap tracking-tight text-[#F9D8B5]">
          Start chatting with Akuru in English or Dhivehi
        </span>
      </div>
    </div>
  );
};

export default EmptyChat;