import { Link } from 'react-router-dom';
import Icon from '../../components/ui/Icon';
export default function Home() {
    return <div className="landing-page">
    <nav className="landing-nav" aria-label="Main navigation">
    <Link to="/" className="brand">
    <span className="brand-mark">J<span>↗</span>
    </span>
    <span>JobPilot<span className="brand-ai">AI</span>
    </span>
    </Link>
    <div className="button-row">
    <Link to="/login" className="text-link">Sign in</Link>
    <Link to="/register" className="btn btn-primary">Get started <Icon name="arrow" size={16}/>
    </Link>
    </div>
    </nav>
    <main>
    <section className="landing-hero">
    <div>
    <span className="eyebrow">A LITTLE DIRECTION FOR WHAT’S NEXT</span>
    <h1>Your career.<br />Your story.<br />
    <em>Your next chapter.</em>
    </h1>
    <p>Give your experience a place to grow. Start with your resume in a personal workspace built for your next career move.</p>
    <div className="button-row">
    <Link to="/register" className="btn btn-primary">Create your workspace <Icon name="arrow" size={18}/>
    </Link>
    <a href="#how-it-works" className="text-link">See how it works ↓</a>
    </div>
    <span className="hero-caption">Start with a PDF. Take it one step at a time.</span>
    </div>
    <div className="landing-art">
    <div className="landing-art-top">
    <span className="status-dot"/> A clearer path forward</div>
    <div className="landing-document">
    <span className="feature-icon">
    <Icon name="file" size={30}/>
    </span>
    <h2>Experience,<br />with perspective.</h2>
    <div className="paper-line"/>
    <div className="paper-line"/>
    <div className="paper-line short"/>
    <div className="landing-art-note">
    <Icon name="check"/> Upload. Extract. Begin.</div>
    </div>
    <span className="landing-star">✳</span>
    </div>
    </section>
    <section id="how-it-works" className="landing-features">
    <span className="eyebrow">BUILT ONE THOUGHTFUL STEP AT A TIME</span>
    <h2>Make a start. Find your direction.</h2>
    <div className="step-grid">{[{ number: '01', title: 'Your own workspace', text: 'Create an account and keep your starting point in one place.' }, { number: '02', title: 'Bring your resume', text: 'Upload a text-based PDF and extract the words behind your experience.' }, { number: '03', title: 'More to come', text: 'Structured profiles, job matching, and application tracking are on the roadmap.' }].map(item => <article className="card step-card" key={item.number}>
        <span className="step-number">{item.number}</span>
        <h3>{item.title}</h3>
        <p>{item.text}</p>
        </article>)}</div>
    </section>
    </main>
    <footer className="landing-footer">
    <strong>JobPilot AI</strong>
    <span>Your next chapter starts with you.</span>
    <Link to="/login">Open your workspace ↗</Link>
    </footer>
    </div>;
}
