"""Small, explainable job-email rules. No network access, HTML rendering, or AI."""
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from app.services.text_rules import normalize_text, unique, skill_values, mentioned_skills
from app.schemas.job import JobFields, JobWarning, JobParseResult, validate_job_url

PARSER_VERSION = 'job-rules-v3'
ALIASES = {
    'title': {'title', 'job title', 'role', 'position', 'job role', 'position title', 'designation'},
    'company': {'company', 'employer', 'company name', 'organization', 'organisation'},
    'location': {'location', 'job location', 'work location', 'based in'},
    'work_mode': {'work mode', 'work arrangement', 'workplace', 'workplace type', 'work model'},
    'employment_type': {'employment type', 'job type', 'contract type', 'employment'},
    'skills': {'skills', 'required skills', 'technologies', 'tech stack', 'technical skills', 'key skills', 'must have skills'},
    'application_url': {'apply', 'apply here', 'apply link', 'application url', 'application link', 'job url', 'apply now', 'view job', 'view details', 'job link'},
    'description': {'description', 'job description', 'responsibilities', 'requirements', 'about the role', 'about the job', 'what you will do', 'what you’ll do', 'qualifications', 'what we are looking for', 'required qualifications', 'preferred qualifications', 'key responsibilities', 'benefits'},
}
LABELS = {label: field for field, labels in ALIASES.items() for label in labels}
URL = re.compile(r'https?://[^\s<>"\']+', re.I)


def canonical_url(value: str | None) -> str | None:
    """Ignore known tracking parameters/anchors; preserve job identifiers and hash routes."""
    if value is None:
        return None
    validate_job_url(value)
    url = urlsplit(value)
    host = url.hostname.lower().encode('idna').decode('ascii')
    if ':' in host:
        host = f'[{host}]'
    if url.port and not (url.scheme.lower() == 'https' and url.port == 443 or url.scheme.lower() == 'http' and url.port == 80):
        host += f':{url.port}'
    params = [(key, val) for key, val in parse_qsl(url.query, keep_blank_values=True)
              if not key.casefold().startswith('utm_') and key.casefold() not in {'gclid', 'fbclid', 'mc_cid', 'mc_eid'}]
    return urlunsplit((url.scheme.lower(), host, url.path or '/', urlencode(sorted(params, key=lambda item: item[0])), '' if url.fragment.casefold() in {'', 'apply', 'application', 'top'} else url.fragment))


ROLE_WORD = re.compile(r'\b(developer|engineer|designer|analyst|manager|intern|consultant|scientist|specialist|architect|administrator|researcher|accountant|recruiter|associate|executive|tester)\b', re.I)
FOOTER = re.compile(r'(?i)^(?:unsubscribe|manage (?:your )?(?:preferences|alerts)|privacy policy|you (?:are receiving|received) this|sent (?:to|by)|view (?:this email )?in (?:your )?browser)\b')


def heading_candidate(line):
    """Recognize a role/company relationship, never arbitrary recruiter prose."""
    line = re.sub(r'(?i)^(?:subject:\s*)?(?:(?:new )?job (?:alert|opportunity)|job opening|hiring|we are hiring|we’re hiring|we\'re hiring)\s*[:!–—-]?\s*', '', line).strip()
    line = re.sub(r'(?i)^subject:\s*', '', line)
    match = re.fullmatch(r'(.{2,100}?)\s+(?:at|@)\s+(.{2,100})', line)
    if not match:
        hiring = re.fullmatch(r'(.{2,100}?) is hiring (?:an? )?(.{2,100}?)[!.]?', line, re.I)
        if hiring:
            company, title = hiring.groups()
        else:
            return None
    else:
        title, company = match.groups()
    title, company = title.strip(), company.strip().rstrip('!.')
    if (ROLE_WORD.search(title) and len(title.split()) <= 10 and len(company.split()) <= 8
            and not re.search(r'(?i)\b(?:we|you|our|your|looking|seeking|need|apply|https?)\b', title + ' ' + company)
            and not any(symbol in company for symbol in '|:<>')):
        return title, company
    return None


