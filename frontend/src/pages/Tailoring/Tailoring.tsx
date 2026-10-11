import {useEffect, useRef, useState} from 'react';
import {Link, useParams, useSearchParams} from 'react-router-dom';
import {FormProvider, useForm} from 'react-hook-form';
import {tailoringService, type ResumeVersion, type VersionList, type Section} from '../../services/tailoring.service';
import {apiError} from '../../api/axios';
import ProfileFields from '../../components/Profile/ProfileFields';
import ProfileDetails from '../../components/Profile/ProfileDetails';
import {toForm, toProfile, type ProfileFormValues} from '../../components/Profile/profile-form';
import PageHeader from '../../components/ui/PageHeader';

export default function Tailoring() {
    const {jobId} = useParams();
    return <Workspace key={jobId} jobId={Number(jobId)}/>;
}
function Workspace({jobId}:{jobId:number}) {
    const [params,setParams] = useSearchParams();
    const selected = Number(params.get('version')) || null;
    const [list,setList] = useState<VersionList|null>(null);
    const [version,setVersion] = useState<ResumeVersion|null>(null);
    const [error,setError] = useState('');
    const [busy,setBusy] = useState(false);
    const [loading,setLoading] = useState(true);
    const [consent,setConsent] = useState(false);
    const [offset,setOffset] = useState(0);
    const [refresh,setRefresh] = useState(0);
    const requestId = useRef<string|null>(null);
    useEffect(() => {
        let active = true;
        async function load() {
        setLoading(true); setError(''); setVersion(null);
        await Promise.all([tailoringService.list(jobId,offset),selected ? tailoringService.get(jobId,selected) : Promise.resolve(null)])
            .then(([page,item]) => {if(active) {setList(page);setVersion(item);}})
            .catch(error => {if(active) setError(apiError(error));})
            .finally(() => {if(active) setLoading(false);});
        }
        void load();
        return () => {active = false;};
    },[jobId,selected,offset,refresh]);
    async function generate() {
        if(!list?.profile_revision || !consent) return;
        setBusy(true);setError('');
        requestId.current ??= crypto.randomUUID();
        try {
            const result = await tailoringService.generate(jobId,requestId.current,list.profile_revision,list.job_revision);
            requestId.current = null;
            setParams({version:String(result.id)});setRefresh(value=>value+1);
        } catch(error) {
            // Keep the ID for network retries: the server may already have created the version.
            setError(apiError(error));
        } finally {setBusy(false);}
    }
    function startNew() {requestId.current=null;setParams({});setRefresh(value=>value+1);}
    return <div className="tailoring-workspace">
        <PageHeader eyebrow="TAILORED TO THE OPPORTUNITY" title="Your experience. A relevant resume." description="Choose a draft, check the evidence, and make it yours before exporting." action={<Link className="btn btn-secondary" to={`/jobs/${jobId}`}>Back to saved job</Link>}/>
        <section className="card tailoring-start">
            <div><h2>Create a tailored version</h2><p>AI can select relevant experience and suggest clearer wording. Your main profile stays unchanged.</p></div>
            {list && !list.configured && <p className="notice">AI setup is needed: configure OPENAI_API_KEY and OPENAI_MODEL on the backend, then restart it. Existing versions remain available.</p>}
            {list && !list.profile_revision && <p className="notice">First <Link to="/profile">review and save your profile</Link>.</p>}
            {list && !list.has_description && <p className="notice">Add the full description in <Link to={`/jobs/${jobId}/edit`}>Edit job</Link> before generating.</p>}
            <label className="tailoring-check"><input type="checkbox" checked={consent} disabled={busy} onChange={event=>setConsent(event.target.checked)}/> Send my reviewed experience and this job description to OpenAI to create a draft. Contact fields and project links are excluded from the AI request.</label>
            <div className="button-row"><button className="btn btn-primary" disabled={busy||loading||!consent||!list?.configured||!list.profile_revision||!list.has_description} onClick={()=>void generate()}>{busy?'Creating your draft…':'Generate with AI'}</button><button className="btn btn-secondary" disabled={busy} onClick={()=>setRefresh(value=>value+1)}>Refresh versions</button>{error && <button className="text-link" disabled={busy} onClick={startNew}>Start a new request</button>}</div>
            <p className="form-note">Generation creates a separate draft version. It does not approve a resume or submit an application. Check every claim; AI can make mistakes.</p>
        </section>
        {error && <p className="notice error" role="alert">{error}</p>}
        <section className="section-block tailoring-versions" aria-label="Resume versions"><h2>Resume versions</h2><div className="button-row">{list?.items.map(item=><button disabled={busy} aria-pressed={selected===item.id} className={`btn ${selected===item.id?'btn-primary':'btn-secondary'}`} key={item.id} onClick={()=>setParams({version:String(item.id)})}>Version #{item.id} · {item.status}</button>)}</div>{list && !list.total && <p>No versions yet. Generate your first draft above.</p>}{list && list.total>10 && <div className="button-row"><button className="text-link" disabled={offset===0||busy} onClick={()=>setOffset(Math.max(0,offset-10))}>Newer versions</button><button className="text-link" disabled={offset+10>=list.total||busy} onClick={()=>setOffset(offset+10)}>Older versions</button></div>}</section>
        {!loading && version && ['draft','failed'].includes(version.status) && <DiscardVersion key={`${version.id}-${version.revision}`} version={version} onDiscarded={()=>{requestId.current=null;setVersion(null);setOffset(0);setParams({});setRefresh(value=>value+1);}}/>}
        {loading ? <p role="status">Loading resume workspace…</p> : version?.status==='generating' ? <p className="notice">This version is generating. Refresh shortly. If it remains here after a few minutes, generation may have been interrupted; start a new request.</p> : version?.status==='failed' ? <section className="card"><p role="alert">{version.error}</p><button className="btn btn-secondary" onClick={startNew}>Start a new request</button></section> : version?.data && <Review key={`${version.id}-${version.revision}`} version={version} onSaved={value=>{setVersion(value);setList(old=>old?{...old,items:old.items.map(item=>item.id===value.id?{...item,status:value.status}:item)}:old);}}/>}
    </div>;
}
function Review({version,onSaved}:{version:ResumeVersion;onSaved:(value:ResumeVersion)=>void}) {
    const form = useForm<ProfileFormValues>({defaultValues:toForm(version.data!)});
    const [order,setOrder] = useState<Section[]>(version.section_order);
    const [busy,setBusy] = useState(false);
    const [error,setError] = useState('');
    const [notice,setNotice] = useState('');
    const [showPdf,setShowPdf] = useState(false);
    const [pdfUrl,setPdfUrl] = useState<string|null>(null);
    useEffect(()=>()=>{if(pdfUrl) URL.revokeObjectURL(pdfUrl);},[pdfUrl]);
    const [preview,setPreview] = useState(false);
    const dirty = form.formState.isDirty || order.join()!==version.section_order.join();
    async function save(approve:boolean) {
        await form.handleSubmit(async values=>{
            if(approve&&!values.confirmed) {setError('Confirm that you reviewed the facts before approving.');return;}
            setBusy(true);setError('');setNotice('');
            try {const result=await tailoringService.save(version.job_id,version.id,version.revision,toProfile(values),order,approve);onSaved(result);}
            catch(error) {setError(apiError(error));}
            finally {setBusy(false);}
        })();
    }
    async function download(viewOnly=false) {
        setBusy(true);setError('');
        try {
            const blob=await tailoringService.pdf(version.job_id,version.id);
            const url=URL.createObjectURL(blob);setPdfUrl(url);
            if(viewOnly) {setShowPdf(true);return;}
            const anchor=document.createElement('a');anchor.href=url;anchor.download=(version.pdf_filename || `resume-job-${version.job_id}-version-${version.id}.pdf`);document.body.appendChild(anchor);anchor.click();anchor.remove();
            setNotice('Your approved PDF is ready. If the download did not start, use Save approved PDF below.');
        } catch {setError('Could not load this PDF. Refresh to check whether the source profile or job changed.');}
        finally {setBusy(false);}
    }
    function move(index:number,direction:number) {const next=[...order];[next[index],next[index+direction]]=[next[index+direction],next[index]];setOrder(next);form.setValue('confirmed',false);}
    return <>
        <section className="card section-block"><div className="section-heading"><div><span className="eyebrow">VERSION #{version.id} · {version.status.toUpperCase()}</span><h2>{version.job_snapshot.title}</h2><p>{version.job_snapshot.company}</p></div>{version.status==='approved' && <div className="button-row"><button className="btn btn-secondary" disabled={busy||dirty||version.stale} onClick={()=>void download(true)}>View PDF</button><button className="btn btn-primary" disabled={busy||dirty||version.stale} onClick={()=>void download()}>Download approved PDF</button></div>}</div>
            {version.stale && <p className="notice">Your profile or job changed after this version was generated. You can keep editing this draft, but generate a new version before approval or export.</p>}
            {version.saved_pdf && <p className="notice" role="status">Approved PDF saved in your approved resumes folder: <strong>{version.saved_pdf}</strong></p>}
            <p className="form-note">Profile revision {version.profile_revision} · Job revision {version.job_revision} · Model: {version.model}</p>
            {version.proposal && <div className="tailoring-evidence"><div><h3>Suggested changes</h3><ul>{version.proposal.changes.map((change,i)=><li key={i}>{change}</li>)}</ul></div><div><h3>Questions to resolve</h3>{version.proposal.questions.length?<ul>{version.proposal.questions.map((question,i)=><li key={i}>{question}</li>)}</ul>:<p>No questions suggested. Still check every claim.</p>}<p className="form-note">Add confirmed missing experience to your main profile, then generate a new version.</p></div></div>}
            <details className="draft-source"><summary>Compare with the original reviewed profile</summary><ProfileDetails data={version.profile_snapshot}/></details>
            <details className="draft-source"><summary>Job description used for this version</summary><pre>{version.job_snapshot.description}</pre></details>
            {version.proposal && <details className="draft-source"><summary>Evidence for the original AI suggestions</summary><p>These references describe the AI proposal. Your manual edits below may differ.</p>{[...(version.proposal.summary?[version.proposal.summary]:[]),...version.proposal.experience.flatMap(entry=>entry.bullets),...version.proposal.projects.flatMap(entry=>entry.bullets)].map((statement,index)=><div className="draft-entry" key={index}><p>{statement.text}</p><ul>{statement.evidence.map(key=><li key={key}><strong>{key}</strong>: {sourceValue(version.profile_snapshot,key)}</li>)}</ul></div>)}</details>}
        </section>
        {showPdf && pdfUrl && !dirty && !version.stale && version.status==='approved' && <section className="card section-block" aria-label="Approved PDF preview">
            <div className="section-heading"><h2>Approved PDF</h2><button type="button" className="btn btn-secondary" onClick={()=>setShowPdf(false)}>Close PDF</button></div>
            <p className="form-note">This is the PDF for your approved resume. If your browser cannot display it, <a href={pdfUrl} target="_blank" rel="noopener noreferrer">open the PDF in a new tab</a> or download it.</p>
            <iframe className="tailoring-pdf-preview" src={pdfUrl} title="Approved resume PDF" />
        </section>}
        <FormProvider {...form}><form className="card section-block" onSubmit={event=>{event.preventDefault();void save(false);}} onChange={event=>{if(!(event.target instanceof HTMLInputElement && event.target.name==='confirmed')) form.setValue('confirmed',false);}}>
            <div className="section-heading"><h2>{preview?'Content preview':'Review and edit your resume'}</h2><button type="button" className="btn btn-secondary" onClick={()=>setPreview(!preview)}>{preview?'Return to editing':'Preview content'}</button></div>
            {error && <p className="notice error" role="alert">{error}</p>}{notice && <p className="notice" role="status">{notice}</p>}{pdfUrl && !dirty && <a className="btn btn-secondary" href={pdfUrl} download={(version.pdf_filename || `resume-job-${version.job_id}-version-${version.id}.pdf`)}>Save approved PDF</a>}
            <fieldset disabled={busy} className="review-form-fields">
                <p className="form-note">Edits affect only this resume version. Saving edits returns an approved version to draft until you approve it again.</p>
                {preview?<ProfileDetails data={toProfile(form.getValues())}/>:<ProfileFields/>}
                <section className="review-section"><h3>PDF section order</h3><p className="form-note">Contact details stay at the top. Empty sections are omitted. PDFs must fit one readable A4 page; shorten the summary or bullets if approval reports that the content is too long.</p><ol className="tailoring-order">{order.map((section,index)=><li key={section}><span>{section}</span><button type="button" className="text-link" aria-label={`Move ${section} up`} disabled={index===0} onClick={()=>move(index,-1)}>↑</button><button type="button" className="text-link" aria-label={`Move ${section} down`} disabled={index===order.length-1} onClick={()=>move(index,1)}>↓</button></li>)}</ol></section>
                <label className="tailoring-check"><input type="checkbox" {...form.register('confirmed')}/> I reviewed this resume and confirm that its experience, skills, dates, and claims are accurate.</label>
                <div className="button-row"><button className="btn btn-secondary" type="submit">Save draft edits</button><button className="btn btn-primary" type="button" disabled={version.stale} onClick={()=>void save(true)}>Approve resume</button></div>
            </fieldset>
        </form></FormProvider>
    </>;
}
function sourceValue(source:unknown,path:string):string {
    let value:unknown=source;
    for(const key of path.split('.')) {if(!value||typeof value!=='object')return 'Source unavailable';value=(value as Record<string,unknown>)[key];}
    return typeof value==='string'?value:'Source unavailable';
}


function DiscardVersion({version,onDiscarded}:{version:ResumeVersion;onDiscarded:()=>void}) {
    const [confirming,setConfirming]=useState(false);
    const [busy,setBusy]=useState(false);
    const [error,setError]=useState('');
    async function discard() {
        setBusy(true);setError('');
        try {await tailoringService.discard(version.job_id,version.id,version.revision);onDiscarded();}
        catch(error) {setError(apiError(error));}
        finally {setBusy(false);}
    }
    return <section className="card section-block" aria-label="Discard resume draft">
        {error && <p className="notice error" role="alert">{error}</p>}
        {confirming ? <><p>Discard version #{version.id}? This permanently removes this draft and its stored AI suggestions. Unsaved edits will also be lost. Your main profile and saved job stay unchanged.</p><div className="button-row"><button className="btn btn-secondary" disabled={busy} onClick={()=>void discard()}>{busy?'Discarding…':'Yes, discard draft'}</button><button className="text-link" disabled={busy} onClick={()=>setConfirming(false)}>Keep draft</button></div></> : <><p>Don’t want to keep this version? Remove it from your resume versions.</p><button className="btn btn-secondary" onClick={()=>setConfirming(true)}>Discard draft</button></>}
    </section>;
}
