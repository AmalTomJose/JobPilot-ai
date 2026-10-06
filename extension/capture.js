// Self-contained: Chrome copies this function into an isolated page context.
export function readJobPage() {
    const host = location.hostname.toLowerCase();
    if (host === 'linkedin.com' || host.endsWith('.linkedin.com')) {
        return {error: 'LinkedIn page reading is disabled. Copy the description yourself and paste it in JobPilot.'};
    }
    if (!['http:', 'https:'].includes(location.protocol)) {
        return {error: 'Open a permitted public job page first.'};
    }
    const clean = value => String(value || '').replace(/\r/g, '').trim();
    const selected = clean(window.getSelection()?.toString());
    let title = '';
    let company = '';
    let description = selected;
    let method = selected ? 'Selected text' : '';
    // Do not read the entire page. Prefer a single explicit JobPosting or a known description section.
    const postings = [];
    function visit(value, depth = 0) {
        if (!value || depth > 8 || postings.length > 10) return;
        if (Array.isArray(value)) { value.slice(0, 100).forEach(item => visit(item, depth + 1)); return; }
        if (typeof value !== 'object') return;
        const type = value['@type'];
        if (type === 'JobPosting' || Array.isArray(type) && type.includes('JobPosting')) postings.push(value);
        if (value['@graph']) visit(value['@graph'], depth + 1);
        if (value.mainEntity) visit(value.mainEntity, depth + 1);
    }
    for (const node of [...document.querySelectorAll('script[type="application/ld+json"]')].slice(0, 20)) {
        const text = node.textContent || '';
        if (text.length > 200000) continue;
        try {visit(JSON.parse(text));} catch { /* malformed metadata is ignored */ }
    }
    if (postings.length === 1) {
        title = clean(postings[0].title);
        company = clean(postings[0].hiringOrganization?.name);
        if (!description) {
            // Detached template is inert: never attach provider markup or load its assets.
            const template = document.createElement('template');
            template.innerHTML = String(postings[0].description || '');
            template.content.querySelectorAll('script,style,iframe,img').forEach(node => node.remove());
            template.content.querySelectorAll('p,div,br,li,h1,h2,h3').forEach(node => node.append('\n'));
            description = clean(template.content.textContent);
            method = 'Job posting metadata';
        }
    }
    if (!description && postings.length <= 1) {
        const nodes = document.querySelectorAll('[itemprop="description"], [data-testid="job-description"], #job-description, .job-description');
        if (nodes.length === 1) {
            description = clean(nodes[0].innerText);
            method = 'Job description section';
        }
    }
    if (!title) title = clean(document.querySelector('h1')?.innerText);
    if (!description) return {error: 'Select only the full job description on the page, then open this extension again. We did not copy the entire page.'};
    if (description.length < 40 || description.length > 20000) return {error: 'Select one complete job description between 40 and 20,000 characters.'};
    const url = new URL(location.href);
    url.username = ''; url.password = ''; url.hash = '';
    for (const key of [...url.searchParams.keys()]) {
        if (/^(utm_|trk|tracking|ref|token|auth|session)/i.test(key)) url.searchParams.delete(key);
    }
    return {title: title.slice(0, 255), company: company.slice(0, 255), description, url: url.href, method};
}
