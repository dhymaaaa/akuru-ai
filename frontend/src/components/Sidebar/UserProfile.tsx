import React from 'react';
import Icon from '@mdi/react';
import { mdiAccountCircle } from '@mdi/js';

interface UserProfileProps {
  email: string;
}

const UserProfile: React.FC<UserProfileProps> = ({ email }) => {
  return (
    <div className="p-4 border-t border-[#292929] flex items-center">
      <Icon path={mdiAccountCircle} size={1} className='text-[#E9D8B5]' />
      <span className="text-sm ml-3">{email || 'Loading...'}</span>
    </div>
  );
};

export default UserProfile;