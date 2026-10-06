import {readJobPage} from './capture.js';
import {validPayload} from './handoff.js';

const form = document.getElementById('preview');
const message = document.getElementById('message');
const fields = ['title', 'company', 'url', 'description'];
try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    const results = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: readJobPage});
    const result = results[0]?.result;
    if (!result || result.error) throw new Error(result?.error || 'No job description was found.');
    for (const field of fields) document.getElementById(field).value = result[field] || '';
    message.textContent = result.method + '. Check and edit the preview below. Nothing has been sent.';
    form.hidden = false;
} catch (error) {
    message.textContent = error.message || 'This page cannot be read. Paste the description in JobPilot instead.';
}
document.getElementById('cancel').addEventListener('click', () => window.close());
form.addEventListener('submit', async event => {
    event.preventDefault();
    const payload = Object.fromEntries(fields.map(field => [field, document.getElementById(field).value.trim()]));
    if (!validPayload(payload)) {message.textContent = 'Check the URL and description length.'; return;}
    const button = document.getElementById('send');
    button.disabled = true;
    try {
        const result = await chrome.runtime.sendMessage({type: 'send', payload});
        if (!result?.ok) throw new Error(result?.error || 'Could not send preview.');
        fields.forEach(field => {document.getElementById(field).value = '';});
        form.hidden = true;
        message.textContent = 'Sent to your JobPilot tab. Review it there before saving.';
    } catch (error) {
        message.textContent = error.message || 'Could not send preview.';
        button.disabled = false;
    }
});
