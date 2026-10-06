import type {JobFields, JobImport} from './job.types';
export interface CaptureInput {title: string; company: string; url: string; description: string}
export interface CapturePreview {raw_text: string; draft_data: JobFields; warnings: JobImport['warnings']; parser_version: string}
