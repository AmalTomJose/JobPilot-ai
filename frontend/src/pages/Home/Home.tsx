import "./Home.css";
import {Link} from "react-router-dom";

function Home() {
  return (
    <div className="home">

      {/* Navbar */}

      <nav className="navbar">

        <div className="logo">
          JobPilot AI
        </div>

        <ul className="nav-links">
          <li>Home</li>
          <li>Features</li>
          <li>Pricing</li>
          <li>About</li>
        </ul>

        <div className="buttons">
          <button className="login-btn" >
            <Link to ="/login"/>
            Login
          </button>

          <button className="signup-btn">
            Get Started
          </button>
        </div>

      </nav>

      {/* Hero Section */}

      <section className="hero">

        <div className="hero-left">

          <h1>
            Find Your Dream Job
            <br />
            with AI
          </h1>

          <p>
            Build ATS-friendly resumes, generate cover letters,
            search thousands of jobs, and track every application
            from one dashboard.
          </p>

          <div className="hero-buttons">

            <button className="primary-btn">
              Start Free
            </button>

            <button className="secondary-btn">
              Learn More
            </button>

          </div>

        </div>

        <div className="hero-right">

          <div className="dashboard-preview">

            <h3>AI Resume Score</h3>

            <h2>92%</h2>

            <div className="skills">
              ✔ React
              <br />
              ✔ FastAPI
              <br />
              ✔ PostgreSQL
              <br />
              ✔ Docker
            </div>

          </div>

        </div>

      </section>

      {/* Features */}

      <section className="features">

        <h2>Features</h2>

        <div className="feature-container">

          <div className="feature-card">
            <h3>AI Resume Builder</h3>
            <p>Create professional resumes in minutes.</p>
          </div>

          <div className="feature-card">
            <h3>Job Search</h3>
            <p>Search thousands of jobs from multiple platforms.</p>
          </div>

          <div className="feature-card">
            <h3>Application Tracker</h3>
            <p>Track every interview and application status.</p>
          </div>

        </div>

      </section>

      {/* Footer */}

      <footer>

        <h3>JobPilot AI</h3>

        <p>
          © 2026 All Rights Reserved
        </p>

      </footer>

    </div>
  );
}

export default Home;