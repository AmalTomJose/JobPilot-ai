import { Link } from 'react-router-dom';
import { useProfile } from '../../hooks/useProfile';

export default function ProfileSummary() {
    const {profile, loading, error, retry} = useProfile();
    return <section className="card section-block profile-summary">
        <div className="section-heading"><div><span className="eyebrow">YOUR CONFIRMED EXPERIENCE</span><h2>{profile ? 'Your profile, ready for the next step.' : 'Build a profile you can trust.'}</h2></div><Link to="/profile" className="text-link">View profile</Link></div>
        {loading ? <p role="status">Loading your profile…</p> : error ? <div className="notice error" role="alert">{error}<button className="text-link" onClick={retry}>Retry</button></div> : profile ? <>
            <p className="draft-copy">{profile.data.summary ?? 'Your reviewed details are saved. Update them whenever your experience changes.'}</p>
            <div className="profile-stats">{[[profile.data.skills.length, 'Skills'], [profile.data.experience.length, 'Experience entries'], [profile.data.education.length, 'Education entries'], [profile.data.projects.length, 'Projects']].map(([count, label]) => <div key={label}><strong>{count}</strong><span>{label}</span></div>)}</div>
            <span className="pill teal">Confirmed profile</span>
        </> : <><p className="draft-copy">Upload a resume, build a draft, then review and confirm your details. Your saved profile will appear here.</p><Link to="/resume" className="btn btn-secondary">Review your resume</Link></>}
    </section>;
}
