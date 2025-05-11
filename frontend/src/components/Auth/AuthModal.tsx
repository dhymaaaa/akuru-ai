import { useState, useEffect } from 'react';

interface AuthModalProps {
    isAuthenticated: boolean;
    onClose: () => void;
    onSignUp: () => void;
    onLogin: () => void;
    onTryFirst: () => void;
}

const AuthModal = ({ isAuthenticated, onClose, onSignUp, onLogin, onTryFirst }: AuthModalProps) => {
    const [isOpen, setIsOpen] = useState(true);

    // Close modal if user is authenticated
    useEffect(() => {
        if (isAuthenticated) {
            setIsOpen(false);
        }
    }, [isAuthenticated]);

    const handleClose = () => {
        setIsOpen(false);
        onClose();
    };

    if (!isOpen || isAuthenticated) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop with blur effect */}
            <div className="absolute inset-0 backdrop-blur-md bg-black/30" onClick={handleClose}></div>
            
            <div className="relative z-10 bg-[#1E1E1E] rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden border border-[#3A3A3A]">
                <div className="flex justify-center items-center bg-gradient-to-r from-[#292929] to-[#3D3D3D] p-6 text-center relative">
                    <svg 
                        version="1.0" xmlns="http://www.w3.org/2000/svg"
                        width="80pt" height="45pt" viewBox="0 0 310.000000 178.000000"
                        preserveAspectRatio="xMidYMid meet">
                        <rect width="100%" height="100%" fill="transparent" />
                        <g transform="translate(0.000000,178.000000) scale(0.100000,-0.100000)"
                            fill="transparent" stroke="none">
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
                    <button
                        className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors"
                        onClick={handleClose}
                        aria-label="Close"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>

                <div className="p-6">
                    <div className="space-y-4">
                        <button
                            className="w-full bg-[#E9D8B5] hover:bg-[#d9c8a5] text-black font-medium py-3 px-4 rounded-lg transition duration-200"
                            onClick={onSignUp}
                        >
                            Sign Up
                        </button>

                        <button
                            className="w-full bg-transparent hover:bg-[#333333] text-[#E9D8B5] font-medium py-3 px-4 rounded-lg border border-[#E9D8B5] transition duration-200"
                            onClick={onLogin}
                        >
                            Log In
                        </button>

                        <div className="relative flex items-center py-2">
                            <div className="flex-grow border-t border-[#3A3A3A]"></div>
                            <span className="flex-shrink mx-4 text-gray-400 text-sm">or</span>
                            <div className="flex-grow border-t border-[#3A3A3A]"></div>
                        </div>

                        <button
                            className="w-full bg-[#292929] hover:bg-[#363636] text-white font-medium py-3 px-4 rounded-lg transition duration-200"
                            onClick={onTryFirst}
                        >
                            Try It First
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AuthModal;