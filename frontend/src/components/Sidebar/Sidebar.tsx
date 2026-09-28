import { Link, NavLink } from 'react-router-dom';
import Icon, { type IconName } from '../ui/Icon';
const links: {
    to: string;
    label: string;
    icon: IconName;
}[] = [
    { to: '/dashboard', label: 'Overview', icon: 'grid' },
    { to: '/resume', label: 'My resume', icon: 'file' },
    { to: '/profile', label: 'Profile', icon: 'user' },
    { to: '/jobs', label: 'Job inbox', icon: 'briefcase' },
    { to: '/matches', label: 'Matches', icon: 'spark' },
    { to: '/applications', label: 'Applications', icon: 'send' },
    { to: '/settings', label: 'Settings', icon: 'settings' },
];
export default function Sidebar({open, onClose}: {open: boolean; onClose: () => void}) {
    const closeOnMobile = () => { if (window.matchMedia('(max-width: 650px)').matches) onClose(); };
    return <aside id="workspace-sidebar" aria-label="Workspace sidebar" className="sidebar" hidden={!open} onKeyDown={event => { if (event.key === 'Escape') onClose(); }}>
    <div className="sidebar-header">
    <Link className="brand" to="/dashboard" onClick={closeOnMobile}>
    <span className="brand-mark">J<span>↗</span>
    </span>
    <span>JobPilot<span className="brand-ai">AI</span>
    </span>
    </Link>
    <button type="button" className="icon-button sidebar-close" onClick={onClose} aria-label="Close navigation sidebar"><Icon name="close" size={18}/></button>
    </div>
    <span className="nav-caption">YOUR WORKSPACE</span>
    <nav aria-label="Main navigation" className="side-nav">{links.map(link => <NavLink onClick={closeOnMobile} key={link.to} to={link.to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <Icon name={link.icon}/>{link.label}</NavLink>)}</nav>
    <div className="sidebar-bottom">
    <div className="sidebar-note">
    <span className="small-orbit">
    <Icon name="spark"/>
    </span>
    <h3>Start with your story.</h3>
    <p>A great next step begins with a clear picture of you.</p>
    <Link to="/resume" onClick={closeOnMobile}>Add your resume <Icon name="arrow" size={16}/>
    </Link>
    </div>
    <div className="sidebar-foot">A little more direction. Every day.</div>
    </div>
    </aside>;
}
