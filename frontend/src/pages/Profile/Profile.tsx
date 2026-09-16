import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import PageHeader from '../../components/ui/PageHeader';
import Icon from '../../components/ui/Icon';
export default function Profile() {
    const { user } = useAuth();
    return <>
    <PageHeader eyebrow="A PICTURE OF YOU" title="Your profile" description="Your account today. Your experience, brought together next."/>
    <div className="content-with-aside">
    <section className="card profile-card">
    <div className="profile-identity">
    <span className="avatar avatar-large">{user?.name.slice(0, 1).toUpperCase()}</span>
    <div>
    <h2>{user?.name}</h2>
    <span className="pill teal">Personal account</span>
    </div>
    </div>
    <dl className="detail-list">
    <div>
    <dt>Full name</dt>
    <dd>{user?.name}</dd>
    </div>
    <div>
    <dt>Email address</dt>
    <dd>{user?.email}</dd>
    </div>
    </dl>
    <p className="form-note">These details were provided at registration. Account editing is not available yet.</p>
    </section>
    <section className="subtle-card">
    <Icon name="file" size={26}/>
    <h3>More than a name on a page.</h3>
    <p>Skills, education, and work experience will appear here once resume parsing and review are available.</p>
    <Link to="/resume" className="text-link">Start with your resume <Icon name="arrow" size={16}/>
    </Link>
    </section>
    </div>
    </>;
}
