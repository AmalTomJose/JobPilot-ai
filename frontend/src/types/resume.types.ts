export type ResumeResponse = {
    id: number;
    file_name: string;
    file_type: string;
    file_size: number;
    raw_text: string | null;
    created_at: string;
};
