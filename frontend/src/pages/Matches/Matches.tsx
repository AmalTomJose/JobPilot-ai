import {useEffect, useState} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {matchService} from '../../services/match.service';
import type {MatchPage} from '../../types/match.types';
import {apiError} from '../../api/axios';
import PageHeader from '../../components/ui/PageHeader';
import MatchCard from './MatchCard';

export default function Matches() {
    const [params, setParams] = useSearchParams();
    const archived = params.get('archived') === 'true';
    const rawOffset = Number(params.get('offset') || 0);
    const offset = Number.isSafeInteger(rawOffset) && rawOffset >= 0 ? rawOffset : 0;
    const [data, setData] = useState<MatchPage | null>(null);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState('');
    const [runError, setRunError] = useState('');
    const [notice, setNotice] = useState('');
    const [attempt, setAttempt] = useState(0);
    useEffect(() => {
        let active = true;
        async function load() {
            setLoading(true); setError('');
            try {const result = await matchService.list(archived, offset); if (active) setData(result);}
            catch (error) {if (active) setError(apiError(error));}
            finally {if (active) setLoading(false);}
        }
        void load();
        return () => {active = false;};
    }, [archived, offset, attempt]);
    async function run() {
        setRunning(true); setRunError(''); setNotice('');
        try {
            const result = await matchService.run();
            setNotice(`Checked ${result.processed} saved jobs: ${result.scored} scored, ${result.insufficient} with insufficient information. Archived jobs were excluded.`);
            setParams(archived ? {archived: 'true'} : {});
            setAttempt(value => value + 1);
        } catch (error) {setRunError(apiError(error));}
        finally {setRunning(false);}
    }
    function page(next: number) {setParams({...(archived ? {archived: 'true'} : {}), offset: String(next)});}
    return <>
        <PageHeader eyebrow="UNDERSTAND YOUR OPTIONS" title="Your job matches" description="Compare your confirmed skills with the jobs you saved. Every result comes with a breakdown." action={<button className="btn btn-primary" onClick={run} disabled={running || loading || !!error || !data?.profile_ready || !data?.profile_has_skills || !data.total}>{running ? 'Comparing skills…' : 'Find matches'}</button>}/>
        <section className="subtle-card match-explainer"><h2>What does the score mean?</h2><p>2 matched skills out of 3 listed skills = 66.7% coverage. We compare exact names and a small set of common aliases. The score does not measure hiring chances, experience level, location fit, or salary fit.</p><Link className="text-link" to="/profile">Review your profile →</Link></section>
        <div className="match-controls"><label><input type="checkbox" checked={archived} disabled={running} onChange={event => setParams(event.target.checked ? {archived: 'true'} : {})}/> Show archived jobs</label><button className="text-link" disabled={running || loading} onClick={() => setAttempt(value => value + 1)}>Refresh results</button></div>
        {notice && <p className="notice success" role="status">{notice}</p>}
        {runError && <p className="notice error" role="alert">{runError}</p>}
        {loading ? <p role="status">Loading matches…</p> : error ? <div className="notice error" role="alert">{error}<button className="btn btn-secondary" onClick={() => setAttempt(value => value + 1)}>Retry</button></div> : data && <>
            {!data.profile_ready ? <section className="card profile-empty"><h2>Start with a confirmed profile</h2><p>Upload your resume, review its draft, and save your profile before finding matches.</p><Link className="btn btn-primary" to="/resume">Review your resume</Link></section> : !data.profile_has_skills ? <p className="notice">Your confirmed profile has no skills yet. <Link to="/profile">Review your profile</Link> before comparing jobs.</p> : null}
            {!!(data.pending || data.outdated) && <p className="notice">Not checked: {data.pending} · Outdated: {data.outdated}. Find matches updates saved jobs; archived results are kept for reference.</p>}
            {!data.total ? <section className="card profile-empty"><h2>No jobs to compare yet</h2><p>Add a job or review a pasted email in your job inbox.</p><Link className="btn btn-secondary" to="/jobs">Open job inbox</Link></section> : <div className="match-list">{data.items.map(item => <MatchCard item={item} key={item.job_id}/>)}</div>}
            {!!data.total && !data.items.length && <p className="form-note">No results on this page. Go back to the previous page.</p>}
            {(data.total > 20 || offset > 0) && <div className="job-pagination"><button className="btn btn-secondary" disabled={!offset || running} onClick={() => page(Math.max(0, offset-20))}>Previous</button><span>Page {Math.floor(offset/20)+1}</span><button className="btn btn-secondary" disabled={offset+20 >= data.total || running} onClick={() => page(offset+20)}>Next</button></div>}
        </>}
    </>;
}
