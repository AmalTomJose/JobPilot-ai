import type {CaptureInput} from '../types/capture.types';

interface ExtensionRuntime {
    lastError?: {message?: string};
    sendMessage: (id: string, message: {type: string; nonce: string}, callback: (response?: {payload?: unknown; error?: string}) => void) => void;
}
export function validCapture(value: unknown): value is CaptureInput {
    if (!value || typeof value !== 'object') return false;
    const item = value as Record<string, unknown>;
    if (typeof item.title !== 'string' || item.title.length > 255 || typeof item.company !== 'string' || item.company.length > 255 ||
        typeof item.description !== 'string' || item.description.trim().length < 40 || item.description.length > 20000 ||
        typeof item.url !== 'string' || item.url.length > 2048) return false;
    try {const url = new URL(item.url); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password;} catch {return false;}
}
export function receivePreview(hash: string): Promise<CaptureInput> {
    const params = new URLSearchParams(hash.replace(/^#/, ''));
    const id = params.get('extension') || '';
    const nonce = params.get('handoff') || '';
    if (!/^[a-p]{32}$/.test(id) || !/^[a-f0-9-]{36}$/.test(nonce)) return Promise.reject(new Error('Invalid extension handoff. Send the preview again.'));
    const runtime = (window as unknown as {chrome?: {runtime?: ExtensionRuntime}}).chrome?.runtime;
    if (!runtime?.sendMessage) return Promise.reject(new Error('Open this page in Chrome with the JobPilot extension installed, or paste the description below.'));
    return new Promise((resolve, reject) => {
        const timeout = window.setTimeout(() => reject(new Error('The extension did not respond. Send the preview again.')), 10000);
        runtime.sendMessage(id, {type: 'claim', nonce}, response => {
            window.clearTimeout(timeout);
            if (runtime.lastError || !response || !validCapture(response.payload)) {
                reject(new Error(response?.error || 'The preview expired or was already received. Send it again from the extension.'));
            } else {
                const {title, company, url, description} = response.payload;
                resolve({title, company, url, description});
            }
        });
    });
}
