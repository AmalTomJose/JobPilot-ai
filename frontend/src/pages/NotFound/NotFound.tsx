import { Link } from 'react-router-dom';
export default function NotFound() {
    return <main className="full-state">
    <span className="eyebrow">404 · A SMALL DETOUR</span>
    <h1>Let’s get you back on track.</h1>
    <p className="muted">This page doesn’t exist, but your next step is still waiting.</p>
    <Link to="/dashboard" className="btn btn-primary">Back to workspace →</Link>
    </main>;
}
