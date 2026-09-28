import api from '../api/axios';
import type {Job, JobDetail, JobFields, JobFilters, JobImport, ImportSummary, Page} from '../types/job.types';
export const jobService = {
    async list(params: JobFilters): Promise<Page<Job>> { return (await api.get('/jobs', {params})).data; },
    async get(id: number): Promise<JobDetail> { return (await api.get(`/jobs/${id}`)).data; },
    async create(data: JobFields, importId: number | null): Promise<JobDetail> { return (await api.post('/jobs', {...data, import_id: importId})).data; },
    async update(id: number, data: JobFields, revision: number, status: Job['status']): Promise<JobDetail> { return (await api.put(`/jobs/${id}`, {...data, expected_revision: revision, status})).data; },
    async importEmail(raw_text: string): Promise<JobImport> { return (await api.post('/jobs/imports', {raw_text})).data; },
    async getImport(id: number): Promise<JobImport> { return (await api.get(`/jobs/imports/${id}`)).data; },
    async imports(offset = 0): Promise<Page<ImportSummary>> { return (await api.get('/jobs/imports', {params:{offset, limit:10}})).data; },
};
