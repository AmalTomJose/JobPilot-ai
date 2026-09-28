import {Link} from 'react-router-dom';
import type {MatchItem} from '../../types/match.types';

export default function MatchCard({item}: {item: MatchItem}) {
    const total = item.matched_skills.length + item.missing_skills.length;
    return <article className="card match-card">
        <div className="match-card-heading"><div><span className="pill neutral">{item.job_status === 'archived' ? 'Archived job' : 'Saved job'}</span><h2><Link to={`/jobs/${item.job_id}`}>{item.title}</Link></h2><p className="muted">{item.company || 'Company not provided'}</p></div>
            <div className="match-score">{item.state === 'pending' ? <strong>Not checked</strong> : item.state === 'outdated' ? <strong>Outdated</strong> : item.score === null ? <strong>Not enough information</strong> : <><strong>{item.score}%</strong><span>listed-skill coverage</span></>}</div>
        </div>
        {item.state === 'pending' ? <p className="form-note">{item.job_status === 'archived' ? 'Change this job’s status to Saved in the job editor, then find matches to compare it.' : 'Choose Find matches to compare this job with your confirmed profile.'}</p> : <>
            {item.state === 'outdated' && <p className="notice">Your profile, this job, or the matching rules changed. {item.job_status === 'archived' ? 'Restore this job to Saved before finding matches again.' : 'Find matches again to refresh this result.'} The breakdown below is from the previous check.</p>}
            {item.score === null ? <p className="form-note">{item.reason === 'profile_skills_missing' ? 'Add skills to your confirmed profile before comparing.' : 'This job has no listed skills. Edit the job to add skills supported by its description.'}</p> : <>
                <p className="form-note">{item.matched_skills.length} of {total} unique listed skills matched{item.state === 'outdated' ? ' in the previous check' : ''}. Missing means not listed in your profile, not that you cannot do it.</p>
                <div className="match-breakdown"><section><h3>Matched skills</h3>{item.matched_skills.length ? <ul>{item.matched_skills.map(skill => <li key={skill.job_skill}><span className="pill teal">{skill.job_skill}</span>{skill.job_skill !== skill.profile_skill && <span className="form-note">Your profile: {skill.profile_skill}</span>}</li>)}</ul> : <p className="form-note">No listed skills overlap yet.</p>}</section>
                    <section><h3>Not listed in your profile</h3>{item.missing_skills.length ? <div className="draft-skills">{item.missing_skills.map(skill => <span className="pill neutral" key={skill}>{skill}</span>)}</div> : <p className="form-note">All listed skills are covered.</p>}</section></div>
            </>}
            <p className="form-note">Checked {item.computed_at ? new Date(`${item.computed_at}${/[zZ]|[+-]\d\d:\d\d$/.test(item.computed_at) ? '' : 'Z'}`).toLocaleString() : 'previously'}</p>
        </>}
        <div className="button-row"><Link className="text-link" to={`/jobs/${item.job_id}`}>View job →</Link><Link className="text-link" to={`/jobs/${item.job_id}/edit`}>Edit job skills</Link></div>
    </article>;
}
