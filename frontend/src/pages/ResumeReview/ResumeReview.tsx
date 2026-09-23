import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Link, useBeforeUnload, useBlocker, useNavigate, useParams } from 'react-router-dom';
import { FormProvider, useForm } from 'react-hook-form';
import { resumeService } from '../../services/resume.service';
import { profileService } from '../../services/profile.service';
import { apiError } from '../../api/axios';
import type { ResumeResponse } from '../../types/resume.types';
import type { ResumeParse } from '../../types/resume-parse.types';
import type { Profile, ProfileData } from '../../types/profile.types';
import ConfirmDialog from '../../components/ui/ConfirmDialog';
import PageHeader from '../../components/ui/PageHeader';
import ProfileFields from '../../components/Profile/ProfileFields';
import { toForm, toProfile, type ProfileFormValues } from '../../components/Profile/profile-form';

type ReviewContext = { resume: ResumeResponse; parsed: ResumeParse | null; profile: Profile | null; initial: ProfileData; fromProfile: boolean };

export default function ResumeReview() {
    const { resumeId } = useParams();
    const id = Number(resumeId);
    if (!Number.isSafeInteger(id) || id <= 0) return <section className="card"><h2>Resume not found</h2><Link to="/resume">Choose a saved resume</Link></section>;
    return <ReviewLoader key={id} id={id}/>;
}

function ReviewLoader({id}: {id: number}) {
    const [context, setContext] = useState<ReviewContext | null>(null);
    const [error, setError] = useState('');
    const [attempt, setAttempt] = useState(0);
    useEffect(() => {
        let active = true;
        async function load() {
            setError(''); setContext(null);
            try {
                const [resume, parsed, profile] = await Promise.all([
                    resumeService.get(id),
                    resumeService.getParse(id).catch(error => {
                        if (axios.isAxiosError(error) && error.response?.status === 404) return null;
                        throw error;
                    }),
                    profileService.get(),
                ]);
                const fromProfile = profile?.source_resume_id === id;
                const initial = fromProfile ? profile!.data : parsed?.status === 'completed' ? parsed.draft_data : null;
                if (!initial) throw new Error('Build a completed draft on the resume page before reviewing this document.');
                if (active) setContext({resume, parsed, profile, initial, fromProfile});
            } catch (error) {
                if (active) setError(axios.isAxiosError(error) ? apiError(error) : error instanceof Error ? error.message : 'Could not open this review.');
            }
        }
        void load();
        return () => { active = false; };
    }, [id, attempt]);
    if (error) return <section className="card"><h2>Review unavailable</h2><p role="alert" className="notice error">{error}</p><div className="button-row"><button className="btn btn-secondary" onClick={() => setAttempt(value => value + 1)}>Retry</button><Link to={`/resume?id=${id}`} className="text-link">Back to resume</Link></div></section>;
    if (!context) return <p role="status" className="form-note">Opening your resume review…</p>;
    return <ReviewEditor context={context}/>;
}

