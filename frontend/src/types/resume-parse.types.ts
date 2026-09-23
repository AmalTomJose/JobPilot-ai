export type ResumeSummary = {
    id: number;
    file_name: string;
    file_type: string;
    file_size: number;
    created_at: string;
};
export type ExperienceDraft = {
    title: string | null;
    company: string | null;
    location: string | null;
    date_text: string | null;
    description: string[];
    source_text: string;
};
export type EducationDraft = {
    institution: string | null;
    degree: string | null;
    field_of_study: string | null;
    date_text: string | null;
    source_text: string;
};
export type ProjectDraft = {
    name: string | null;
    description: string[];
    technologies: string[];
    links: string[];
    source_text: string;
};
export type ResumeDraft = {
    contact: {
        name: string | null;
        email: string | null;
        phone: string | null;
        location: string | null;
        links: string[];
    };
    summary: string | null;
    skills: string[];
    experience: ExperienceDraft[];
    education: EducationDraft[];
    projects: ProjectDraft[];
    unclassified_text: string | null;
};
export type ResumeParse = {
    id: number;
    resume_id: number;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    parser_version: string;
    draft_data: ResumeDraft | null;
    warnings: {code: string; section: string; message: string}[];
    error_message: string | null;
    created_at: string;
    completed_at: string | null;
};
