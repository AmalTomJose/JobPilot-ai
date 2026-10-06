import {Link} from 'react-router-dom';
import GmailConnection from '../../components/Gmail/GmailConnection';
import { useAuth } from '../../hooks/useAuth';
import PageHeader from '../../components/ui/PageHeader';
import Icon from '../../components/ui/Icon';
export default function Settings() {
    const { user, logout } = useAuth();
    return <>
    <PageHeader eyebrow="MAKE YOURSELF AT HOME" title="Settings" description="Your account and workspace, at a glance."/>
    <div className="settings-stack">
    <GmailConnection/>
    <section className="card">
        <span className="eyebrow">CLICK · PREVIEW · SEND</span>
        <h2>Import a job page</h2>
        <p>Use the JobPilot Chrome extension on permitted sites, or paste a description. Review first, then add the job or save a draft for later.</p>
        <p className="form-note">Load the extension folder through Chrome’s Load unpacked option. Full setup steps are in docs/BROWSER_CAPTURE.md. LinkedIn uses the manual paste fallback.</p>
        <Link className="btn btn-secondary" to="/jobs/capture">Open job-page import</Link>
    </section>
    <section className="card">
    <div className="setting-heading">
    <span className="feature-icon">
    <Icon name="user"/>
    </span>
    <div>
    <h2>Your account</h2>
    <p className="muted">Signed in as {user?.email}</p>
    </div>
    </div>
    <div className="setting-row">
    <div>
    <h3>End this session</h3>
    <p>Sign out of JobPilot on this browser.</p>
    </div>
    <button className="btn btn-secondary" onClick={logout}>Sign out <Icon name="logout" size={17}/>
    </button>
    </div>
    </section>
    <section className="card">
    <div className="setting-heading">
    <span className="feature-icon">
    <Icon name="settings"/>
    </span>
    <div>
    <h2>Workspace preferences</h2>
    <p className="muted">More ways to make JobPilot yours are on the roadmap.</p>
    </div>
    </div>
    <div className="setting-row">
    <div>
    <h3>Profile and password updates</h3>
    <p>Account editing and password recovery are not available yet.</p>
    </div>
    <span className="pill neutral">Planned</span>
    </div>
    </section>
    </div>
    </>;
}
