import { useState, useEffect, useRef } from 'react';
import Icon from '@mdi/react';
import { mdiAccountCircle, mdiArrowRight, mdiLoading } from '@mdi/js';
import AuthModal from './Auth/AuthModal';

interface UserData {
  name: string;
  email: string;
}

interface Message {
  id?: number;
  role: 'user' | 'akuru';
  content: string;
  created_at?: string;
}

interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

const Home = () => {
  const [userData, setUserData] = useState<UserData>({ name: '', email: '' });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [showAuthModal, setShowAuthModal] = useState<boolean>(true);
  const [isTryingFirst, setIsTryingFirst] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch user data on component mount
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Check if token exists
        const token = localStorage.getItem('token');
        if (!token) {
          console.warn('No token found in localStorage');
          setUserData({ name: 'Guest', email: 'Guest account' });
          setIsAuthenticated(false);
          setIsLoading(false);
          return;
        }

        console.log('Token found, attempting to fetch user data');
        setIsAuthenticated(true);

        try {
          const response = await fetch('/api/user', {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });

          if (!response.ok) {
            const errorText = await response.text();
            console.error('API response not OK:', response.status, response.statusText, errorText);
            throw new Error(`Failed to fetch user data: ${response.status}`);
          }

          const responseText = await response.text();

          if (!responseText.trim()) {
            throw new Error('Empty response from server');
          }

          const data = JSON.parse(responseText);

          if (!data || typeof data !== 'object') {
            throw new Error('Invalid data format received');
          }

          setUserData({
            name: data.name || 'User',
            email: data.email || 'user@example.com'
          });

          // After successful authentication, fetch conversations
          fetchConversations();
        } catch (fetchError) {
          console.error('Fetch error:', fetchError);
          setUserData({ name: 'User', email: 'Error fetching data' });
          setError(`Fetch error: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}`);
        }
      } catch (error) {
        console.error('Error in overall fetchUserData function:', error);
        setUserData({ name: 'Guest', email: 'Error occurred' });
        setError(`Global error: ${error instanceof Error ? error.message : String(error)}`);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserData();
  }, []);

  // Handler for AuthModal actions
  const handleSignUp = () => {
    window.location.href = '/signup';
  };

  const handleLogin = () => {
    window.location.href = '/login';
  };

  const handleTryFirst = () => {
    setShowAuthModal(false);
    setIsTryingFirst(true);
    // Set guest mode
    setUserData({ name: 'Guest', email: 'Guest session' });
  };

  const handleCloseModal = () => {
    setShowAuthModal(false);
  };

  // Fetch conversations from API
  const fetchConversations = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch('/api/conversations', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch conversations: ${response.status}`);
      }

      const data = await response.json();
      setConversations(data);
    } catch (error) {
      console.error('Error fetching conversations:', error);
    }
  };

  // Create a new conversation
  const createConversation = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return null;

      const response = await fetch('/api/conversations', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title: 'New Conversation' })
      });

      if (!response.ok) {
        throw new Error(`Failed to create conversation: ${response.status}`);
      }

      const data = await response.json();

      // Add the new conversation to the list and set it as current
      setConversations(prev => [data, ...prev]);
      setCurrentConversation(data.id);
      setMessages([]);

      return data.id;
    } catch (error) {
      console.error('Error creating conversation:', error);
      return null;
    }
  };

  // Fetch messages for a conversation
  const fetchMessages = async (conversationId: number) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch(`/api/conversations/${conversationId}/messages`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch messages: ${response.status}`);
      }

      const data = await response.json();
      setMessages(data);

      // Scroll to bottom after messages load
      setTimeout(() => {
        scrollToBottom();
      }, 100);
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  };

  // Send a message and get AI response
  const sendMessage = async (content: string) => {
    if (!content.trim()) return;

    try {
      setIsProcessing(true);

      // If in try-first mode, handle guest messages locally
      if (isTryingFirst) {
        // Add user message to UI
        const userMessage: Message = { role: 'user', content };
        setMessages(prev => [...prev, userMessage]);

        // Simulate AI response after short delay
        setTimeout(() => {
          const aiMessage: Message = {
            role: 'akuru',
            content: "This is a demo version. Please sign up or log in to chat with Akuru AI's full capabilities."
          };
          setMessages(prev => [...prev, aiMessage]);
          scrollToBottom();
          setIsProcessing(false);
        }, 1000);

        // Clear input field
        setMessage('');
        return;
      }

      // If no conversation is selected, create a new one
      let conversationId = currentConversation;
      if (!conversationId) {
        conversationId = await createConversation();
        if (!conversationId) throw new Error('Failed to create conversation');
      }

      // Add user message to UI immediately for better UX
      const userMessage: Message = { role: 'user', content };
      setMessages(prev => [...prev, userMessage]);
      scrollToBottom();

      // Clear input field
      setMessage('');

      const token = localStorage.getItem('token');
      if (!token) throw new Error('No authentication token found');

      const response = await fetch(`/api/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          role: 'user',
          content
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.status}`);
      }

      const data = await response.json();

      // If the response contains an AI response, add it to the messages
      if (data.ai_response) {
        const aiMessage: Message = {
          id: data.ai_response.id,
          role: 'akuru',
          content: data.ai_response.content
        };
        setMessages(prev => [...prev, aiMessage]);
        scrollToBottom();
      }

      // Refresh conversations list to update the updated_at timestamp
      fetchConversations();
    } catch (error) {
      console.error('Error sending message:', error);
      setError(`Error sending message: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle new chat button
  const handleNewChat = () => {
    setCurrentConversation(null);
    setMessages([]);
  };

  // Handle conversation selection
  const handleSelectConversation = (conversationId: number) => {
    setCurrentConversation(conversationId);
    fetchMessages(conversationId);
  };

  // Handle input form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(message);
  };

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Format conversation title for display
  const formatConversationTitle = (conversation: Conversation) => {
    if (conversation.title && conversation.title !== 'New Conversation') {
      return conversation.title;
    }

    // If no meaningful title, use the first message or default
    return `New conversation (${conversation.message_count} messages)`;
  };

  return (
    <>
      {!isAuthenticated && showAuthModal && !isTryingFirst && (
        <AuthModal
          isAuthenticated={isAuthenticated}
          onClose={handleCloseModal}
          onSignUp={handleSignUp}
          onLogin={handleLogin}
          onTryFirst={handleTryFirst}
        />
      )}
      <div className="flex h-screen bg-[#292929] text-white">
        {/* Sidebar */}
        <div className="w-80 bg-[#1E1E1E] flex flex-col">
          <div className="p-4 flex items-center justify-between">
            <button className="p-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="#E9D8B5">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
          <div className="px-4 py-2">
            <button
              onClick={handleNewChat}
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
          </div>
          <div className="px-4 py-2 mt-2">
            <h3 className="text-sm font-medium text-white">Recents</h3>
          </div>
          <div className="flex-1 overflow-y-auto">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`flex items-center px-4 py-3 mx-4 ${currentConversation === conversation.id ? 'bg-[#292929]' : 'hover:bg-[#292929]'} rounded-lg transition-all duration-200 cursor-pointer hover:shadow-md`}
                onClick={() => handleSelectConversation(conversation.id)}
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
                <span className="text-sm">{formatConversationTitle(conversation)}</span>
              </div>
            ))}
          </div>
          <div className="p-4 border-t border-[#292929] flex items-center">
            <Icon path={mdiAccountCircle} size={1} className='text-[#E9D8B5]' />
            <span className="text-sm ml-3">{userData.email || 'Loading...'}</span>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 flex flex-col">
          <div className="flex justify-between items-center p-4">
            <div className="flex">
              <svg version="1.0" xmlns="http://www.w3.org/2000/svg"
                width="80pt" height="45pt" viewBox="0 0 310.000000 178.000000"
                preserveAspectRatio="xMidYMid meet">
                <rect width="100%" height="100%" fill="#292929" />
                <g transform="translate(0.000000,178.000000) scale(0.100000,-0.100000)"
                  fill="#292929" stroke="none">
                  <path d="M0 890 l0 -890 1550 0 1550 0 0 890 0 890 -1550 0 -1550 0 0 -890z" />
                </g>
                <g transform="translate(0.000000,178.000000) scale(0.100000,-0.100000)"
                  fill="#E9D8B5" stroke="none">
                  <path d="M2445 1370 c0 -13 -47 -16 -345 -20 -433 -6 -412 2 -424 -172 -7 -107 -5 -112
                      49 -84 39 20 85 1 85 -34 0 -12 -24 -29 -76 -54 -63 -30 -75 -39 -69 -54 4 -9
                      11 -35 15 -57 14 -70 51 -88 205 -98 l40 -2 3 -77 c2 -43 6 -78 10 -78 4 0 43
                      36 87 80 l80 80 245 0 c262 0 277 3 313 51 17 24 19 44 19 213 0 128 -3 195
                      -12 216 -13 32 -55 60 -89 60 -33 0 -51 11 -51 31 0 27 68 26 121 -2 69 -35
                      79 -70 79 -294 0 -178 -1 -194 -22 -235 -38 -74 -56 -78 -338 -86 l-245 -6
                      -111 -110 c-73 -72 -116 -108 -124 -103 -9 6 -11 33 -8 102 6 115 1 123 -80
                      123 -34 0 -71 7 -92 18 -41 20 -80 83 -80 131 0 27 -3 32 -17 27 -24 -9 -167
                      -113 -219 -159 -120 -106 23 73 156 194 l80 74 0 107 c0 59 5 119 11 135 12
                      33 56 82 84 93 11 5 178 8 370 7 304 -2 350 -4 350 -17z m-111 -212 c29 -41 1
                      -124 -62 -190 -36 -38 -62 -49 -62 -26 0 6 18 40 41 75 45 68 48 104 7 82 -13
                      -7 -53 -36 -89 -65 -96 -76 -159 -114 -191 -114 -42 0 -33 22 20 47 26 13 80
                      51 121 85 101 87 160 128 182 128 10 0 25 -10 33 -22z m-1590 -106 c40 -24 66
                      -77 66 -137 0 -72 -25 -107 -102 -143 -60 -29 -213 -61 -226 -48 -3 3 1 6 10
                      6 18 0 186 86 211 107 48 44 41 157 -10 169 -27 7 -53 -14 -53 -43 0 -16 -12
                      -17 -28 -1 -16 16 -15 60 1 80 32 40 73 44 131 10z m441 7 c77 -36 107 -136
                      66 -218 -16 -31 -33 -43 -89 -69 -63 -28 -158 -52 -205 -52 -11 0 24 23 78 50
                      116 59 130 71 146 117 14 42 -2 107 -28 117 -25 10 -53 -3 -53 -25 0 -24 -29
                      -37 -41 -18 -18 29 -9 67 22 93 37 31 47 32 104 5z m63 -391 c-3 -27 -12 -37
                      -63 -66 -33 -19 -105 -71 -159 -115 -125 -99 -139 -106 -167 -81 -23 20 -23
                      12 3 179 12 74 15 80 37 80 37 0 48 -26 32 -82 -20 -70 -24 -103 -14 -103 5 0
                      52 36 103 80 98 84 182 138 213 139 15 1 18 -5 15 -31z m-600 -40 c2 -21 5
                      -38 8 -38 2 0 27 18 55 40 57 45 83 50 99 20 13 -24 4 -60 -13 -60 -7 0 -39
                      -27 -72 -60 -44 -44 -67 -60 -87 -60 -29 0 -48 23 -48 59 0 42 -24 33 -88 -33
                      -69 -71 -95 -79 -100 -33 -3 23 10 41 75 107 80 80 112 101 148 97 15 -2 21
                      -11 23 -39z m1047 25 c21 -21 15 -85 -15 -142 -35 -69 -130 -130 -130 -84 0 9
                      18 43 40 74 22 32 40 62 40 68 0 17 -24 13 -46 -7 -45 -40 -151 -114 -210
                      -144 -59 -31 -64 -32 -80 -16 -17 17 -12 54 6 43 15 -9 41 8 158 102 59 48
                      121 95 137 105 37 22 78 23 100 1z"
                  />
                </g>
              </svg>
            </div>
            <div className="flex-1 flex justify-end">
              <button className="p-2 mb-4">
                <svg version="1.0" xmlns="http://www.w3.org/2000/svg"
                  width="15pt" height="15pt" viewBox="0 0 512.000000 512.000000"
                  preserveAspectRatio="xMidYMid meet">
                  <g transform="translate(0.000000,512.000000) scale(0.100000,-0.100000)"
                    fill="#E9D8B5" stroke="none">
                    <path d="M1810 5071 c-381 -125 -719 -327 -1006 -604 -232 -223 -388 -434
                        -526 -710 -501 -1007 -310 -2193 483 -2988 502 -504 1199 -781 1899 -756 548
                        20 1015 179 1455 496 472 339 815 837 975 1415 35 128 36 147 11 203 -26 57
                        -84 87 -156 81 -44 -4 -64 -13 -119 -54 -158 -116 -259 -179 -381 -239 -283
                        -138 -527 -195 -839 -195 -515 0 -993 197 -1356 559 -367 367 -565 841 -564
                        1356 1 443 131 839 380 1158 63 81 81 134 65 189 -23 76 -93 129 -168 127 -21
                        0 -90 -18 -153 -38z m-284 -573 c-78 -187 -133 -397 -156 -598 -14 -123 -14
                        -410 0 -525 94 -767 564 -1432 1245 -1764 314 -154 585 -219 940 -228 356 -9
                        626 42 964 184 57 24 106 41 109 39 8 -8 -120 -213 -199 -319 -440 -591 -1099
                        -927 -1819 -927 -505 0 -948 147 -1354 448 -275 205 -510 490 -669 810 -159
                        321 -229 624 -229 987 1 315 45 554 154 830 163 413 462 784 833 1032 71 48
                        212 132 222 133 1 0 -18 -46 -41 -102z"/>
                  </g>
                </svg>
              </button>
            </div>
          </div>
          <div className="flex-1 flex flex-col">
            <div className="flex-1 overflow-y-auto p-6">
              {isAuthenticated ? (
                messages.length === 0 ? (
                  // Empty state for chat
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
                ) : (
                  // Chat messages
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
                )
              ) : (
                // Not authenticated view
                <div className="flex flex-col items-center justify-center h-full">
                  {isLoading ? (
                    <h1 className="text-3xl font-medium mb-4">Loading...</h1>
                  ) : (
                    <>
                      <h1 className="text-3xl font-medium mb-4">
                        Hello, {userData.name}
                      </h1>
                      {error && (
                        <div className="bg-red-500 bg-opacity-20 p-4 rounded-md mb-4">
                          <p className="text-red-300">{error}</p>
                        </div>
                      )}
                      <div className="text-center">
                        <div className="text-gray-400 mb-4">
                          <span className="whitespace-pre-wrap tracking-tight text-[#F9D8B5]">
                            For a complete experience with saved conversations, please create an account or log in.
                          </span>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Chat input */}
            <div className="p-6">
              <form onSubmit={handleSubmit} className="relative w-full max-w-3xl mx-auto">
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
          </div>
        </div>
      </div>
    </>
  );
};

export default Home;