import React from 'react';
import Icon from '@mdi/react';
import { mdiLoading, mdiArrowRight } from '@mdi/js';

interface ChatInputProps {
  message: string;
  setMessage: (message: string) => void;
  isAuthenticated: boolean;
  isProcessing: boolean;
  onSubmit: (e: React.FormEvent) => void;
}

const ChatInput: React.FC<ChatInputProps> = ({
  message,
  setMessage,
  isAuthenticated,
  isProcessing,
  onSubmit
}) => {
  return (
    <div className="p-6 bg-[#292929]">
      <form onSubmit={onSubmit} className="relative w-full max-w-3xl mx-auto">
        <input
          type="text"
          className="w-full px-4 py-3 bg-transparent text-[#E9D8B5] placeholder-[#E9D8B5] border border-[#E9D8B5] rounded-full focus:outline-none focus:ring-1 focus:ring-[#E9D8B5]"
          placeholder="Type a message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={!isAuthenticated || isProcessing}
        />
        <button
          type="submit"
          disabled={!isAuthenticated || isProcessing || !message.trim()}
          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[#E9D8B5] hover:text-white transition-colors disabled:opacity-50"
        >
          {isProcessing ? (
            <Icon path={mdiLoading} size={1} className="animate-spin" />
          ) : (
            <Icon className='text-[#E9D8B5]' path={mdiArrowRight} size={1} />
          )}
        </button>
      </form>
      <div className="flex justify-center text-xs text-gray-400 mt-2">
        <div className='font-bold'>Akuru can make mistakes</div>
        <div className='font-bold ml-5'>...</div>
        <div className='font-bold ml-5'>އަކުރަށް ގޯސްކޮށްވެސް ބުނެވިދާނެ</div>
      </div>
    </div>
  );
};

export default ChatInput;