import { createContext } from 'react';
import type { User } from '../types/user.types';
import type { LoginResponse } from '../types/auth.types';
export type AuthContextType = {
    user: User | null;
    isAuthenticated: boolean;
    loading: boolean;
    sessionError: string;
    retrySession: () => void;
    login: (response: LoginResponse) => void;
    logout: () => void;
};
export const AuthContext = createContext<AuthContextType | undefined>(undefined);
