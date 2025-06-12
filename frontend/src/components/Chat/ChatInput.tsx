import React, { useRef, useEffect } from 'react';
import Icon from '@mdi/react';
import { mdiLoading, mdiArrowRight } from '@mdi/js';

interface ChatInputProps {
  message: string;
  isProcessing: boolean;
  setMessage: (message: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

const ChatInput: React.FC<ChatInputProps> = ({
  message,
  setMessage,
  isProcessing,
  onSubmit
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isMultiLine, setIsMultiLine] = React.useState(false);

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto';
     
      // Calculate the new height (max 3 lines)
      const lineHeight = 24; // Reduced line height
      const maxHeight = lineHeight * 3 + 12; // 3 lines max + padding
      const newHeight = Math.min(textarea.scrollHeight, maxHeight);
     
      textarea.style.height = `${newHeight}px`;
     
      // Check if content spans multiple lines - adjusted for new minHeight
      const singleLineHeight = 40; // Reduced minHeight
      setIsMultiLine(newHeight > singleLineHeight);
    }
  }, [message]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const formEvent = e as unknown as React.FormEvent;
      onSubmit(formEvent);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(e);
  };

  return (
    <div className="p-6 bg-[#292929]">
      <style>
        {`
          .scrollbar-hide::-webkit-scrollbar {
            display: none;
          }
        `}
      </style>
      
      <div className="relative w-full max-w-3xl mx-auto">
        <div className="relative flex items-end">
          <textarea
            ref={textareaRef}
            className={`w-full px-4 py-2 pr-12 bg-transparent text-[#E9D8B5] placeholder-[#E9D8B5] border border-[#E9D8B5] focus:outline-none focus:ring-1 focus:ring-[#E9D8B5] resize-none overflow-y-auto leading-6 scrollbar-hide transition-all duration-200 ${
              isMultiLine ? 'rounded-2xl' : 'rounded-full'
            }`}
            placeholder="Type a message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isProcessing}
            rows={1}
            style={{
              minHeight: '40px', // Reduced from 48px to 40px
              maxHeight: '84px', // Maximum height for 3 lines
              scrollbarWidth: 'none', // Firefox
              msOverflowStyle: 'none' // IE and Edge
            }}
          />
          <button
            type="button"
            onClick={handleFormSubmit}
            disabled={isProcessing || !message.trim()}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[#E9D8B5] hover:text-white transition-colors disabled:opacity-50 flex-shrink-0"
          >
            {isProcessing ? (
              <Icon path={mdiLoading} size={0.8} className="animate-spin" />
            ) : (
              <Icon className='text-[#E9D8B5]' path={mdiArrowRight} size={0.8} />
            )}
          </button>
        </div>
      </div>
      
      <div className="flex justify-center text-xs text-gray-400 mt-2">
        <div className='font-bold'>Akuru can make mistakes</div>
        <div className='font-bold ml-5'>...</div>
        <div className='font-bold ml-5'>އަކުރަށް ގޯސްކޮށްވެސް ބުނެވިދާނެ</div>
      </div>
    </div>
  );
};

export default ChatInput;