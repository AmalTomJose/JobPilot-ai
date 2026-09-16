import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
export default function ProtectedRoute() {
    const { isAuthenticated, loading, sessionError, retrySession, logout } = useAuth();
    const location = useLocation();
    if (loading)
        return <div className="full-state" role="status">
        <span className="brand-mark">J<span>↗</span>
        </span>
        <p>Opening your workspace…</p>
        </div>;
    if (sessionError)
        return <div className="full-state">
        <div className="card state-card">
        <span className="eyebrow">Connection interrupted</span>
        <h1>Let’s reconnect.</h1>
        <p role="alert">{sessionError}</p>
        <div className="button-row">
        <button className="btn btn-primary" onClick={retrySession}>Try again</button>
        <button className="btn btn-secondary" onClick={logout}>Back to sign in</button>
        </div>
        </div>
        </div>;
    return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace state={{ from: location }}/>;
}
