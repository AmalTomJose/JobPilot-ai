import {useEffect,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {jobService} from '../../services/job.service';
import {apiError} from '../../api/axios';
import type {Job,ImportSummary,Page,JobFilters,WorkMode} from '../../types/job.types';
import PageHeader from '../../components/ui/PageHeader';

export default function Jobs() {
    const [params,setParams]=useSearchParams();
    const q=(params.get('q')??'').slice(0,200);
    const status=params.get('status')??'saved';
    const source=params.get('source')??'';
    const mode=params.get('work_mode')??'';
    const offset=Math.max(0,Number(params.get('offset'))||0);
    const [importOffset,setImportOffset]=useState(0);
    const [jobs,setJobs]=useState<Page<Job>|null>(null);
    const [imports,setImports]=useState<Page<ImportSummary>|null>(null);
    const [loading,setLoading]=useState(true);
    const [error,setError]=useState('');
    const [attempt,setAttempt]=useState(0);
    useEffect(()=>{
        let active=true;
        async function load(){
            setLoading(true);setError('');
            const filters:JobFilters={q,offset:Number.isSafeInteger(offset)?offset:0,limit:20};
            if(status==='saved'||status==='archived')filters.status=status;
            if(source==='manual'||source==='email')filters.source=source;
            if(['remote','hybrid','onsite'].includes(mode))filters.work_mode=mode as WorkMode;
            try {const [saved,pending]=await Promise.all([jobService.list(filters),jobService.imports(importOffset)]);if(active){setJobs(saved);setImports(pending);}}
            catch(error){if(active)setError(apiError(error));}
            finally{if(active)setLoading(false);}
        }
        void load();return()=>{active=false;};
    },[q,status,source,mode,offset,importOffset,attempt]);
    function filter(name:string,value:string){const next=new URLSearchParams(params);next.set(name,value);next.delete('offset');setParams(next);}
    function page(value:number){const next=new URLSearchParams(params);next.set('offset',String(value));setParams(next);}
    return <>
        <PageHeader eyebrow="OPPORTUNITIES, IN ONE PLACE" title="Your job inbox" description="Collect openings, review the details, and keep your next move in sight." action={<div className="button-row"><Link className="btn btn-secondary" to="/jobs/new">Add job</Link><Link className="btn btn-primary" to="/jobs/import">Paste job email</Link></div>}/>
        <section className="card job-filters"><form key={q} className="job-search" onSubmit={event=>{event.preventDefault();filter('q',String(new FormData(event.currentTarget).get('q')??'').trim());}}><label className="sr-only" htmlFor="job-search">Search jobs</label><input id="job-search" name="q" defaultValue={q} maxLength={200} placeholder="Search title, company, location or description"/><button className="btn btn-secondary" type="submit">Search</button></form>
            <div className="job-filter-row"><div className="field"><label htmlFor="filter-status">Status</label><select id="filter-status" value={status} onChange={event=>filter('status',event.target.value)}><option value="saved">Saved</option><option value="archived">Archived</option><option value="">All statuses</option></select></div><div className="field"><label htmlFor="filter-source">Source</label><select id="filter-source" value={source} onChange={event=>filter('source',event.target.value)}><option value="">All sources</option><option value="manual">Manual</option><option value="email">Email</option></select></div><div className="field"><label htmlFor="filter-mode">Work arrangement</label><select id="filter-mode" value={mode} onChange={event=>filter('work_mode',event.target.value)}><option value="">All arrangements</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">On-site</option></select></div><button className="text-link" onClick={()=>setParams({})}>Reset filters</button></div>
        </section>
        {loading?<p role="status" className="section-block">Loading your job inbox…</p>:error?<div role="alert" className="notice error section-block">{error}<button className="btn btn-secondary" onClick={()=>setAttempt(value=>value+1)}>Retry</button></div>:<>
            {imports && imports.total>0 && <section className="card section-block pending-jobs"><div className="section-heading"><div><span className="eyebrow">READY FOR YOUR REVIEW</span><h2>Email drafts</h2></div><span className="pill neutral">{imports.total} awaiting review</span></div><p className="form-note">Extraction is saved. Review a draft before adding it to your jobs.</p>{imports.items.map(item=><Link key={item.id} className="pending-job" to={`/jobs/imports/${item.id}/review`}><div><strong>{item.title??'Untitled job email'}</strong><p>{item.company??'Company not identified'}</p></div><span className="text-link">Review →</span></Link>)}<div className="job-pagination"><button className="text-link" disabled={importOffset===0} onClick={()=>setImportOffset(value=>Math.max(0,value-10))}>Previous drafts</button><button className="text-link" disabled={importOffset+10>=imports.total} onClick={()=>setImportOffset(value=>value+10)}>Next drafts</button></div></section>}
            <section className="section-block"><div className="section-heading"><h2>Saved opportunities</h2><span className="muted small">{jobs?.total??0} result{jobs?.total===1?'':'s'}</span></div>
                {jobs && jobs.items.length>0?<div className="job-grid">{jobs.items.map(job=><Link className="card job-card" to={`/jobs/${job.id}`} key={job.id}><div className="job-card-top"><span className="pill neutral">{job.source_type==='email'?'From email':'Manual'}</span><span className="small muted">{job.status}</span></div><h3>{job.title}</h3><p className="job-company">{job.company??'Company not provided'}</p><p className="form-note">{[job.location,job.work_mode,job.employment_type].filter(Boolean).join(' · ')||'Location and arrangement not provided'}</p><div className="draft-skills">{job.skills.slice(0,4).map((skill,index)=><span className="pill teal" key={index}>{skill}</span>)}{job.skills.length>4&&<span className="pill neutral">+{job.skills.length-4}</span>}</div><span className="text-link">View job →</span></Link>)}</div>:<div className="card profile-empty"><h3>No jobs in this view yet.</h3><p>Add an opportunity, review an email draft, or change your filters.</p><Link className="text-link" to="/jobs/new">Add your first job →</Link></div>}
                {jobs && (jobs.total>20 || offset>0) && <div className="job-pagination"><button className="btn btn-secondary" disabled={offset===0} onClick={()=>page(Math.max(0,offset-20))}>Previous jobs</button><span className="form-note">Page {Math.floor(offset/20)+1}</span><button className="btn btn-secondary" disabled={offset+20>=jobs.total} onClick={()=>page(offset+20)}>Next jobs</button></div>}
            </section>
        </>}
    </>;
}
