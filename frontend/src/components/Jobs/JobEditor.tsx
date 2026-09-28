import {useRef, useState} from 'react';
import {useForm} from 'react-hook-form';
import {Link, useBeforeUnload, useBlocker, useNavigate} from 'react-router-dom';
import axios from 'axios';
import {apiError} from '../../api/axios';
import {jobService} from '../../services/job.service';
import type {JobDetail, JobImport, DuplicateJob} from '../../types/job.types';
import {blankJob, formToJob, jobToForm, type JobFormValues} from './job-form';
import ConfirmDialog from '../ui/ConfirmDialog';
import PageHeader from '../ui/PageHeader';

export default function JobEditor({source = null, job = null}: {source?: JobImport | null; job?: JobDetail | null}) {
    const form = useForm<JobFormValues>({defaultValues:jobToForm(job ?? source?.draft_data ?? blankJob, job?.status)});
    const {register, formState:{isDirty, isSubmitting, errors}} = form;
    const saved = useRef(false);
    const navigate = useNavigate();
    const [error, setError] = useState('');
    const [duplicate, setDuplicate] = useState<DuplicateJob | null>(source?.duplicate ?? null);
    const blocker = useBlocker(({currentLocation,nextLocation}) => !saved.current && (isDirty || isSubmitting) && currentLocation.pathname !== nextLocation.pathname);
    useBeforeUnload(event => { if (!saved.current && (isDirty || isSubmitting)) {event.preventDefault(); event.returnValue='';} });
    async function save(values: JobFormValues) {
        setError(''); setDuplicate(null);
        try {
            const result = job ? await jobService.update(job.id, formToJob(values), job.revision, values.status) : await jobService.create(formToJob(values), source?.id ?? null);
            saved.current = true; form.reset(values); navigate(`/jobs/${result.id}`);
        } catch (error) {
            setError(apiError(error));
            if (axios.isAxiosError(error)) setDuplicate(error.response?.data?.details?.duplicate ?? null);
        }
    }
    return <>
        <PageHeader eyebrow="BUILD YOUR JOB INBOX" title={job ? 'Edit saved job' : source ? 'Review this opportunity.' : 'Add a job.'} description="Keep the details that matter. Unknown fields can stay empty; a job title is required." action={<Link className="text-link" to="/jobs">Back to jobs</Link>}/>
        <div className="review-intro"><span className="pill teal">{source ? 'From pasted email' : 'Manual entry'}</span>{source && <a className="text-link" href="#job-source">Compare original email</a>}</div>
        {duplicate && <div className="notice warning" role="status"><strong>Already in your inbox</strong><p>{duplicate.reason}</p><Link className="text-link" to={`/jobs/${duplicate.id}`}>Open {duplicate.title}</Link></div>}
        <div className={source ? 'review-layout' : 'job-editor-single'}>
            <form className="card review-form" onSubmit={event=>{void form.handleSubmit(save)(event);}}>
                <fieldset className="review-form-fields" disabled={isSubmitting}>
                    <h2>Job details</h2><div className="review-fields">
                        <div className="field"><label htmlFor="job-title">Job title *</label><input id="job-title" maxLength={255} {...register('title',{validate:value=>!!value.trim() || 'Enter a job title.'})} aria-invalid={!!errors.title}/>{errors.title && <p role="alert" className="form-note">{errors.title.message}</p>}</div>
                        <div className="field"><label htmlFor="job-company">Company</label><input id="job-company" maxLength={255} {...register('company')}/></div>
                        <div className="field"><label htmlFor="job-location">Location</label><input id="job-location" maxLength={255} {...register('location')}/></div>
                        <div className="field"><label htmlFor="job-mode">Work arrangement</label><select id="job-mode" {...register('work_mode')}><option value="">Not identified</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">On-site</option></select></div>
                        <div className="field"><label htmlFor="job-type">Employment type</label><input id="job-type" maxLength={255} placeholder="e.g. Full-time" {...register('employment_type')}/></div>
                        <div className="field"><label htmlFor="job-url">Application URL</label><input id="job-url" type="url" maxLength={2048} placeholder="https://…" {...register('application_url')}/></div>
                        <div className="field review-wide"><label htmlFor="job-description">Job description</label><textarea id="job-description" rows={9} maxLength={20000} {...register('description')}/></div>
                        <div className="field review-wide"><label htmlFor="job-skills">Required skills</label><textarea id="job-skills" rows={4} maxLength={25500} aria-describedby="job-skills-hint" {...register('skills')}/><p id="job-skills-hint" className="form-note">One skill per line, copied from the job requirements.</p></div>
                        {job && <div className="field"><label htmlFor="job-status">Inbox status</label><select id="job-status" {...register('status')}><option value="saved">Saved</option><option value="archived">Archived</option></select></div>}
                    </div>
                    <div className="review-save"><label className="review-confirm"><input type="checkbox" {...register('confirmed',{required:'Review the details and confirm before saving.'})}/><span>I have reviewed these details and want to save this job.</span></label>
                        {errors.confirmed && <p role="alert" className="notice error">{errors.confirmed.message}</p>}
                        {error && <p role="alert" className="notice error">{error}</p>}
                        <div className="button-row"><button className="btn btn-primary" type="submit">{isSubmitting ? 'Saving…' : job ? 'Save changes' : 'Save job'}</button><Link className="text-link" to={job ? `/jobs/${job.id}` : '/jobs'}>Cancel</Link></div>
                        <p className="form-note">Saving keeps this opportunity in your inbox. It does not submit an application.</p>
                    </div>
                </fieldset>
            </form>
            {source && <aside className="review-evidence"><section className="card"><span className="eyebrow">YOUR REFERENCE</span><h2 id="job-source">Original email text</h2><pre className="review-source">{source.raw_text}</pre></section><section className="draft-warnings"><h3>Extraction notes</h3><ul>{source.warnings.map((warning,index)=><li key={index}>{warning.message}</li>)}</ul></section></aside>}
        </div>
        {blocker.state==='blocked' && <ConfirmDialog title={isSubmitting ? 'Saving your job' : 'Leave without saving?'} description={isSubmitting ? 'Wait until the save finishes.' : 'Your form changes have not been saved.'} onCancel={()=>blocker.reset()} onConfirm={isSubmitting ? undefined : ()=>blocker.proceed()} confirmLabel="Discard changes and leave"/>}
    </>;
}