def parse_job_email(raw_text: str) -> JobParseResult:
    if not raw_text.strip() or len(raw_text) > 100000:
        raise ValueError('Expected between 1 and 100,000 characters of email text')
    warnings = []

    def warn(code, field, message):
        warning = JobWarning(code=code, field=field, message=message)
        if warning not in warnings:
            warnings.append(warning)

    text = normalize_text(raw_text)
    values, descriptions, body, inferred = {}, [], [], []
    section = None
    pending = None
    for original in text.splitlines():
        line = re.sub(r'^\s*(?:>\s*|[•●▪]\s*|[-*]\s+)', '', original).strip()
        line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)
        if FOOTER.match(line):
            break
        key, sep, value = line.partition(':')
        field = LABELS.get(key.strip().casefold()) if sep else LABELS.get(line.casefold())
        if field:
            pending = None
            section = field
            if field == 'description':
                descriptions.append((key + ': ' if key.casefold() not in {'description', 'job description'} else '') + value.strip())
            elif value.strip():
                values.setdefault(field, []).append(value.strip())
            elif field != 'skills':
                pending = field
            continue
        if pending and line:
            # An unknown label must not become a scalar field value.
            if not re.match(r'^[A-Za-z ]{1,40}:', line) or pending == 'application_url' and URL.search(line):
                values.setdefault(pending, []).append(line)
            pending = None
            section = None
            continue
        candidate = heading_candidate(line)
        if candidate:
            inferred.append(candidate)
        if section == 'description':
            descriptions.append(line)
        elif section == 'skills' and line:
            if sep or len(line.split()) > 16:
                section = None
                body.append(line)
            else:
                values.setdefault('skills', []).append(line)
        elif line and not re.match(r'(?i)^(?:from|to|sent|date):', line):
            body.append(line)
        if not line and section != 'description':
            section = None

    for title, company in inferred:
        values.setdefault('title', []).append(title)
        # Avoid overriding explicit company labels, but retain conflict warnings.
        values.setdefault('company', []).append(company)
    draft = JobFields()
    if len(unique(values.get('title', []))) > 1:
        warn('MULTIPLE_JOBS', 'document', 'Several distinct roles were found. Paste one opening at a time; fields were left empty to avoid combining jobs.')
        return JobParseResult(draft_data=draft, warnings=warnings, parser_version=PARSER_VERSION)
    for field in ('title', 'company', 'location', 'employment_type'):
        candidates = unique(values.get(field, []))
        if len(candidates) == 1 and len(candidates[0]) <= 255:
            setattr(draft, field, candidates[0])
        elif candidates:
            warn('AMBIGUOUS_FIELD', field, f'Multiple or oversized {field.replace("_", " ")} values were found. Enter the correct value during review.')
    if inferred:
        warn('CHECK_HEADING', 'title', 'The job heading supplied role/company information. Confirm these fields during review.')

    modes = {'remote': 'remote', 'hybrid': 'hybrid', 'onsite': 'onsite', 'on-site': 'onsite', 'on site': 'onsite'}
    mode_source = values.get('work_mode', [])
    # Work mode often appears alongside the explicit location, e.g. Bengaluru (Hybrid).
    if not mode_source and draft.location:
        mode_source = [draft.location]
    if not mode_source:
        mode_source = [line for line in body if line.casefold() in modes]
    found_modes = unique(modes[match.group().casefold()] for value in mode_source
                         for match in re.finditer(r'\b(?:remote|hybrid|on-site|on site|onsite)\b', value, re.I))
    if len(found_modes) == 1 and not any(re.search(r'(?i)\b(?:not|no|non)\b', value) for value in mode_source):
        draft.work_mode = found_modes[0]
    elif values.get('work_mode'):
        warn('UNKNOWN_WORK_MODE', 'work_mode', 'Work arrangement could not be identified unambiguously. Choose it during review.')
    if not draft.employment_type:
        employment = unique(line for line in body if re.fullmatch(r'(?i)(?:full[- ]time|part[- ]time|contract|internship|temporary|freelance)', line))
        if len(employment) == 1:
            draft.employment_type = employment[0]

    description = '\n'.join(descriptions).strip()
    if not description:
        # Preserve the unlabeled body as a description rather than throwing it away.
        description = '\n'.join(body).strip()
        if description:
            warn('CHECK_DESCRIPTION', 'description', 'Unlabeled email text was kept as the description. Remove greetings or unrelated content during review.')
    if len(description) <= 20000:
        draft.description = description or None
    else:
        warn('LONG_DESCRIPTION', 'description', 'The description exceeds the review limit. Summarize it; the complete source is preserved.')
    skills = skill_values('\n'.join(values.get('skills', [])))
    if not skills:
        # Only recognize exact named technologies, not implied or negated requirements.
        skill_text = '\n'.join(line for line in description.splitlines() if not re.search(r'(?i)\b(?:not|no|without|optional)\b', line)
                               and not URL.search(line))
        skills = mentioned_skills(skill_text)
        if skills:
            warn('CHECK_SKILLS', 'skills', 'Named technologies were found in the description. Confirm which belong in the job skills list.')
    draft.skills = [item for item in skills if len(item) <= 255][:100]
    if len(skills) > len(draft.skills):
        warn('SKILL_LIMIT', 'skills', 'Some skill entries exceeded the field limits. Check the original email.')

    candidates = []
    explicit = values.get('application_url', [])
    for value in explicit:
        matches = URL.findall(value)
        candidates.extend(matches or [value])
    if not candidates:
        # Apply buttons copied as Markdown or plain text carry stronger evidence
        # than unrelated privacy/footer links. URLs are never opened here.
        for line in text.splitlines():
            if re.match(r'(?i)^\s*(?:\[)?(?:apply(?: now| here)?|view (?:job|details))\b', line):
                candidates.extend(URL.findall(line))
    preferred = bool(candidates)
    if not candidates:
        candidates = URL.findall(text)
    candidates = unique(value.rstrip('.,);]') for value in candidates)
    valid = []
    for value in candidates:
        try:
            validate_job_url(value)
            if len(value) > 2048:
                raise ValueError()
            valid.append(value)
        except ValueError:
            warn('INVALID_LINK', 'application_url', 'A link could not be used as an application URL. Check the original email.')
    if len(valid) == 1:
        draft.application_url = valid[0]
        if not preferred:
            warn('CHECK_LINK', 'application_url', 'One web link was found. Confirm that it opens the job application, rather than an email preference page.')
    elif len(valid) > 1:
        warn('AMBIGUOUS_LINK', 'application_url', 'Multiple web links were found. Select the correct application URL during review.')
    for field in ('title', 'company'):
        if not getattr(draft, field):
            warn('MISSING_FIELD', field, f'No clear {field} was found. Add it during review if known.')
    warn('REVIEW_REQUIRED', 'document', 'Extraction uses text patterns, not AI. Compare the draft with the source before saving.')
    return JobParseResult(draft_data=draft, warnings=warnings, parser_version=PARSER_VERSION)
