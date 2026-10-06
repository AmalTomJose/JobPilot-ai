export const APP_ORIGIN = 'http://localhost:5173';
export const TTL_MS = 10 * 60 * 1000;
export function validPayload(data) {
    if (!data || typeof data !== 'object') return false;
    if (typeof data.title !== 'string' || data.title.length > 255 || typeof data.company !== 'string' || data.company.length > 255) return false;
    if (typeof data.description !== 'string' || data.description.trim().length < 40 || data.description.length > 20000) return false;
    try {
        const url = new URL(data.url);
        return typeof data.url === 'string' && data.url.length <= 2048 &&
            ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password;
    } catch { return false; }
}
export function allowedReceiver(sender, record, nonce, now = Date.now()) {
    try {
        const url = new URL(sender.url);
        return !!record && record.expires > now && record.nonce === nonce &&
            sender.tab?.id === record.tabId && sender.frameId === 0 &&
            url.origin === APP_ORIGIN && url.pathname === '/jobs/capture';
    } catch { return false; }
}
