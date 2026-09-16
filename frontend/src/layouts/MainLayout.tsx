import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar/Sidebar';
import Navbar from '../components/Navbar/Navbar';
export default function MainLayout() {
    return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <Sidebar />
    <div className="workspace">
    <Navbar />
    <main id="main-content" className="page-content">
    <Outlet />
    </main>
    <footer className="workspace-footer">
    <span>JobPilot AI</span>
    <span>One thoughtful step toward what’s next.</span>
    </footer>
    </div>
    </div>;
}
