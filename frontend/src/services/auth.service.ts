import type { LoginFormData } from "../types/auth.types";
import type { RegisterFormData } from "../types/auth.types";

import api from "../api/axios";

export const authService = {
    login: async (data: LoginFormData) => {
        console.log("Login request:", data);
        const response = await api.post('/auth/login', data);
        console.log(response.data)
        return response.data
    },
    register: async (data: RegisterFormData) => {
        console.log("Register request:", data);

        const response = await api.post('/auth/register', data);
        console.log(response.data)
       
    },
    getCurrentUser: async ()=>{
        const response = await api.get('/auth/me');
        return response.data;
    }
};