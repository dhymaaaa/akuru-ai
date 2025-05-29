import React, { RefObject } from 'react';
import { Message } from '@/types';

interface ChatMessagesProps {
  messages: Message[];
  messagesEndRef: RefObject<HTMLDivElement | null>;
}

// Helper function to detect Dhivehi text
const containsDhivehi = (text: string): boolean => {
  return /[\u0780-\u07BF]/.test(text);
};

// Function to process mixed content paragraphs
const formatMessageContent = (content: string) => {
  // If there's no Dhivehi text, return as is
  if (!containsDhivehi(content)) {
    return content;
  }

  // Split content by line breaks
  const lines = content.split('\n');
  return lines.map((line, index) => {
    // Check if line contains Dhivehi
    if (containsDhivehi(line)) {
      // Check if the line is a mix of Dhivehi and non-Dhivehi
      const hasMixedContent = /[a-zA-Z0-9]/.test(line) && containsDhivehi(line);
      
      if (hasMixedContent) {
        // For mixed content, we need to split into paragraphs
        // This simple version just puts the Dhivehi in a separate block
        // First, find all Dhivehi segments
        const dhivehiSegments = line.match(/[\u0780-\u07BF]+[^\n]*/g) || [];
        
        // Replace Dhivehi segments with placeholder to get non-Dhivehi parts
        let nonDhivehiContent = line;
        dhivehiSegments.forEach((segment, i) => {
          nonDhivehiContent = nonDhivehiContent.replace(segment, `__DHIVEHI_${i}__`);
        });
        
        // Split non-Dhivehi by placeholders
        const parts = nonDhivehiContent.split(/__DHIVEHI_\d+__/);
        
        // Reconstruct with proper styling
        const result = [];
        
        for (let i = 0; i < parts.length; i++) {
          // Add non-Dhivehi part if not empty
          if (parts[i].trim()) {
            result.push(
              <span key={`non-dhivehi-${index}-${i}`} className="text-left ltr inline">
                {parts[i]}
              </span>
            );
          }
          
          // Add Dhivehi part if available
          if (i < dhivehiSegments.length) {
            result.push(
              <div key={`dhivehi-${index}-${i}`} className="block rtl text-right mt-3">
                {dhivehiSegments[i]}
              </div>
            );
          }
        }
        
        return (
          <React.Fragment key={`mixed-${index}`}>
            {index > 0 && <br />}
            {result}
          </React.Fragment>
        );
      } else {
        // For pure Dhivehi lines
        return (
          <React.Fragment key={`dhivehi-line-${index}`}>
            {index > 0 && <br />}
            <div className="block rtl text-right mt-3">{line}</div>
          </React.Fragment>
        );
      }
    } else {
      // For pure non-Dhivehi lines
      return (
        <React.Fragment key={`non-dhivehi-line-${index}`}>
          {index > 0 && <br />}
          <span className="text-left ltr">{line}</span>
        </React.Fragment>
      );
    }
  });
};

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages, messagesEndRef }) => {
  // Custom SVG component for the Akuru icon
  const AkuruIcon = () => (
    <svg
      width="36"
      height="32"
      viewBox="0 0 154 130"
      xmlns="http://www.w3.org/2000/svg"
      className="fill-current"
    >
      <g fill="#E9D8B5" transform="translate(0.000000,130.000000) scale(0.100000,-0.100000)">
        <path d="M299 996 c-82 -25 -111 -86 -107 -221 l3 -90 30 0 30 0 5 107 c8 164,
        -20 152 368 158 300 5 317 6 320 24 2 10 -2 22 -10 27 -20 13 -596 9 -639 -5z"/>
        <path d="M1005 996 c-16 -12 -17 -16 -6 -30 7 -9 28 -16 45 -16 17 0 41 -7 52
        -15 39 -27 46 -63 42 -238 -4 -228 18 -211 -278 -215 l-229 -3 -68 -65 -68
        -64 -3 52 c-2 29 -8 58 -14 65 -6 8 -34 13 -72 13 -90 0 -128 22 -143 84 -14
        56 -28 69 -56 54 -16 -8 -19 -18 -15 -53 10 -85 83 -144 181 -145 l47 0 0
        -100 c0 -89 2 -100 18 -100 9 0 62 45 117 100 l100 100 218 0 c239 0 252 3
        301 61 l27 32 -3 208 -3 208 -28 29 c-44 46 -126 65 -162 38z"/>
        <path d="M734 788 c-16 -13 -38 -31 -49 -41 -38 -36 -163 -128 -171 -126 -25
        4 -35 -3 -32 -23 8 -55 108 -19 231 84 33 27 61 47 64 44 3 -2 -12 -30 -32
        -60 -49 -74 -38 -107 23 -70 44 26 72 70 84 128 9 43 9 58 -1 70 -20 24 -83
        20 -117 -6z"/>
      </g>
    </svg>
  );

  return (
    <div className="w-full px-6 py-4">
      <div className="max-w-5xl mx-auto space-y-8">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-2xl ${
                message.role === 'user'
                  ? 'bg-[#434343] text-white rounded-tr-none'
                  : 'border border-[#434343] text-white rounded-tl-none'
              }`}
            >
              {message.role === 'akuru' ? (
                <div className="flex items-start">
                  <div className="flex-shrink-0 mr-3">
                    <AkuruIcon />
                  </div>
                  <div className="flex-1">
                    {formatMessageContent(message.content)}
                  </div>
                </div>
              ) : (
                formatMessageContent(message.content)
              )}
            </div>
          </div>
        ))}
        {/* This div is used to scroll to bottom */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatMessages;