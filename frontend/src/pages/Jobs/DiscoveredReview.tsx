import {useEffect, useState} from 'react';
import {Link, useParams, useLocation} from 'react-router-dom';
import {discoveredService, type DiscoveredJob} from '../../services/discovered.service';
import {apiError} from '../../api/axios';
import JobEditor from '../../components/Jobs/JobEditor';

export default function DiscoveredReview() {
    const location = useLocation();
    const backTo = '/jobs/discovered' + location.search;
    const {candidateId} = useParams();
    const [item, setItem] = useState<DiscoveredJob | null>(null);
    const [error, setError] = useState('');
    useEffect(() => {
        let active = true;
        discoveredService.get(Number(candidateId)).then(value => {if(active) setItem(value);})
            .catch(error => {if(active) setError(apiError(error));});
        return () => {active = false;};
    }, [candidateId]);
    if(error) return <p className="notice error" role="alert">{error} <Link to={backTo}>Back to discovered jobs</Link></p>;
    if(!item) return <p role="status">Loading opportunity…</p>;
    if(item.status !== 'pending') return <section className="card"><h2>This opening has already been handled.</h2><Link to={item.job_id ? `/jobs/${item.job_id}` : '/jobs/discovered'}>Continue →</Link></section>;
    return <><section className="notice"><p>Email alerts may contain only a summary. Start with Go to website to read the full job description. From that page, send a preview using the extension on a permitted site. For manual copy and paste, use Saved jobs → Import job page. Select this discovered opening when reviewing the captured description. LinkedIn uses manual copy and paste.</p><div className="button-row">{item.gmail_url && <a className="btn btn-secondary" href={item.gmail_url} target="_blank" rel="noopener noreferrer" title="Opens Gmail in a new tab. Sign in to the mailbox that received this email.">Open original email in Gmail ↗</a>}{item.job_url && <a className="btn btn-primary" href={item.job_url} target="_blank" rel="noopener noreferrer">Go to website ↗</a>}<Link className="text-link" to={backTo}>Back to discovered jobs</Link></div></section><JobEditor key={item.id} preview={item} candidateId={item.id}/></>;
}
