import type { JobFields, WorkMode } from '../../types/job.types';
export type JobFormValues = {
    title: string; company: string; location: string; work_mode: WorkMode | '';
    employment_type: string; description: string; skills: string; application_url: string;
    status: 'saved' | 'archived'; confirmed: boolean;
};
export const blankJob: JobFields = {title:null, company:null, location:null, work_mode:null, employment_type:null, description:null, skills:[], application_url:null};
export function jobToForm(data: JobFields, status: 'saved' | 'archived' = 'saved'): JobFormValues {
    return {title:data.title ?? '', company:data.company ?? '', location:data.location ?? '', work_mode:data.work_mode ?? '', employment_type:data.employment_type ?? '', description:data.description ?? '', skills:data.skills.join('\n'), application_url:data.application_url ?? '', status, confirmed:false};
}
export function formToJob(values: JobFormValues): JobFields {
    const nullable = (value: string) => value.trim() || null;
    return {title:nullable(values.title), company:nullable(values.company), location:nullable(values.location), work_mode:values.work_mode || null, employment_type:nullable(values.employment_type), description:nullable(values.description), skills:values.skills.split(/\r?\n/).map(value => value.trim()).filter(Boolean), application_url:nullable(values.application_url)};
}
