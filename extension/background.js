import {APP_ORIGIN, TTL_MS, validPayload, allowedReceiver} from './handoff.js';

// Only the packaged popup can create a handoff. Websites cannot create or list them.
let chain = Promise.resolve();
chrome.runtime.onMessage.addListener((message, sender, reply) => {
    if (sender.id !== chrome.runtime.id || sender.url !== chrome.runtime.getURL('popup.html') || message?.type !== 'send') return;
    chain = chain.then(async () => {
        if (!validPayload(message.payload)) throw new Error('Invalid job preview.');
        await cleanExpired();
        const all = await chrome.storage.session.get(null);
        if (Object.keys(all).length >= 10) throw new Error('Finish or close an earlier preview before sending another.');
        const nonce = crypto.randomUUID();
        // Create a blank tab first: bind its ID before allowing the app to request content.
        const tab = await chrome.tabs.create({url: 'about:blank'});
        try {
            await chrome.storage.session.set({[nonce]: {nonce, tabId: tab.id, expires: Date.now() + TTL_MS, payload: message.payload}});
            await chrome.tabs.update(tab.id, {url: APP_ORIGIN + '/jobs/capture#extension=' + chrome.runtime.id + '&handoff=' + nonce});
            reply({ok: true});
        } catch (error) {
            await chrome.storage.session.remove(nonce);
            throw error;
        }
    }).catch(() => reply({error: 'Could not send the preview. Try again after finishing an earlier preview.'}));
    return true;
});

chrome.runtime.onMessageExternal.addListener((message, sender, reply) => {
    if (message?.type !== 'claim' || typeof message.nonce !== 'string' || !/^[a-f0-9-]{36}$/.test(message.nonce)) return;
    // Serialize claims so the same handoff cannot be consumed twice.
    chain = chain.then(async () => {
        const record = (await chrome.storage.session.get(message.nonce))[message.nonce];
        if (!allowedReceiver(sender, record, message.nonce)) {reply({error: 'Preview unavailable or expired. Send it again from the extension.'}); return;}
        await chrome.storage.session.remove(message.nonce);
        reply({payload: record.payload});
    }).catch(() => reply({error: 'Preview unavailable. Send it again.'}));
    return true;
});

async function cleanExpired() {
    const values = await chrome.storage.session.get(null);
    const expired = Object.entries(values).filter(([, value]) => value.expires <= Date.now()).map(([key]) => key);
    if (expired.length) await chrome.storage.session.remove(expired);
}
chrome.alarms.create('expire-previews', {periodInMinutes: 1});
chrome.alarms.onAlarm.addListener(alarm => {if (alarm.name === 'expire-previews') void cleanExpired();});
chrome.tabs.onRemoved.addListener(tabId => {
    chain = chain.then(async () => {
        const records = await chrome.storage.session.get(null);
        const keys = Object.entries(records).filter(([, record]) => record.tabId === tabId).map(([key]) => key);
        if (keys.length) await chrome.storage.session.remove(keys);
    }).catch(() => {});
});
