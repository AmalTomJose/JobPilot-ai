import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Icon from '../ui/Icon';
export default function Navbar() {
    const { user, logout } = useAuth();
    const { pathname } = useLocation();
    const labels: Record<string, string> = { '/dashboard': 'Overview', '/resume': 'My resume', '/profile': 'Profile', '/jobs': 'Discover jobs', '/applications': 'Applications', '/settings': 'Settings' };
    return <header className="topbar">
    <div className="breadcrumb">Workspace <span>/</span> <strong>{labels[pathname]}</strong>
    </div>
    <div className="topbar-actions">
    <span className="workspace-badge">
    <i />Personal workspace</span>
    <Link className="avatar" to="/profile" aria-label="View profile">{user?.name.slice(0, 1).toUpperCase()}</Link>
    <button className="icon-button" onClick={logout} aria-label="Sign out" title="Sign out">
    <Icon name="logout"/>
    </button>
    </div>
    </header>;
}
