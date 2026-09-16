import { Link, Outlet } from 'react-router-dom';
import Icon from '../components/ui/Icon';
export default function AuthLayout() {
    return <div className="auth-shell">
    <aside className="auth-story">
    <Link to="/" className="brand">
    <span className="brand-mark">J<span>↗</span>
    </span>
    <span>JobPilot<span className="brand-ai">AI</span>
    </span>
    </Link>
    <div className="auth-story-body">
    <span className="eyebrow">YOUR NEXT CHAPTER</span>
    <h1>Good things<br />start with<br />
    <em>a little direction.</em>
    </h1>
    <p>Your experience has a story to tell. Bring it together in a workspace built for your next career move.</p>
    <div className="auth-story-card">
    <Icon name="file" size={28}/>
    <div>
    <strong>Your resume. A clearer starting point.</strong>
    <p>Upload a PDF and extract its text, all in one place.</p>
    </div>
    </div>
    </div>
    <span className="auth-foot">Made for the next step, whatever it looks like.</span>
    </aside>
    <main className="auth-main">
    <Link to="/" className="back-link">← Back to home</Link>
    <Outlet />
    <p className="auth-fineprint">
    <Icon name="shield" size={15}/> Your workspace is protected by your account.</p>
    </main>
    </div>;
}
