import { NavLink } from "react-router-dom";

const Sidebar = () => {
  return (
    <aside
      style={{
        width: "220px",
        background: "#f3f4f6",
        padding: "20px",
        minHeight: "100vh",
      }}
    >
      <h3>Menu</h3>

      <ul style={{ listStyle: "none", padding: 0 }}>
        <li><NavLink to="/dashboard">Dashboard</NavLink></li>
        <li><NavLink to="/profile">Profile</NavLink></li>
        <li><NavLink to="/resume">Resume</NavLink></li>
        <li><NavLink to="/jobs">Jobs</NavLink></li>
        <li><NavLink to="/applications">Applications</NavLink></li>
        <li><NavLink to="/settings">Settings</NavLink></li>
      </ul>
    </aside>
  );
};

export default Sidebar;