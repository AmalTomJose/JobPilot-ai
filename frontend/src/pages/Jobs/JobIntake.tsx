import {useRef, useState} from 'react';
import {Link, useBeforeUnload, useBlocker, useNavigate} from 'react-router-dom';
import {jobService} from '../../services/job.service';
import {apiError} from '../../api/axios';
import PageHeader from '../../components/ui/PageHeader';
import ConfirmDialog from '../../components/ui/ConfirmDialog';

export default function JobIntake() {
    const [text, setText] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const complete = useRef(false);
    const navigate = useNavigate();
    const blocker = useBlocker(({currentLocation,nextLocation}) => !complete.current && !!text && currentLocation.pathname !== nextLocation.pathname);
    useBeforeUnload(event => {if (!complete.current && text) {event.preventDefault(); event.returnValue='';}});
    async function extract(event: React.FormEvent) {
        event.preventDefault(); setSaving(true); setError('');
        try {const result = await jobService.importEmail(text); complete.current=true; navigate(`/jobs/imports/${result.id}/review`);}
        catch(error) {setError(apiError(error));}
        finally {setSaving(false);}
    }
    return <>
        <PageHeader eyebrow="FROM EMAIL TO OPPORTUNITY" title="Bring in a job email." description="Paste the text of one opening. We’ll keep the original and prepare an editable draft." action={<Link className="text-link" to="/jobs">Back to jobs</Link>}/>
        <div className="content-with-aside"><form className="card review-form" onSubmit={extract}><div className="field"><label htmlFor="email-text">Job email text</label><textarea className="email-input" id="email-text" rows={17} maxLength={100000} value={text} onChange={event=>setText(event.target.value)} disabled={saving} placeholder={'Job title: Backend Developer\nCompany: Example Labs\nLocation: Bengaluru\nWork mode: Hybrid\nSkills: Python, SQL\nApply: https://example.com/jobs/123\nDescription:\nBuild APIs and work with the engineering team.'}/><p className="form-note">Up to 100,000 characters. Text is saved only to your JobPilot account on this server.</p></div>{error && <p role="alert" className="notice error">{error}</p>}<button className="btn btn-primary" disabled={saving || !text.trim()} type="submit">{saving ? 'Extracting…' : 'Extract & review'}</button></form>
        <aside className="subtle-card"><h3>One opening at a time.</h3><p>Paste the email content, including its job heading and application link. Common headings, labeled fields, and multiline sections are supported. Check every extracted value before saving.</p><p>To refresh an older unsaved import, paste the same text and extract again. Saved jobs keep their original extraction. Mailbox connection and automatic syncing will come later. No links are fetched and no AI service receives this text.</p></aside></div>
        {blocker.state==='blocked' && <ConfirmDialog title={saving ? 'Extracting the email' : 'Leave this email?'} description={saving ? 'Wait for extraction to finish.' : 'The pasted text has not been saved yet.'} onCancel={()=>blocker.reset()} onConfirm={saving ? undefined : ()=>blocker.proceed()} confirmLabel="Discard and leave"/>}
    </>;
}
