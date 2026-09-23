import axios from 'axios';
import api from '../api/axios';
import type { Profile, ProfileSave } from '../types/profile.types';

export const profileService = {
    async get(): Promise<Profile | null> {
        try { return (await api.get<Profile>('/profile')).data; }
        catch (error) {
            if (axios.isAxiosError(error) && error.response?.status === 404) return null;
            throw error;
        }
    },
    async save(request: ProfileSave): Promise<Profile> {
        return (await api.put<Profile>('/profile', request)).data;
    },
};
