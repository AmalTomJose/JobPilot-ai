import {useEffect, useState} from 'react';
import {Link, useLocation, useNavigate} from 'react-router-dom';
import {useAuth} from '../../hooks/useAuth';
import {captureService} from '../../services/capture.service';
import {receivePreview} from '../../services/extension-handoff';
import {discoveredService, type DiscoveredJob} from '../../services/discovered.service';
import {apiError} from '../../api/axios';
import type {CaptureInput, CapturePreview} from '../../types/capture.types';
import JobEditor from '../../components/Jobs/JobEditor';
import PageHeader from '../../components/ui/PageHeader';

export default function JobCapture() {
    const location = useLocation();
    const navigate = useNavigate();
    const {user} = useAuth();
    const [input, setInput] = useState<CaptureInput>(() => {
        const params = new URLSearchParams(location.search);
        return {title: (params.get('title') || '').slice(0,255), url: (params.get('url') || '').slice(0,2048), company: '', description: ''};
    });
    const requestedCandidate = Number(new URLSearchParams(location.search).get('candidate'));
    const [candidateId, setCandidateId] = useState<number | undefined>(Number.isSafeInteger(requestedCandidate) && requestedCandidate > 0 ? requestedCandidate : undefined);
    const [options, setOptions] = useState<DiscoveredJob[]>([]);
    const [optionOffset, setOptionOffset] = useState(0);
    const [optionTotal, setOptionTotal] = useState(0);
    const [optionError, setOptionError] = useState('');
    const [optionBusy, setOptionBusy] = useState(false);
    useEffect(() => {
        let active = true;
        discoveredService.list().then(page => {if(active) {setOptions(old => [...old, ...page.items.filter(item => !old.some(existing => existing.id === item.id))]); setOptionOffset(page.items.length); setOptionTotal(page.total);}}).catch(() => {if(active) setOptionError('Could not load discovered openings. Retry before linking this preview.');});
        return () => {active = false;};
    }, []);
    async function moreOptions() {
        setOptionBusy(true); setOptionError('');
        try {const page = await discoveredService.list('pending', optionOffset); setOptions(old => [...old, ...page.items.filter(item => !old.some(existing => existing.id === item.id))]); setOptionOffset(optionOffset + page.items.length); setOptionTotal(page.total);}
        catch(error) {setOptionError(apiError(error));}
        finally {setOptionBusy(false);}
    }
    const [preview, setPreview] = useState<CapturePreview | null>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    async function extract(value: CaptureInput) {
        setError(''); setBusy(true);
        try {
            if (!candidateId) {const matches = await discoveredService.lookup(value.url); const pending = matches.find(item => item.status === 'pending'); if(pending) {setCandidateId(pending.id); setOptions(old => old.some(item => item.id === pending.id) ? old : [pending, ...old]);}}
            setPreview(await captureService.preview(value));
        }
        catch (error) {setError(apiError(error));}
        finally {setBusy(false);}
    }
    async function receive() {
        setError(''); setBusy(true);
        try {
            const value = await receivePreview(location.hash);
            setInput(value);
            navigate('/jobs/capture' + location.search, {replace:true});
            // Keep received text in memory even if the extraction request fails.
            if (!candidateId) {const matches = await discoveredService.lookup(value.url); const pending = matches.find(item => item.status === 'pending'); if(pending) {setCandidateId(pending.id); setOptions(old => old.some(item => item.id === pending.id) ? old : [pending, ...old]);}}
            setPreview(await captureService.preview(value));
        } catch (error) {setError(apiError(error, error instanceof Error ? error.message : 'Could not receive preview.'));}
        finally {setBusy(false);}
    }
    const association = <section className="card section-block"><div className="field"><label htmlFor="capture-discovery">Attach to a discovered opening</label><select id="capture-discovery" value={candidateId ?? ''} onChange={event => setCandidateId(event.target.value ? Number(event.target.value) : undefined)}><option value="">Separate job / match by original URL on save</option>{candidateId && !options.some(item => item.id === candidateId) && <option value={candidateId}>Selected opening #{candidateId}</option>}{options.map(item => <option key={item.id} value={item.id}>{item.draft_data.title || 'Untitled opening'} — {item.draft_data.company || item.source_site} (#{item.id})</option>)}</select></div><p className="form-note">Choose the opening you visited if the website changed its URL. Approving will save the job and remove that opening from the pending queue.</p>{optionError && <p className="notice error" role="alert">{optionError}</p>}{(optionError || optionOffset < optionTotal) && <button type="button" className="text-link" disabled={optionBusy} onClick={() => void moreOptions()}>{optionBusy ? 'Loading…' : 'Load more openings / retry'}</button>}</section>;
    if (preview) return <><JobEditor preview={preview} capture={input} candidateId={candidateId} association={association}/></>;

    return <>
        <PageHeader eyebrow="ONE OPENING AT A TIME" title="Bring in a job description" description="Receive an extension preview or paste the full description yourself. Nothing is saved until you choose."/>
        {association}
        <section className="card capture-intake">
            <p className="notice">You are importing into {user?.email}. Only use page-reading features where the site permits them. For restricted sites, copy and paste manually.</p>
            {location.hash && <div className="section-block"><p>Your extension preview is ready to receive. It expires after ten minutes and can be received once.</p><button className="btn btn-primary" disabled={busy} onClick={() => void receive()}>{busy ? 'Receiving…' : 'Receive and extract preview'}</button></div>}
            {error && <p role="alert" className="notice error">{error}</p>}
            <form onSubmit={event => {event.preventDefault(); void extract(input);}}>
                <fieldset disabled={busy} className="review-form-fields">
                    <div className="review-fields">
                        <div className="field"><label htmlFor="capture-title">Job title, if known</label><input id="capture-title" maxLength={255} value={input.title} onChange={event => setInput({...input,title:event.target.value})}/></div>
                        <div className="field"><label htmlFor="capture-company">Company, if known</label><input id="capture-company" maxLength={255} value={input.company} onChange={event => setInput({...input,company:event.target.value})}/></div>
                        <div className="field review-wide"><label htmlFor="capture-url">Original job URL</label><input id="capture-url" type="url" required maxLength={2048} value={input.url} onChange={event => setInput({...input,url:event.target.value})}/></div>
                        <div className="field review-wide"><label htmlFor="capture-text">Full job description</label><textarea id="capture-text" rows={12} required minLength={40} maxLength={20000} value={input.description} onChange={event => setInput({...input,description:event.target.value})}/></div>
                    </div>
                    <div className="button-row"><button className="btn btn-primary" disabled={busy} type="submit">{busy ? 'Extracting…' : 'Extract temporary preview'}</button><Link className="text-link" to="/jobs">Cancel</Link></div>
                    <p className="form-note">Temporary previews are lost when you close or reload this page. No AI service receives this text.</p>
                </fieldset>
            </form>
        </section>
    </>;
}
