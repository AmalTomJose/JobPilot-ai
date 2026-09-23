import { useEffect, useState } from 'react';
import { profileService } from '../services/profile.service';
import { apiError } from '../api/axios';
import type { Profile } from '../types/profile.types';

export function useProfile() {
    const [profile, setProfile] = useState<Profile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [attempt, setAttempt] = useState(0);
    useEffect(() => {
        let active = true;
        async function load() {
            setLoading(true); setError('');
            try { const result = await profileService.get(); if (active) setProfile(result); }
            catch (error) { if (active) setError(apiError(error)); }
            finally { if (active) setLoading(false); }
        }
        void load();
        return () => { active = false; };
    }, [attempt]);
    return {profile, loading, error, retry: () => setAttempt(value => value + 1)};
}
