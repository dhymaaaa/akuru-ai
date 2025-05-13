import React, { useState, useEffect, useRef } from 'react';
import Icon from '@mdi/react';
import { mdiAccountCircle, mdiLogout } from '@mdi/js';

interface UserProfileProps {
  email: string;
  isCollapsed: boolean;
  onLogout?: () => void;
  onProfileToggle?: (isExpanded: boolean) => void;
  onExpandSidebar?: () => void; // New prop to request sidebar expansion
}

const UserProfile: React.FC<UserProfileProps> = ({
  email,
  isCollapsed,
  onLogout = () => console.log('Logout clicked'),
  onProfileToggle = () => {},
  onExpandSidebar = () => {} // Default empty function
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
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

  // Reset expanded state when sidebar collapses
  useEffect(() => {
    if (isCollapsed && isExpanded) {
      setIsExpanded(false);
      onProfileToggle(false);
    }
  }, [isCollapsed]);

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
            onClick={(e) => {
              e.stopPropagation(); // Prevent triggering the outside click
              onLogout();
            }}
            className="flex items-center space-x-2 w-full rounded-lg px-4 py-3 bg-[#292929] transition hover:bg-[#363636]"
          >
            <Icon path={mdiLogout} size={0.9} className="text-[#E9D8B5]" />
            {!isCollapsed && <span>Log out</span>}
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