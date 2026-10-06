import api from '../api/axios';
import type {CaptureInput, CapturePreview} from '../types/capture.types';
import type {JobFields, JobDetail, JobImport} from '../types/job.types';

export const captureService = {
    async preview(capture: CaptureInput): Promise<CapturePreview> {
        return (await api.post('/jobs/capture/preview', capture)).data;
    },
    async save(data: JobFields): Promise<JobDetail> {
        return (await api.post('/jobs/capture/save', data)).data;
    },
    async saveDraft(capture: CaptureInput, draft_data: JobFields): Promise<JobImport> {
        return (await api.post('/jobs/capture/drafts', {capture, draft_data})).data;
    },
};
