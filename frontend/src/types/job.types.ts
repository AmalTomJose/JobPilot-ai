export type WorkMode = 'remote' | 'hybrid' | 'onsite';
export type JobFields = {
    title: string | null; company: string | null; location: string | null;
    work_mode: WorkMode | null; employment_type: string | null;
    description: string | null; skills: string[]; application_url: string | null;
};
export type DuplicateJob = {id: number; title: string; company: string | null; reason: string};
export type JobImport = {
    id: number; raw_text: string; draft_data: JobFields;
    warnings: {code: string; field: string; message: string}[];
    parser_version: string; created_at: string; duplicate: DuplicateJob | null;
};
export type Job = JobFields & {
    id: number; title: string; source_import_id: number | null; source_type: 'manual' | 'email';
    status: 'saved' | 'archived'; revision: number; created_at: string; updated_at: string;
};
export type JobDetail = Job & {source: JobImport | null};
export type Page<T> = {items: T[]; total: number; limit: number; offset: number};
export type ImportSummary = {id: number; title: string | null; company: string | null; created_at: string};
export type JobFilters = {q?: string; status?: 'saved' | 'archived'; source?: 'manual' | 'email'; work_mode?: WorkMode; limit?: number; offset?: number};