function ReviewEditor({context}: {context: ReviewContext}) {
    const {resume, parsed, profile, initial, fromProfile} = context;
    const methods = useForm<ProfileFormValues>({defaultValues: toForm(initial)});
    const {isDirty, isSubmitting} = methods.formState;
    const saved = useRef(false);
    const navigate = useNavigate();
    const [error, setError] = useState('');
    const [conflict, setConflict] = useState(false);
    const [reloading, setReloading] = useState(false);
    const [confirmReload, setConfirmReload] = useState(false);
    const [revision, setRevision] = useState(profile?.revision ?? 0);
    const blocker = useBlocker(({currentLocation, nextLocation}) => !saved.current && (isDirty || isSubmitting) && currentLocation.pathname + currentLocation.search !== nextLocation.pathname + nextLocation.search);
    useBeforeUnload(event => {
        if (!saved.current && (isDirty || isSubmitting)) { event.preventDefault(); event.returnValue = ''; }
    });
    async function save(values: ProfileFormValues) {
        setError(''); setConflict(false);
        try {
            await profileService.save({source_resume_id: resume.id, expected_revision: revision, data: toProfile(values)});
            saved.current = true;
            methods.reset(values);
            navigate('/profile');
        } catch (error) {
            setError(apiError(error));
            setConflict(axios.isAxiosError(error) && error.response?.status === 409);
        }
    }
    async function reloadProfile() {
        setConfirmReload(false);
        setReloading(true);
        try {
            const latest = await profileService.get();
            // If another document is now the source, return to the profile rather than
            // silently relabeling its confirmed details as this document's extraction.
            if (latest && latest.source_resume_id !== resume.id) {
                saved.current = true; navigate('/profile'); return;
            }
            methods.reset(toForm(latest?.data ?? initial));
            setRevision(latest?.revision ?? 0); setError(''); setConflict(false);
        } catch (error) { setError(apiError(error)); }
        finally { setReloading(false); }
    }
    return <>
        <PageHeader eyebrow="MAKE IT YOURS" title="Review your experience." description="Check the extracted details, fill in what is missing, and save a profile you can trust." action={<Link className="text-link" to={`/resume?id=${resume.id}`}>Back to resume</Link>}/>
        <div className="review-intro" id="review-form-top"><span className="pill teal">{fromProfile ? 'Editing confirmed profile' : 'Reviewing parsed draft'}</span><span className="muted small">{resume.file_name}</span><a className="text-link" href="#review-source">Compare original text</a></div>
        {fromProfile && <p className="notice success">Your saved corrections are loaded. Rebuilding the parsed draft never replaces them.</p>}
        {profile && !fromProfile && <p className="notice warning">You already have a confirmed profile. Saving this resume will replace its details with the reviewed information below.</p>}
        <div className="review-layout">
            <FormProvider {...methods}><form className="card review-form" onSubmit={event => { void methods.handleSubmit(save)(event); }}>
                <fieldset disabled={isSubmitting || reloading} className="review-form-fields">
                    <ProfileFields/>
                    <div className="review-save">
                        <label className="review-confirm"><input type="checkbox" {...methods.register('confirmed', {required: 'Confirm that you reviewed these details before saving.'})}/><span>I have reviewed these details and want to save them as my confirmed profile.</span></label>
                        {methods.formState.errors.confirmed && <p role="alert" className="notice error">{methods.formState.errors.confirmed.message}</p>}
                        {error && <div role="alert" className="notice error">{error}</div>}
                        {conflict && <button type="button" className="text-link" onClick={() => setConfirmReload(true)}>Discard edits and load latest profile</button>}
                        <div className="button-row"><button className="btn btn-primary" type="submit">{isSubmitting ? 'Saving profile…' : 'Save confirmed profile'}</button><Link className="text-link" to="/profile">Cancel</Link></div>
                        <p className="form-note">Changes are saved only when you confirm. Your original PDF and parsed draft stay unchanged.</p>
                    </div>
                </fieldset>
            </form></FormProvider>
            <aside className="review-evidence">
                <section className="card"><span className="eyebrow">YOUR REFERENCE</span><h2 id="review-source">Original extracted text</h2><p className="form-note">Compare each field with the source. Nothing here is changed by your edits.</p><pre className="review-source">{resume.raw_text ?? 'No extracted text available.'}</pre><a className="text-link" href="#review-form-top">Back to review fields</a></section>
                {parsed && parsed.warnings.length > 0 && <section className="draft-warnings"><h3>Parser notes</h3><p className="form-note">These describe the parsed draft and remain here after you correct a field.</p><ul>{parsed.warnings.map((warning, index) => <li key={index}>{warning.message}</li>)}</ul></section>}
                <section className="subtle-card"><h3>Keep it accurate.</h3><p>Leave unknown fields empty. You can add or remove entries and keep dates in their original wording. Links need a complete web address.</p></section>
            </aside>
        </div>
        {blocker.state === 'blocked' && <ConfirmDialog title={isSubmitting ? 'Your profile is being saved' : 'Leave without saving?'} description={isSubmitting ? 'Wait for the save to finish before leaving this page.' : 'Your changes on this page have not been saved.'} onCancel={() => blocker.reset()} onConfirm={isSubmitting ? undefined : () => blocker.proceed()} confirmLabel="Discard changes and leave"/>}
        {confirmReload && <ConfirmDialog title="Load the latest profile?" description="This discards your unsaved changes and loads the latest confirmed details." onCancel={() => setConfirmReload(false)} onConfirm={() => { void reloadProfile(); }} confirmLabel="Discard edits and reload"/>}
    </>;
}
