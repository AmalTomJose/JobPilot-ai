import {useEffect,useState} from 'react';
import {Link,useParams} from 'react-router-dom';
import {jobService} from '../../services/job.service';
import {apiError} from '../../api/axios';
import type {JobDetail as JobRecord} from '../../types/job.types';
import PageHeader from '../../components/ui/PageHeader';

export default function JobDetail() {
    const {jobId}=useParams(); const id=Number(jobId);
    return <Detail key={jobId} id={id}/>;
}
function Detail({id}:{id:number}) {
    const [job,setJob]=useState<JobRecord|null>(null);
    const [error,setError]=useState(''); const [attempt,setAttempt]=useState(0);
    useEffect(()=>{
        let active=true;
        async function load() {
            setError('');
            if(!Number.isSafeInteger(id)||id<=0) {setError('Job not found');return;}
            try {const result=await jobService.get(id);if(active)setJob(result);} catch(error){if(active)setError(apiError(error));}
        }
        void load();return()=>{active=false;};
    },[id,attempt]);
    if(error)return <section className="card"><p role="alert" className="notice error">{error}</p><button className="btn btn-secondary" onClick={()=>setAttempt(value=>value+1)}>Retry</button> <Link className="text-link" to="/jobs">Back to jobs</Link></section>;
    if(!job)return <p role="status">Loading saved job…</p>;
    return <>
        <PageHeader eyebrow="YOUR JOB INBOX" title={job.title} description={job.company ?? 'Company not provided'} action={<Link className="btn btn-primary" to={`/jobs/${job.id}/edit`}>Edit job</Link>}/>
        <div className="review-intro"><span className={`pill ${job.status==='saved'?'teal':'neutral'}`}>{job.status==='saved'?'Saved job':'Archived job'}</span><span className="pill neutral">{job.source_type==='email'?'From email':'Manually added'}</span><Link className="text-link" to="/jobs">Back to jobs</Link></div>
        <section className="card job-detail"><dl className="detail-list"><div><dt>Location</dt><dd>{job.location??'Not provided'}</dd></div><div><dt>Work arrangement</dt><dd>{job.work_mode??'Not provided'}</dd></div><div><dt>Employment type</dt><dd>{job.employment_type??'Not provided'}</dd></div></dl>
            <div className="draft-section"><h2>Job description</h2><p className="job-description">{job.description??'No description added.'}</p></div>
            <div className="draft-section"><h3>Required skills</h3><div className="draft-skills">{job.skills.length?job.skills.map((skill,i)=><span className="pill teal" key={i}>{skill}</span>):<p className="form-note">No skills added.</p>}</div></div>
            <div className="draft-section"><h3>Application link</h3>{job.application_url?<><p className="draft-link small">{job.application_url}</p><a className="btn btn-secondary" href={job.application_url} target="_blank" rel="noopener noreferrer">Open application website ↗</a><p className="form-note">Opens an external website. JobPilot does not apply for you.</p></>:<p className="form-note">No application URL added.</p>}</div>
            <p className="form-note">Saved {new Date(job.created_at+'Z').toLocaleDateString()} · Last updated {new Date(job.updated_at+'Z').toLocaleDateString()}</p>
        </section>
        {job.source && <section className="card section-block"><h2>Original email</h2><p className="form-note">Your saved job details can differ from this unchanged source.</p><details className="draft-source"><summary>Show original email text</summary><pre>{job.source.raw_text}</pre></details><details className="draft-source"><summary>Show extraction notes</summary><ul>{job.source.warnings.map((warning,i)=><li key={i}>{warning.message}</li>)}</ul></details></section>}
    </>;
}
