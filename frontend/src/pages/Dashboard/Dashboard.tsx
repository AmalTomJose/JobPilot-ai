import ProfileSummary from '../../components/Profile/ProfileSummary';
import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import Icon, { type IconName } from '../../components/ui/Icon';
import PageHeader from '../../components/ui/PageHeader';
const steps = [{ number: '01', title: 'Bring your experience', text: 'Upload your resume as a PDF.', icon: 'upload' }, { number: '02', title: 'Make it readable', text: 'Extract text and build a structured draft.', icon: 'file' }, { number: '03', title: 'Build your profile', text: 'Review your draft and confirm your profile.', icon: 'user' }] as const;
export default function Dashboard() {
    const { user } = useAuth();
    return <>
    <PageHeader eyebrow="YOUR CAREER, IN FOCUS" title={`Welcome back, ${user?.name.split(' ')[0] || 'there'}.`} description="A little clarity today. A little closer to your next chapter." action={<span className="date-chip">Your personal workspace</span>}/>
    <ProfileSummary/>
    <section className="welcome-banner">
    <div className="welcome-copy">
    <span className="pill light">
    <span className="status-dot"/> START HERE</span>
    <h2>Your experience.<br />
    <em>A new perspective.</em>
    </h2>
    <p>Bring your resume into JobPilot. We’ll extract the text so you can take the next step with a clearer starting point.</p>
    <Link to="/resume" className="btn btn-dark">Upload your resume <Icon name="arrow" size={18}/>
    </Link>
    <span className="hero-caption">PDF format · Up to 5 MB</span>
    </div>
    <div className="resume-art" aria-hidden="true">
    <div className="orbit orbit-one"/>
    <div className="orbit orbit-two"/>
    <div className="art-spark">✳</div>
    <div className="paper-card">
    <div className="paper-avatar"/>
    <div className="paper-line title"/>
    <div className="paper-line short"/>
    <div className="paper-rule"/>
    <div className="paper-label">EXPERIENCE</div>
    <div className="paper-line"/>
    <div className="paper-line"/>
    <div className="paper-line short"/>
    <div className="paper-label">YOUR NEXT CHAPTER</div>
    <div className="paper-tags">
    <i />
    <i />
    <i />
    </div>
    </div>
    <div className="art-label">
    <span>
    <Icon name="check" size={16}/>
    </span> A clearer starting point</div>
    </div>
    </section>
    <section className="section-block">
    <div className="section-heading">
    <div>
    <span className="eyebrow">SMALL STEPS, REAL PROGRESS</span>
    <h2>Your path forward</h2>
    </div>
    <span className="muted small">Built around you</span>
    </div>
    <div className="step-grid">{steps.map(step => <div className="card step-card" key={step.number}>
        <div className="step-top">
        <span className="feature-icon">
        <Icon name={step.icon}/>
        </span>
        <span className="step-number">{step.number}</span>
        </div>
        <h3>{step.title}</h3>
        <p>{step.text}</p></div>)}</div>
    </section>
    <section className="section-block">
    <div className="section-heading">
    <h2>A workspace that grows with you</h2>
    </div>
    <div className="two-columns">{([{ icon: 'briefcase', title: 'Find your fit', text: 'Job discovery and matching will bring opportunities closer to your experience.', to: '/jobs', link: 'Explore what’s ahead' }, { icon: 'send', title: 'Keep your next move in view', text: 'A dedicated place for your applications, from first interest to the next conversation.', to: '/applications', link: 'Visit applications' }] as {
            icon: IconName;
            title: string;
            text: string;
            to: string;
            link: string;
        }[]).map(card => <Link className="card roadmap-card" to={card.to} key={card.to}>
        <span className="feature-icon neutral-icon">
        <Icon name={card.icon}/>
        </span>
        <div>
        <span className="eyebrow">ON THE ROADMAP</span>
        <h3>{card.title}</h3>
        <p>{card.text}</p>
        <span className="text-link">{card.link} <Icon name="arrow" size={16}/>
        </span>
        </div>
        </Link>)}</div>
    </section>
    </>;
}
