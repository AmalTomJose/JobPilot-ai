import type { ProfileData } from '../../types/profile.types';

export default function ProfileDetails({data}: {data: ProfileData}) {
    return <>
        <div className="draft-grid">
            <section><h3>Contact information</h3><dl className="detail-list">{(['name', 'email', 'phone', 'location'] as const).map(field => <div key={field}><dt>{field}</dt><dd>{data.contact[field] ?? 'Not provided'}</dd></div>)}</dl>{data.contact.links.map((link, index) => <p className="small draft-link" key={index}>{link}</p>)}</section>
            <section><h3>Summary & skills</h3><p className="draft-copy">{data.summary ?? 'No summary added.'}</p><div className="draft-skills">{data.skills.length ? data.skills.map((skill, index) => <span className="pill teal" key={index}>{skill}</span>) : <p className="form-note">No skills added.</p>}</div></section>
        </div>
        <section className="draft-section"><h3>Experience</h3>{!data.experience.length && <p className="form-note">No experience added.</p>}{data.experience.map((entry, index) => <article className="draft-entry" key={index}><h4>{entry.title ?? 'Role not provided'}</h4><p>{[entry.company, entry.location, entry.date_text].filter(Boolean).join(' · ')}</p><ul>{entry.description.map((line, i) => <li key={i}>{line}</li>)}</ul></article>)}</section>
        <section className="draft-section"><h3>Education</h3>{!data.education.length && <p className="form-note">No education added.</p>}{data.education.map((entry, index) => <article className="draft-entry" key={index}><h4>{entry.degree ?? 'Qualification not provided'}</h4><p>{[entry.institution, entry.field_of_study, entry.date_text].filter(Boolean).join(' · ')}</p></article>)}</section>
        <section className="draft-section"><h3>Projects</h3>{!data.projects.length && <p className="form-note">No projects added.</p>}{data.projects.map((entry, index) => <article className="draft-entry" key={index}><h4>{entry.name ?? 'Project name not provided'}</h4><ul>{entry.description.map((line, i) => <li key={i}>{line}</li>)}</ul><p>{entry.technologies.join(', ')}</p>{entry.links.map((link, i) => <p className="draft-link" key={i}>{link}</p>)}</article>)}</section>
    </>;
}
