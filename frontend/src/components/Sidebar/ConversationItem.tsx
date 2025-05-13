import React from 'react';

interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onSelect: (id: number) => void;
  formatTitle: (conversation: Conversation) => string;
  isCollapsed: boolean;
}

const ConversationItem: React.FC<ConversationItemProps> = ({
  conversation,
  isActive,
  onSelect,
  formatTitle,
  isCollapsed
}) => {
  return (
    <div
      className={`flex items-center px-4 py-3 mx-4 ${isActive ? 'bg-[#292929]' : 'hover:bg-[#292929]'} rounded-lg transition-all duration-200 cursor-pointer hover:shadow-md`}
      onClick={() => onSelect(conversation.id)}
    >
      <div className="w-6 h-6 flex items-center justify-center mr-3">
        <svg version="1.0" xmlns="http://www.w3.org/2000/svg"
          width="512.000000pt" height="512.000000pt" viewBox="0 0 512.000000 512.000000"
          preserveAspectRatio="xMidYMid meet">
          <g transform="translate(0.000000,512.000000) scale(0.100000,-0.100000)"
            fill="#E9D8B5" stroke="none">
            <path d="M1495 4844 c-273 -24 -395 -50 -528 -112 -310 -145 -562 -441 -641
                -752 -48 -190 -51 -263 -51 -1190 l0 -865 23 -84 c93 -341 356 -601 701 -693
                54 -14 121 -21 231 -25 138 -5 157 -7 178 -26 26 -24 27 -45 6 -129 -81 -315
                244 -592 539 -460 23 11 185 121 360 247 328 233 414 286 533 323 115 35 187
                42 479 42 439 0 595 20 775 97 302 130 532 359 656 655 90 213 97 294 91 1143
                -4 734 -9 806 -57 983 -81 296 -324 581 -614 722 -116 56 -209 84 -363 107
                -94 14 -245 17 -1193 18 -597 1 -1103 1 -1125 -1z m2303 -337 c194 -34 330
                -105 467 -242 140 -140 209 -274 243 -477 15 -91 17 -191 17 -848 0 -744 0
                -745 -23 -825 -78 -276 -271 -498 -526 -604 -134 -56 -183 -61 -631 -71 -434
                -9 -463 -12 -621 -65 -140 -47 -247 -111 -574 -344 -290 -207 -328 -232 -359
                -229 -23 2 -40 12 -54 30 -19 26 -19 28 -2 91 54 200 -32 395 -212 479 -64 30
                -73 32 -242 38 -152 6 -186 11 -249 33 -166 58 -300 173 -371 318 -76 156 -73
                107 -68 1062 5 921 6 951 61 1107 69 201 267 407 472 493 74 32 188 55 319 66
                55 5 586 8 1180 6 943 -2 1092 -4 1173 -18z"/>
            <path d="M1611 3174 c-132 -66 -157 -229 -51 -334 105 -106 268 -81 334 51 43
                88 30 176 -39 244 -68 69 -156 82 -244 39z"/>
            <path d="M2480 3184 c-107 -46 -159 -174 -115 -282 64 -152 273 -172 369 -34
                40 57 48 149 18 208 -54 104 -172 151 -272 108z"/>
            <path d="M3342 3189 c-19 -6 -53 -30 -77 -53 -70 -70 -83 -155 -39 -245 67
                -134 244 -158 342 -45 146 165 -11 404 -226 343z"/>
          </g>
        </svg>
      </div>
      {!isCollapsed && <span className="text-sm">{formatTitle(conversation)}</span>}
    </div>
  );
};

export default ConversationItem;