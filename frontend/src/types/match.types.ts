export interface MatchItem {
    job_id: number;
    title: string;
    company: string | null;
    job_status: 'saved' | 'archived';
    state: 'pending' | 'current' | 'outdated';
    score: number | null;
    matched_skills: {job_skill: string; profile_skill: string}[];
    missing_skills: string[];
    reason: string | null;
    profile_revision: number | null;
    job_revision: number | null;
    matcher_version: string | null;
    computed_at: string | null;
}
export interface MatchPage {
    items: MatchItem[];
    total: number;
    pending: number;
    outdated: number;
    limit: number;
    offset: number;
    profile_ready: boolean;
    profile_has_skills: boolean;
}
export interface MatchRun {processed: number; scored: number; insufficient: number; matcher_version: string}
