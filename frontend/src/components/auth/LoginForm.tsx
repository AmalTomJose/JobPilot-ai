import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { LoginFormData } from '../../types/auth.types';
import { loginSchema } from '../../schemas/auth.schema';
import { authService } from '../../services/auth.service';
import { apiError } from '../../api/axios';
import { useAuth } from '../../hooks/useAuth';
import Icon from '../ui/Icon';
export default function LoginForm() {
    const navigate = useNavigate();
    const location = useLocation();
    const { login } = useAuth();
    const [error, setError] = useState('');
    const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginFormData>({ resolver: zodResolver(loginSchema) });
    async function onSubmit(data: LoginFormData) {
        setError('');
        try {
            login(await authService.login(data));
            const from = location.state?.from;
            const destination = typeof from?.pathname === 'string' && from.pathname.startsWith('/') && !from.pathname.startsWith('//') ? from.pathname + (from.search || '') + (from.hash || '') : '/dashboard';
            navigate(destination, { replace: true });
        }
        catch (err) {
            setError(apiError(err));
        }
    }
    return <section className="auth-form">
    <span className="eyebrow">WELCOME BACK</span>
    <h1>Your next step<br />starts here.</h1>
    <p className="muted">Sign in to your personal career workspace.</p>{location.state?.registered && <div className="notice success" role="status">Account created. Sign in to get started.</div>}{error && <div className="notice error" role="alert">{error}</div>}<form onSubmit={handleSubmit(onSubmit)} noValidate>
    <div className="field">
    <label htmlFor="login-email">Email address</label>
    <input id="login-email" type="email" autoComplete="email" placeholder="you@example.com" {...register('email')} aria-invalid={!!errors.email} aria-describedby={errors.email ? 'login-email-error' : undefined}/>{errors.email && <span className="field-error" id="login-email-error">{errors.email.message}</span>}</div>
    <div className="field">
    <label htmlFor="login-password">Password</label>
    <input id="login-password" type="password" autoComplete="current-password" placeholder="Enter your password" {...register('password')} aria-invalid={!!errors.password} aria-describedby={errors.password ? 'login-password-error' : undefined}/>{errors.password && <span className="field-error" id="login-password-error">{errors.password.message}</span>}</div>
    <button className="btn btn-primary btn-full" disabled={isSubmitting}>{isSubmitting ? 'Signing in…' : 'Sign in'}<Icon name="arrow" size={18}/>
    </button>
    </form>
    <p className="auth-switch">New here? <Link to="/register">Create an account</Link>
    </p>
    </section>;
}
