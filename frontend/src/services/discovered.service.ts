import api from '../api/axios';
import type {CapturePreview} from '../types/capture.types';
import type {JobDetail, JobFields, Page} from '../types/job.types';
export interface DiscoveredJob extends CapturePreview {
    id: number;
    email_message_id: number;
    gmail_url: string | null;
    source_site: 'linkedin' | 'naukri' | 'indeed' | 'other';
    job_url: string | null;
    status: 'pending' | 'dismissed' | 'approved';
    job_id: number | null;
    created_at: string;
}
export const discoverySources = {all: 'All sources', linkedin: 'LinkedIn', naukri: 'Naukri', indeed: 'Indeed', other: 'Other sources'};
export type DiscoverySource = keyof typeof discoverySources;
export const discoveredService = {
    async list(status = 'pending', offset = 0, site: DiscoverySource = 'all'): Promise<Page<DiscoveredJob>> {return (await api.get('/jobs/discovered', {params:{status, offset, ...(site === 'all' ? {} : {site})}})).data;},
    async lookup(url: string): Promise<DiscoveredJob[]> {return (await api.get('/jobs/discovered/lookup', {params:{url}})).data;},
    async get(id: number): Promise<DiscoveredJob> {return (await api.get(`/jobs/discovered/${id}`)).data;},
    async status(id: number, status: 'pending' | 'dismissed'): Promise<DiscoveredJob> {return (await api.patch(`/jobs/discovered/${id}`, {status})).data;},
    async approve(id: number, fields: JobFields): Promise<JobDetail> {return (await api.post(`/jobs/discovered/${id}/approve`, fields)).data;},
    async backfill(afterId: number): Promise<{created:number; next_cursor:number | null}> {return (await api.post('/jobs/discovered/backfill', undefined, {params:{after_id:afterId}})).data;},
};
