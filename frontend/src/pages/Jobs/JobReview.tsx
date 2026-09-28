import {useEffect, useState} from 'react';
import {Link, useParams} from 'react-router-dom';
import {jobService} from '../../services/job.service';
import {apiError} from '../../api/axios';
import type {JobDetail, JobImport} from '../../types/job.types';
import JobEditor from '../../components/Jobs/JobEditor';

export default function JobReview({editing = false}: {editing?: boolean}) {
    const params = useParams();
    const id = Number(editing ? params.jobId : params.importId);
    if (!Number.isSafeInteger(id) || id<=0) return <p className="notice error">This job or import could not be found. <Link to="/jobs">Back to jobs</Link></p>;
    return <ReviewLoader key={`${editing}-${id}`} id={id} editing={editing}/>;
}
function ReviewLoader({id, editing}: {id:number; editing:boolean}) {
    const [result,setResult] = useState<{job:JobDetail|null;source:JobImport|null}|null>(null);
    const [error,setError] = useState('');
    const [attempt,setAttempt] = useState(0);
    useEffect(()=>{
        let active=true;
        async function load() {
            setError('');
            try {
                const next = editing ? await jobService.get(id).then(job=>({job,source:job.source})) : await jobService.getImport(id).then(source=>({job:null,source}));
                if(active) setResult(next);
            } catch(error) {if(active) setError(apiError(error));}
        }
        void load(); return ()=>{active=false;};
    },[id,editing,attempt]);
    if(error) return <section className="card"><p role="alert" className="notice error">{error}</p><button className="btn btn-secondary" onClick={()=>setAttempt(value=>value+1)}>Retry</button> <Link className="text-link" to="/jobs">Back to jobs</Link></section>;
    if(!result) return <p role="status">Opening job details…</p>;
    return <JobEditor job={result.job} source={result.source}/>;
}
