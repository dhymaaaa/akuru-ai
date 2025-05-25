import React, { useState, useEffect, useRef } from 'react';
import Icon from '@mdi/react';
import { mdiAccountCircle, mdiLogout } from '@mdi/js';

interface UserProfileProps {
  email: string;
  isCollapsed: boolean;
  loginPageUrl?: string;
  onLogout?: () => Promise<void> | void; 
  onProfileToggle?: (isExpanded: boolean) => void;
  onExpandSidebar?: () => void;
}

const UserProfile: React.FC<UserProfileProps> = ({
  email,
  isCollapsed,
  loginPageUrl = '/login' ,
  onLogout = () => console.log('Logout clicked'),
  onProfileToggle = () => {},
  onExpandSidebar = () => {},
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [isLoggingOut, setIsLoggingOut] = useState<boolean>(false);
  const profileRef = useRef<HTMLDivElement>(null);
 
  const toggleExpanded = () => {
    // If sidebar is collapsed and we're expanding the profile
    if (isCollapsed && !isExpanded) {
      // Request sidebar expansion
      onExpandSidebar();
      // Set local state to expanded
      setIsExpanded(true);
      onProfileToggle(true);
    } else {
      // Normal toggle behavior when sidebar is already expanded
      const newExpandedState = !isExpanded;
      setIsExpanded(newExpandedState);
      onProfileToggle(newExpandedState);
    }
  };

  // Handle the logout process
  const handleLogout = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering the outside click
    
    // Prevent double-clicks
    if (isLoggingOut) return;
    
    setIsLoggingOut(true);
    
    try {
      // Call the provided logout function
      await onLogout();
      
      // Redirect to login page
      window.location.href = loginPageUrl;
    } catch (error) {
      console.error('Logout failed:', error);
      setIsLoggingOut(false);
    }
  };

  // Reset expanded state when sidebar collapses
  useEffect(() => {
    if (isCollapsed && isExpanded) {
      setIsExpanded(false);
      onProfileToggle(false);
    }
  }, [isCollapsed, isExpanded, onProfileToggle]);

  // Handle clicks outside the component
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      // If the profile is expanded and the click is outside the profile component
      if (
        isExpanded &&
        profileRef.current &&
        !profileRef.current.contains(event.target as Node)
      ) {
        setIsExpanded(false);
        onProfileToggle(false);
      }
    };
    
    // Add event listener when the component mounts
    document.addEventListener('mousedown', handleClickOutside);
   
    // Remove event listener when the component unmounts
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isExpanded, onProfileToggle]);

  return (
    <div className="relative" ref={profileRef}>
      {/* Logout Button - only show when sidebar is expanded */}
      {isExpanded && !isCollapsed && (
        <div className={`${isCollapsed ? 'flex justify-center' : 'px-4'} mb-3`}>
          <button
            onClick={handleLogout}
            disabled={isLoggingOut}
            className={`
              flex items-center space-x-2 w-full rounded-lg px-4 py-3 
              bg-[#292929] transition hover:bg-[#363636]
              ${isLoggingOut ? 'opacity-75 cursor-not-allowed' : ''}
            `}
          >
            <Icon path={mdiLogout} size={0.9} className="text-[#E9D8B5]" />
            {!isCollapsed && (
              <span>{isLoggingOut ? 'Logging out...' : 'Log out'}</span>
            )}
          </button>
        </div>
      )}
     
      {/* Original Profile Component */}
      <div
        className={`${isCollapsed ? 'flex justify-center py-5' : 'p-4 border-t border-[#292929] flex items-center'} cursor-pointer`}
        onClick={(e) => {
          e.stopPropagation(); // Prevent event bubbling
          toggleExpanded();
        }}
      >
        {isCollapsed ? (
          <Icon className='text-[#E9D8B5]' path={mdiAccountCircle} size={1} />
        ) : (
          <>
            <div className="w-6 h-6 flex items-center justify-center">
              <Icon className='text-[#E9D8B5]' path={mdiAccountCircle} size={1} />
            </div>
            <span className="ml-3">{email || 'Loading...'}</span>
          </>
        )}
      </div>
    </div>
  );
};

export default UserProfile;