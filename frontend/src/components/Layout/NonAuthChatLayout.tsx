// components/Layout/NonAuthChatLayout.tsx
import React, { ReactNode } from 'react';

interface NonAuthChatLayoutProps {
    onLogin: () => void;
    onSignUp: () => void;
    onTryFirst: () => void;
    children: ReactNode;
}

const NonAuthChatLayout: React.FC<NonAuthChatLayoutProps> = ({
    onLogin,
    onSignUp,
    onTryFirst,
    children
}) => {
    return (
        <div className="flex h-screen bg-[#292929] text-white">
            {/* Main content area - simplified for non-authenticated users */}
            <div className="flex-1 flex flex-col h-screen">
                {/* Header */}
                <div className="bg-[#1E1E1E] py-3 px-4 border-b border-[#3A3A3A] flex justify-between">
                    <div className="flex items-center">
                        <svg
                            version="1.0" xmlns="http://www.w3.org/2000/svg"
                            width="50pt" height="28pt" viewBox="0 0 310.000000 178.000000"
                            preserveAspectRatio="xMidYMid meet">
                            {/* Your SVG path here (same as in AuthModal) */}
                        </svg>
                    </div>
                    <div>
                        <button onClick={onLogin} className="text-[#E9D8B5] mr-4 hover:underline">
                            Login
                        </button>
                        <button onClick={onSignUp} className="bg-[#E9D8B5] text-black px-4 py-1 rounded-md hover:bg-[#d9c8a5]">
                            Register
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto">
                    <div className="h-full p-6 flex flex-col items-center justify-center">
                        {children}

                        {/* Button to try without login */}
                        <button
                            className="mt-8 bg-[#292929] hover:bg-[#363636] text-white font-medium py-3 px-8 rounded-lg transition duration-200 border border-[#3A3A3A]"
                            onClick={onTryFirst}
                        >
                            Try It First
                        </button>
                    </div>
                </div>

                {/* Input box disabled state */}
                <div className="border-t border-[#3A3A3A] p-4">
                    <div className="relative">
                        <input
                            type="text"
                            disabled
                            placeholder="Log in to start chatting..."
                            className="w-full bg-[#1E1E1E] rounded-lg py-3 px-4 pr-12 focus:outline-none border border-[#3A3A3A] opacity-50"
                        />
                        <button
                            disabled
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 opacity-50"
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 5l7 7-7 7M5 5l7 7-7 7"></path>
                            </svg>
                        </button>
                    </div>
                    <div className="flex justify-center text-xs text-gray-400 mt-2">
                        <div className='font-bold'>Akuru can make mistakes</div>
                        <div className='font-bold ml-5'>...</div>
                        <div className='font-bold ml-5'>އަކުރަށް ގޯސްކޮށްވެސް ބުނެވިދާނެ</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default NonAuthChatLayout;