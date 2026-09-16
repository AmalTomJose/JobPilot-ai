import { z } from 'zod';
const email = z.email('Enter a valid email address');
const password = z.string().min(6, 'Use at least 6 characters').max(128, 'Use 128 characters or fewer');
export const loginSchema = z.object({ email, password });
export const registerSchema = z.object({
    name: z.string().trim().min(2, 'Enter at least 2 characters').max(100, 'Use 100 characters or fewer'),
    email, password, confirmPassword: z.string(),
}).refine(data => data.password === data.confirmPassword, { path: ['confirmPassword'], message: 'Passwords do not match' });
