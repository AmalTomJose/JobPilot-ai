import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { RegisterFormData } from '../../types/auth.types';
import { registerSchema } from '../../schemas/auth.schema';
import { authService } from '../../services/auth.service';
import { apiError } from '../../api/axios';
import Icon from '../ui/Icon';
export default function RegisterForm() {
    const navigate = useNavigate();
    const [error, setError] = useState('');
    const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterFormData>({ resolver: zodResolver(registerSchema) });
    async function onSubmit(data: RegisterFormData) {
        setError('');
        try {
            await authService.register(data);
            navigate('/login', { replace: true, state: { registered: true } });
        }
        catch (err) {
            setError(apiError(err));
        }
    }
    return <section className="auth-form">
    <span className="eyebrow">LET’S GET STARTED</span>
    <h1>Make room for<br />what’s next.</h1>
    <p className="muted">Create your personal JobPilot workspace.</p>{error && <div className="notice error" role="alert">{error}</div>}<form onSubmit={handleSubmit(onSubmit)} noValidate>{([{ name: 'name', label: 'Full name', type: 'text', placeholder: 'Alex Morgan', autocomplete: 'name' }, { name: 'email', label: 'Email address', type: 'email', placeholder: 'you@example.com', autocomplete: 'email' }, { name: 'password', label: 'Password', type: 'password', placeholder: 'At least 6 characters', autocomplete: 'new-password' }, { name: 'confirmPassword', label: 'Confirm password', type: 'password', placeholder: 'Enter your password again', autocomplete: 'new-password' }] as const).map(field => <div className="field" key={field.name}>
        <label htmlFor={`register-${field.name}`}>{field.label}</label>
        <input id={`register-${field.name}`} type={field.type} autoComplete={field.autocomplete} placeholder={field.placeholder} {...register(field.name)} aria-invalid={!!errors[field.name]} aria-describedby={errors[field.name] ? `${field.name}-error` : undefined}/>{errors[field.name] && <span className="field-error" id={`${field.name}-error`}>{errors[field.name]?.message}</span>}</div>)}<button className="btn btn-primary btn-full" disabled={isSubmitting}>{isSubmitting ? 'Creating your account…' : 'Create account'}<Icon name="arrow" size={18}/>
    </button>
    </form>
    <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link>
    </p>
    </section>;
}
