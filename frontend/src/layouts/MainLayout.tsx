import { Suspense, useRef, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar/Sidebar';
import Navbar from '../components/Navbar/Navbar';
export default function MainLayout() {
    const [sidebarOpen, setSidebarOpen] = useState(() => !window.matchMedia('(max-width: 650px)').matches);
    const toggleRef = useRef<HTMLButtonElement>(null);
    const closeSidebar = () => { setSidebarOpen(false); toggleRef.current?.focus(); };
    return <div className={`app-shell ${sidebarOpen ? 'sidebar-open' : 'sidebar-collapsed'}`}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <Sidebar open={sidebarOpen} onClose={closeSidebar}/>
    <div className="workspace">
    <Navbar sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen(open => !open)} toggleRef={toggleRef}/>
    <main id="main-content" className="page-content">
    <Suspense fallback={<p role="status">Opening your workspace…</p>}><Outlet /></Suspense>
    </main>
    <footer className="workspace-footer">
    <span>JobPilot AI</span>
    <span>One thoughtful step toward what’s next.</span>
    </footer>
    </div>
    </div>;
}
