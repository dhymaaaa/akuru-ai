import React from 'react';

interface EmptyChatProps {
  isAuthenticated: boolean;
  userData: {
    name: string;
    email: string;
  };
  isLoading: boolean;
  error: string | null;
}

const EmptyChat: React.FC<EmptyChatProps> = ({
  isAuthenticated,
  userData,
  isLoading,
  error
}) => {
  if (isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <h1 className="text-3xl font-medium mb-4">
          Welcome {userData.name}
        </h1>
        <div className="text-gray-400 mb-4 text-center">
          <span className="whitespace-pre-wrap tracking-tight text-[#F9D8B5]">
            Start chatting with Akuru in English or Dhivehi
          </span>
        </div>
      </div>
    );
  }

  return (
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
                For a complete experience with saved conversations and dialect functionality, please create an account or log in.
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default EmptyChat;