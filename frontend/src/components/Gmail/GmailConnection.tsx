import {useEffect, useState} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {emailService} from '../../services/email.service';
import {apiError} from '../../api/axios';
import type {GmailStatus, GmailLabel, GmailSelection, EmailPage, SyncRun} from '../../types/email.types';

function dateTime(value: string | null) {
    return value ? new Date(value + (/[zZ]|[+-]\d\d:\d\d$/.test(value) ? '' : 'Z')).toLocaleString() : 'Not yet';
}

function Selection({status, labels, busy, save}: {status: GmailStatus; labels: GmailLabel[]; busy: boolean; save: (value: GmailSelection) => void}) {
    const [label, setLabel] = useState(status.label_id || '');
    const [since, setSince] = useState(() => status.import_since?.slice(0,10) || new Date(Date.now()-30*86400000).toISOString().slice(0,10));
    const [automatic, setAutomatic] = useState(status.auto_sync);
    return <form className="gmail-selection" onSubmit={event => {event.preventDefault(); save({label_id: label, import_since: since, auto_sync: automatic});}}>
        <div className="review-fields"><div className="field"><label htmlFor="gmail-label">Job-alert label</label><select id="gmail-label" required value={label} disabled={busy} onChange={event => setLabel(event.target.value)}><option value="">Choose a label</option>{labels.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
            <div className="field"><label htmlFor="gmail-since">Import emails received on or after (UTC)</label><input id="gmail-since" type="date" required max={new Date().toISOString().slice(0,10)} value={since} disabled={busy} onChange={event => setSince(event.target.value)}/></div></div>
        {!labels.length && <p className="notice">Create a custom label such as Job Alerts in Gmail, add your job emails to it, then refresh this connection.</p>}
        <label className="gmail-checkbox"><input type="checkbox" checked={automatic} disabled={busy} onChange={event => setAutomatic(event.target.checked)}/> Enable automatic syncing</label>
        <p className="form-note">Automatic sync requires the Gmail worker to be running on the server. It checks every 15 minutes, or every 5 minutes while more pages remain. Each batch reads up to 10 selected emails. The original emails are never changed.</p>
        <button className="btn btn-secondary" disabled={busy || !label} type="submit">Save import settings</button>
    </form>;
}

export default function GmailConnection() {
    const [params] = useSearchParams();
    const [status, setStatus] = useState<GmailStatus | null>(null);
    const [labels, setLabels] = useState<GmailLabel[]>([]);
    const [messages, setMessages] = useState<EmailPage | null>(null);
    const [runs, setRuns] = useState<SyncRun[]>([]);
    const [offset, setOffset] = useState(0);
    const [attempt, setAttempt] = useState(0);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [actionError, setActionError] = useState('');
    const [labelError, setLabelError] = useState('');
    const [notice, setNotice] = useState('');
    const [confirmDisconnect, setConfirmDisconnect] = useState(false);
    useEffect(() => {
        let active = true;
        async function load() {
            setLoading(true); setError(''); setLabelError('');
            try {
                const [current, history, syncs] = await Promise.all([emailService.status(), emailService.messages(offset), emailService.runs()]);
                if (!active) return;
                setStatus(current); setMessages(history); setRuns(syncs); setLabels([]);
                if (current.configured && current.status === 'connected') {
                    try {const values = await emailService.labels(); if (active) setLabels(values);}
                    catch (error) {if (active) setLabelError(apiError(error));}
                }
            } catch (error) {if (active) setError(apiError(error));}
            finally {if (active) setLoading(false);}
        }
        void load(); return () => {active = false;};
    }, [attempt, offset]);

    async function act(action: () => Promise<string>, reload = true) {
        setBusy(true); setActionError(''); setNotice('');
        try {setNotice(await action());}
        catch (error) {setActionError(error instanceof Error ? apiError(error, error.message) : apiError(error));}
        finally {setBusy(false); if (reload) setAttempt(value => value+1);}
    }
    const outcome = params.get('gmail');
    return <section className="card gmail-panel" aria-labelledby="gmail-heading">
        <div className="section-heading"><div><span className="eyebrow">FROM YOUR MAILBOX</span><h2 id="gmail-heading">Gmail job alerts</h2></div><button className="text-link" disabled={loading || busy} onClick={() => setAttempt(value => value+1)}>Refresh connection</button></div>
        <p>Discover individual openings from selected job emails, then approve or dismiss them in Discovered jobs. Syncing never approves jobs automatically.</p>
        {outcome === 'connected' && <p className="notice success">Gmail authorization completed. Check the current connection below and choose what to import.</p>}
        {outcome === 'cancelled' && <p className="notice">Gmail authorization was cancelled. You can try connecting again.</p>}
        {outcome === 'failed' && <p className="notice error">Gmail authorization could not finish. Check the connection message below.</p>}
        {actionError && <p role="alert" className="notice error">{actionError}</p>}
        {error && <p role="alert" className="notice error">{error}</p>}
        {notice && <p role="status" className="notice success">{notice}</p>}
        {loading ? <p role="status">Loading Gmail connection…</p> : status && <>
            {!status.configured && <div className="notice"><strong>Google setup is needed.</strong><p>The server needs Google OAuth credentials and a separate encryption key. Follow docs/GMAIL_SETUP.md in the project. Do not enter your Gmail password or client secret here.</p></div>}
            <p className="form-note">Status: {status.status.replaceAll('_',' ')}{status.mailbox_email ? ` · ${status.mailbox_email}` : ''}</p>
            {status.last_error && <p className="notice error" role="alert">{status.last_error}</p>}
            {status.status !== 'connected' && <><p className="form-note">Google grants read-only mailbox access, which is broader than one label. JobPilot fetches message bodies only for your selected custom label and date range. Tokens are encrypted on this server. Imported email content is stored in your account for review; no AI service receives it.</p><button className="btn btn-primary" disabled={busy || !status.configured} onClick={() => void act(async () => {const result = await emailService.connect(); const url = new URL(result.authorization_url); if (url.origin !== 'https://accounts.google.com') throw new Error('Unexpected authorization destination'); window.location.assign(url.toString()); return 'Opening Google…';}, false)}>{status.status === 'reconnect_required' ? 'Reconnect Gmail' : 'Connect Gmail'}</button></>}
            {status.status === 'connected' && <>
                {labelError ? <p role="alert" className="notice error">{labelError} Use Refresh connection to retry loading labels.</p> : <Selection key={`${status.label_id}-${status.import_since}-${status.auto_sync}`} status={status} labels={labels} busy={busy} save={value => void act(async () => {await emailService.select(value); return 'Import settings saved.';})}/>}
                <div className="gmail-sync-actions"><button className="btn btn-primary" disabled={busy || !status.configured || !status.label_id} onClick={() => void act(async () => {const run = await emailService.sync(); if (run.status === 'failed') throw new Error(run.error || 'Sync failed.'); setOffset(0); return `Batch complete: ${run.imported} emails processed, ${run.needs_review} need attention, ${run.skipped} already seen or no longer selected.`;})}>{busy ? 'Working…' : status.has_more ? 'Continue sync' : 'Sync now'}</button><Link className="text-link" to="/jobs/discovered">Open discovered jobs →</Link></div>
                <p className="form-note">Last successful batch: {dateTime(status.last_sync_at)}. {status.has_more ? 'More emails remain in this scan.' : 'No continuation page pending.'}</p>
                {status.auto_sync && <p className="form-note">Next automatic check due: {dateTime(status.next_sync_at)}. Refresh to see worker progress.</p>}
            </>}
            {status.status !== 'disconnected' && <div className="gmail-disconnect">{confirmDisconnect ? <div className="notice"><p>Disconnect Gmail and stop automatic syncing? Imported drafts and saved jobs will remain in JobPilot.</p><div className="button-row"><button className="btn btn-secondary" disabled={busy} onClick={() => setConfirmDisconnect(false)}>Keep connected</button><button className="btn btn-secondary" disabled={busy} onClick={() => void act(async () => {const result = await emailService.disconnect(); setConfirmDisconnect(false); return result.revoked ? 'Gmail disconnected. Imported records were kept.' : 'Disconnected locally. Remove JobPilot in Google Account permissions to finish revoking access.';})}>Confirm disconnect</button></div></div> : <button className="text-link" disabled={busy} onClick={() => setConfirmDisconnect(true)}>Disconnect Gmail</button>}</div>}
        </>}
        {!!messages?.total && <div className="section-block"><h3>Imported emails</h3><Link className="btn btn-primary" to="/jobs/discovered">Review discovered jobs →</Link><p className="form-note">Includes previously connected mailboxes. Review new openings in Discovered jobs. Existing drafts remain available.</p>{messages.items.map(item => <article className="gmail-message" key={item.id}><strong>{item.subject || '(No subject)'}</strong><p className="form-note">{item.sender} · {dateTime(item.received_at)}</p>{item.gmail_url && <a className="text-link" href={item.gmail_url} target="_blank" rel="noopener noreferrer">Open original email in Gmail ↗</a>}{item.warning && <p className="notice">{item.warning}</p>}{!!item.openings?.length && <div className="email-openings">{item.openings.map((opening, index) => <div className="email-opening" key={opening.job_url}><h4>{opening.title || `Opening ${index+1}`}</h4><div className="button-row"><a className="btn btn-secondary" href={opening.job_url} target="_blank" rel="noopener noreferrer">Open job ↗</a><Link className="text-link" to={`/jobs/capture?url=${encodeURIComponent(opening.job_url)}&title=${encodeURIComponent(opening.title || '')}`}>Paste description</Link></div><p className="form-note">Open the job, then use the extension on permitted sites or paste its full description. This opening is collected in Discovered jobs for your approval. No editable draft is created automatically.</p></div>)}</div>}{!item.openings?.length && (item.import_id ? <Link className="text-link" to={`/jobs/imports/${item.import_id}/review`}>Open extraction →</Link> : <Link className="text-link" to="/jobs/import">Paste this job manually →</Link>)}</article>)}{(messages.total > 20 || offset > 0) && <div className="job-pagination"><button className="text-link" disabled={!offset || busy} onClick={() => setOffset(value => Math.max(0,value-20))}>Previous emails</button><button className="text-link" disabled={offset+20 >= messages.total || busy} onClick={() => setOffset(value => value+20)}>Next emails</button></div>}</div>}
        {!!runs.length && <details className="section-block"><summary>Recent sync activity</summary>{runs.map(run => <div className="gmail-message" key={run.id}><strong>{run.status} · {dateTime(run.started_at)}</strong><p className="form-note">{run.imported} emails processed · {run.needs_review} need attention · {run.skipped} skipped</p>{run.error && <p>{run.error}</p>}</div>)}</details>}
    </section>;
}
