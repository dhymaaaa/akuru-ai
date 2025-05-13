// UserProfile.tsx - Without border in collapsed state
import React from 'react';
import Icon from '@mdi/react';
import { mdiAccountCircle } from '@mdi/js';

interface UserProfileProps {
  email: string;
  isCollapsed: boolean;
}

const UserProfile: React.FC<UserProfileProps> = ({ email, isCollapsed }) => {
  return (
    <div className={`${isCollapsed ? 'flex justify-center py-5' : 'p-4 border-t border-[#292929] flex items-center'}`}>
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
  );
};

export default UserProfile;