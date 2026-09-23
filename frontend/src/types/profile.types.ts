import type { ResumeDraft } from './resume-parse.types';

export type ProfileData = {
    contact: ResumeDraft['contact'];
    summary: string | null;
    skills: string[];
    experience: Omit<ResumeDraft['experience'][number], 'source_text'>[];
    education: Omit<ResumeDraft['education'][number], 'source_text'>[];
    projects: Omit<ResumeDraft['projects'][number], 'source_text'>[];
};
export type Profile = {
    id: number;
    source_resume_id: number | null;
    source_parser_version: string;
    revision: number;
    data: ProfileData;
    created_at: string;
    updated_at: string;
};
export type ProfileSave = { source_resume_id: number | null; expected_revision: number; data: ProfileData };
