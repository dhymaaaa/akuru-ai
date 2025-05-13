// NewChatButton.tsx - Without border in collapsed state
import React from 'react';

interface NewChatButtonProps {
  onClick: () => void;
  isCollapsed: boolean;
}

const NewChatButton: React.FC<NewChatButtonProps> = ({ onClick, isCollapsed }) => {
  return (
    <div className={`${isCollapsed ? 'flex justify-center' : 'px-4'}`}>
      {isCollapsed ? (
        // Simple icon without any container/border when collapsed
        <button onClick={onClick} className="p-1">
          <svg version="1.0" xmlns="http://www.w3.org/2000/svg" className="h-6 w-6"
            width="96.000000pt" height="96.000000pt" viewBox="0 0 96.000000 96.000000"
            preserveAspectRatio="xMidYMid meet">
            <g transform="translate(0.000000,96.000000) scale(0.100000,-0.100000)"
              fill="#E9D8B5" stroke="none">
              <path d="M600 893 c-147 -78 -160 -281 -23 -372 79 -53 160 -54 241 -4 59 36
                  102 113 102 183 0 113 -92 210 -208 218 -48 3 -66 -1 -112 -25z m118 -106 l3
                  -66 67 -3 c52 -2 67 -6 67 -18 0 -12 -15 -16 -67 -18 l-67 -3 -3 -67 c-2 -52
                  -6 -67 -18 -67 -12 0 -16 15 -18 67 l-3 67 -67 3 c-52 2 -67 6 -67 18 0 12 15
                  16 68 18 l67 3 0 63 c0 34 3 66 7 70 17 17 28 -6 31 -67z"/>
              <path d="M150 802 c-62 -31 -70 -61 -70 -280 0 -210 7 -247 54 -277 14 -9 43
                  -19 66 -22 l40 -6 0 -63 c0 -66 15 -94 49 -94 10 0 66 36 124 80 l106 80 128
                  0 c201 0 233 27 233 198 l0 93 -30 -23 c-28 -21 -30 -25 -30 -93 0 -62 -3 -74
                  -23 -93 -22 -20 -33 -22 -161 -22 l-137 0 -99 -75 -99 -75 -3 72 -3 73 -55 3
                  c-39 2 -61 9 -78 24 -21 21 -22 27 -22 218 0 252 -9 240 176 240 l130 0 11 30
                  11 30 -141 0 c-115 0 -149 -3 -177 -18z"/>
            </g>
          </svg>
        </button>
      ) : (
        // Full button with background when expanded
        <button
          onClick={onClick}
          className="flex items-center space-x-2 w-full rounded-lg px-4 py-3 bg-[#292929] transition hover:bg-[#363636]"
        >
          <svg version="1.0" xmlns="http://www.w3.org/2000/svg" className="h-5 w-5"
            width="96.000000pt" height="96.000000pt" viewBox="0 0 96.000000 96.000000"
            preserveAspectRatio="xMidYMid meet">
            <g transform="translate(0.000000,96.000000) scale(0.100000,-0.100000)"
              fill="#E9D8B5" stroke="none">
              <path d="M600 893 c-147 -78 -160 -281 -23 -372 79 -53 160 -54 241 -4 59 36
                  102 113 102 183 0 113 -92 210 -208 218 -48 3 -66 -1 -112 -25z m118 -106 l3
                  -66 67 -3 c52 -2 67 -6 67 -18 0 -12 -15 -16 -67 -18 l-67 -3 -3 -67 c-2 -52
                  -6 -67 -18 -67 -12 0 -16 15 -18 67 l-3 67 -67 3 c-52 2 -67 6 -67 18 0 12 15
                  16 68 18 l67 3 0 63 c0 34 3 66 7 70 17 17 28 -6 31 -67z"/>
              <path d="M150 802 c-62 -31 -70 -61 -70 -280 0 -210 7 -247 54 -277 14 -9 43
                  -19 66 -22 l40 -6 0 -63 c0 -66 15 -94 49 -94 10 0 66 36 124 80 l106 80 128
                  0 c201 0 233 27 233 198 l0 93 -30 -23 c-28 -21 -30 -25 -30 -93 0 -62 -3 -74
                  -23 -93 -22 -20 -33 -22 -161 -22 l-137 0 -99 -75 -99 -75 -3 72 -3 73 -55 3
                  c-39 2 -61 9 -78 24 -21 21 -22 27 -22 218 0 252 -9 240 176 240 l130 0 11 30
                  11 30 -141 0 c-115 0 -149 -3 -177 -18z"/>
            </g>
          </svg>
          <span>New chat</span>
        </button>
      )}
    </div>
  );
};

export default NewChatButton;