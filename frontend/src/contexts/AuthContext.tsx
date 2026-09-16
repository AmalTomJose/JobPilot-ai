import { useState, useEffect, type ReactNode } from 'react';
import axios from 'axios';
import type { User } from '../types/user.types';
import type { LoginResponse } from '../types/auth.types';
import { authService } from '../services/auth.service';
import { AuthContext } from './auth-context';
export function AuthProvider({ children }: {
    children: ReactNode;
}) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [sessionError, setSessionError] = useState('');
    const [attempt, setAttempt] = useState(0);
    useEffect(() => {
        let active = true;
        let expired = false;
        const clearSession = () => {
            expired = true;
            setUser(null);
            setSessionError('');
        };
        window.addEventListener('session-expired', clearSession);
        async function restore() {
            const restoringToken = localStorage.getItem('access_token');
            if (!restoringToken) {
                setLoading(false);
                return;
            }
            try {
                const currentUser = await authService.getCurrentUser();
                if (active && !expired && localStorage.getItem('access_token') === restoringToken)
                    setUser(currentUser);
            }
            catch (error) {
                if (!active || expired || localStorage.getItem('access_token') !== restoringToken)
                    return;
                if (axios.isAxiosError(error) && error.response?.status === 401) {
                    localStorage.removeItem('access_token');
                    setUser(null);
                }
                else {
                    setSessionError('We could not reconnect to your account. Your session is saved; try again when the server is available.');
                }
            }
            finally {
                if (active)
                    setLoading(false);
            }
        }
        void restore();
        return () => { active = false; window.removeEventListener('session-expired', clearSession); };
    }, [attempt]);
    const login = (response: LoginResponse) => {
        localStorage.setItem('access_token', response.access_token);
        setSessionError('');
        setLoading(false);
        setUser(response.user);
    };
    const logout = () => { localStorage.removeItem('access_token'); setSessionError(''); setUser(null); };
    const retrySession = () => { setLoading(true); setSessionError(''); setAttempt(value => value + 1); };
    return <AuthContext.Provider value={{ user, isAuthenticated: user !== null, loading, sessionError, retrySession, login, logout }}>{children}</AuthContext.Provider>;
}
