// components/Layout/GuestChatLayout.tsx
import React, { ReactNode } from 'react';
import ChatHeader from '../Chat/ChatHeader';

interface GuestChatLayoutProps {
    onLogin: () => void;
    onSignUp: () => void;
    onNewChat: () => void;
    children: ReactNode;
}

const GuestChatLayout: React.FC<GuestChatLayoutProps> = ({
    onLogin,
    onSignUp,
    onNewChat,
    children
}) => {
    return (
        <div className="flex h-screen bg-[#292929] text-white">
            {/* Main content */}
            <div className="flex-1 flex flex-col h-screen">
                {/* Header */}
                <ChatHeader 
                    isLoggedIn={false}
                    onLogin={onLogin}
                    onRegister={onSignUp}
                    onNewChat={onNewChat}
                />

                {/* Content */}
                <div className="flex-1 overflow-y-auto">
                    <div className="h-full flex-1 flex flex-col">
                        {children}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default GuestChatLayout;