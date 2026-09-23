import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useProfile } from '../../hooks/useProfile';
import PageHeader from '../../components/ui/PageHeader';
import ProfileDetails from '../../components/Profile/ProfileDetails';

export default function Profile() {
    const {user} = useAuth();
    const {profile, loading, error, retry} = useProfile();
    return <>
        <PageHeader eyebrow="A PICTURE OF YOU" title="Your confirmed profile" description="Your experience, reviewed by you. A reliable starting point for what comes next."/>
        {loading ? <p role="status" className="form-note">Loading your confirmed profile…</p> : error ? <div className="card"><p className="notice error" role="alert">{error}</p><button className="btn btn-secondary" onClick={retry}>Retry</button></div> : profile ? <section className="card profile-card">
            <div className="draft-toolbar"><div className="profile-identity"><span className="avatar avatar-large">{(profile.data.contact.name ?? user?.name ?? '?').slice(0, 1).toUpperCase()}</span><div><h2>{profile.data.contact.name ?? 'Your professional profile'}</h2><span className="pill teal">Confirmed by you</span><p className="form-note">Updated {new Date(profile.updated_at + (profile.updated_at.endsWith('Z') ? '' : 'Z')).toLocaleDateString()}</p></div></div>{profile.source_resume_id && <Link className="btn btn-primary" to={`/resume/${profile.source_resume_id}/review`}>Edit profile</Link>}</div>
            <ProfileDetails data={profile.data}/>
            <div className="draft-section"><p className="form-note">Your confirmed details are stored separately from extraction results. Rebuilding a draft does not change this profile.</p><Link className="text-link" to={profile.source_resume_id ? `/resume?id=${profile.source_resume_id}` : '/resume'}>View source resume</Link></div>
        </section> : <section className="card profile-empty"><span className="eyebrow">YOUR NEXT STEP</span><h2>Turn your resume into your profile.</h2><p>Build a structured draft, correct the details, and confirm them. Your skills, experience, education, and projects will appear here.</p><Link className="btn btn-primary" to="/resume">Review a resume</Link></section>}
        <section className="subtle-card section-block"><h3>Your sign-in account</h3><p>{user?.name} · {user?.email}</p><p className="form-note">Professional contact details above can differ from your sign-in details. Editing your profile does not change your login.</p></section>
    </>;
}
