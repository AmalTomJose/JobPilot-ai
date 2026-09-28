import type { LoginFormData, LoginResponse, RegisterFormData } from '../types/auth.types';
import type { User } from '../types/user.types';
import api from '../api/axios';
export const authService = {
    async login(data: LoginFormData): Promise<LoginResponse> {
        return (await api.post<LoginResponse>('/auth/login', data)).data;
    },
    async register(data: RegisterFormData): Promise<{
        message: string;
        user: User;
    }> {
        const { name, email, password } = data;
        return (await api.post('/auth/register', { name, email, password })).data;
    },
    async getCurrentUser(): Promise<User> {
        return (await api.get<User>('/auth/me')).data;
    },
};
