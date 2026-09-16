import { useAuth } from '../../hooks/useAuth';
import PageHeader from '../../components/ui/PageHeader';
import Icon from '../../components/ui/Icon';
export default function Settings() {
    const { user, logout } = useAuth();
    return <>
    <PageHeader eyebrow="MAKE YOURSELF AT HOME" title="Settings" description="Your account and workspace, at a glance."/>
    <div className="settings-stack">
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
    <h3>Email connections</h3>
    <p>Connect a mailbox for job email ingestion in a future update.</p>
    </div>
    <span className="pill neutral">Planned</span>
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
