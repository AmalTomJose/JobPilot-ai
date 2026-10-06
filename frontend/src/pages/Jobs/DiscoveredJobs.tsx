import {useEffect, useState} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {discoveredService, discoverySources, type DiscoverySource, type DiscoveredJob} from '../../services/discovered.service';
import type {Page} from '../../types/job.types';
import {apiError} from '../../api/axios';
import PageHeader from '../../components/ui/PageHeader';

export default function DiscoveredJobs() {
    const [params, setParams] = useSearchParams();
    const requestedSite = params.get('site') || 'all';
    const site: DiscoverySource = Object.hasOwn(discoverySources, requestedSite) ? requestedSite as DiscoverySource : 'all';
    const requestedStatus = params.get('status') || 'pending';
    const status = ['pending','dismissed','approved'].includes(requestedStatus) ? requestedStatus : 'pending';
    const requestedOffset = Number(params.get('offset') || 0);
    const offset = Number.isSafeInteger(requestedOffset) && requestedOffset >= 0 ? requestedOffset : 0;
    function filter(key: string, value: string) {setParams(previous => {const next = new URLSearchParams(previous); next.set(key,value); if(key !== 'offset') next.delete('offset'); return next;});}
    const [data, setData] = useState<Page<DiscoveredJob> | null>(null);
    const [refresh, setRefresh] = useState(0);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState('');
    useEffect(() => {
        let active = true;
        async function load() {
            setLoading(true); setError('');
            try {const result = await discoveredService.list(status, offset, site); if(active) setData(result);}
            catch(error) {if(active) setError(apiError(error));}
            finally {if(active) setLoading(false);}
        }
        void load();
        return () => {active = false;};
    }, [status, offset, site, refresh]);
    async function update(item: DiscoveredJob) {
        setBusy(true); setError('');
        try {await discoveredService.status(item.id, item.status === 'dismissed' ? 'pending' : 'dismissed'); setRefresh(value => value+1);}
        catch(error) {setError(apiError(error));}
        finally {setBusy(false);}
    }
    async function backfill() {
        setBusy(true); setError(''); setNotice('Checking previously imported emails…');
        try {
            let cursor: number | null = 0; let count = 0;
            do {const result = await discoveredService.backfill(cursor); count += result.created; cursor = result.next_cursor;} while(cursor !== null);
            setNotice(`${count} openings discovered across all sources. Existing drafts and saved jobs were kept.`);
            filter('offset','0'); setRefresh(value => value+1);
        } catch(error) {setNotice(''); setError(apiError(error));}
        finally {setBusy(false);}
    }
    return <>
        <PageHeader eyebrow="AUTOMATIC DISCOVERY · YOUR APPROVAL" title={site === 'all' ? 'Discovered jobs' : `${discoverySources[site]} openings`} description="Gmail collects possible openings here. Review an opening before adding it to your saved jobs." action={<Link className="btn btn-secondary" to="/jobs">Saved jobs</Link>}/>
        <section className="card section-block">
            <div className="button-row"><div className="field"><label htmlFor="discovery-source">Source website</label><select id="discovery-source" value={site} disabled={busy} onChange={event => filter('site',event.target.value)}>{Object.entries(discoverySources).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></div><div className="field"><label htmlFor="discovery-status">Show</label><select id="discovery-status" value={status} disabled={busy} onChange={event => filter('status',event.target.value)}><option value="pending">Awaiting review</option><option value="dismissed">Dismissed</option><option value="approved">Approved</option></select></div><button className="btn btn-secondary" disabled={busy || loading} onClick={() => setRefresh(value => value+1)}>Refresh</button><button className="text-link" disabled={busy} onClick={() => void backfill()}>Discover from existing emails</button><Link className="text-link" to="/settings">Gmail settings →</Link></div>
            <p className="form-note">An email summary may not contain the full description. Open the original job to check it. Dismissed openings stay hidden from the review queue even if another email mentions them.</p>
        </section>
        {notice && <p className="notice" role="status">{notice}</p>}
        {error && <p className="notice error" role="alert">{error}</p>}
        {loading ? <p role="status">Loading discovered jobs…</p> : data && <section className="section-block">
            <div className="section-heading"><h2>{status === 'pending' ? 'Awaiting your review' : status === 'dismissed' ? 'Dismissed openings' : 'Approved openings'}</h2><span>{data.total} opening{data.total === 1 ? '' : 's'}</span></div>
            {!data.items.length && <div className="card profile-empty"><h3>No openings in this view.</h3><p>Sync your selected Gmail label, or discover openings from emails you already imported.</p></div>}
            <div className="job-grid">{data.items.map(item => <article className="card job-card" key={item.id}>
                <span className="pill teal">{discoverySources[item.source_site]}</span><span className="pill neutral">{item.status === 'pending' ? 'Needs review' : item.status}</span>
                <h3>{item.draft_data.title || 'Job title needs review'}</h3><p>{item.draft_data.company || 'Company not identified'}</p>
                <p className="form-note">{item.status === 'approved' ? 'Saved after your review. Open the saved job for its confirmed details.' : item.draft_data.description ? 'Email text available — verify the full description.' : 'Full description needed.'}</p>
                <div className="button-row">{item.gmail_url && <a className="btn btn-secondary" href={item.gmail_url} target="_blank" rel="noopener noreferrer" title="Opens Gmail in a new tab. Sign in to the mailbox that received this email.">Open original email in Gmail ↗</a>}{item.job_url && <a className="text-link" href={item.job_url} target="_blank" rel="noopener noreferrer">Go to website ↗</a>}
                {item.status === 'approved' && item.job_id ? <Link className="btn btn-primary" to={`/jobs/${item.job_id}`}>View saved job</Link> : item.status === 'pending' && <Link className="btn btn-primary" to={`/jobs/discovered/${item.id}?${params.toString()}`}>Review</Link>}
                {item.status !== 'approved' && <button className="text-link" disabled={busy} onClick={() => void update(item)}>{item.status === 'dismissed' ? 'Restore' : 'Dismiss'}</button>}</div>
            </article>)}</div>
            <div className="job-pagination"><button className="btn btn-secondary" disabled={offset === 0 || busy} onClick={() => filter('offset',String(Math.max(0,offset-20)))}>Previous</button><button className="btn btn-secondary" disabled={offset+20 >= data.total || busy} onClick={() => filter('offset',String(offset+20))}>Next</button></div>
        </section>}
    </>;
}
