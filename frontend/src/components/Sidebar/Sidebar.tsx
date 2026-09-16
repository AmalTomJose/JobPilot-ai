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
    { to: '/jobs', label: 'Discover jobs', icon: 'briefcase' },
    { to: '/applications', label: 'Applications', icon: 'send' },
    { to: '/settings', label: 'Settings', icon: 'settings' },
];
export default function Sidebar() {
    return <aside className="sidebar">
    <Link className="brand" to="/dashboard">
    <span className="brand-mark">J<span>↗</span>
    </span>
    <span>JobPilot<span className="brand-ai">AI</span>
    </span>
    </Link>
    <span className="nav-caption">YOUR WORKSPACE</span>
    <nav aria-label="Main navigation" className="side-nav">{links.map(link => <NavLink key={link.to} to={link.to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <Icon name={link.icon}/>{link.label}</NavLink>)}</nav>
    <div className="sidebar-bottom">
    <div className="sidebar-note">
    <span className="small-orbit">
    <Icon name="spark"/>
    </span>
    <h3>Start with your story.</h3>
    <p>A great next step begins with a clear picture of you.</p>
    <Link to="/resume">Add your resume <Icon name="arrow" size={16}/>
    </Link>
    </div>
    <div className="sidebar-foot">A little more direction. Every day.</div>
    </div>
    </aside>;
}
