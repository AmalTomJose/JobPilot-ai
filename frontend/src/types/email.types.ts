export interface GmailStatus {
    configured: boolean;
    status: 'disconnected' | 'connected' | 'reconnect_required';
    mailbox_email: string | null;
    label_id: string | null;
    label_name: string | null;
    import_since: string | null;
    auto_sync: boolean;
    next_sync_at: string | null;
    last_sync_at: string | null;
    last_error: string | null;
    has_more: boolean;
}
export interface GmailLabel {id: string; name: string}
export interface GmailSelection {label_id: string; import_since: string; auto_sync: boolean}
export interface EmailMessage {gmail_url?: string | null; openings?: {title: string | null; job_url: string}[]; id: number; subject: string; sender: string; received_at: string | null; import_id: number | null; status: string; warning: string | null}
export interface EmailPage {items: EmailMessage[]; total: number; limit: number; offset: number}
export interface SyncRun {id: number; started_at: string; finished_at: string | null; status: string; imported: number; skipped: number; needs_review: number; error: string | null}
