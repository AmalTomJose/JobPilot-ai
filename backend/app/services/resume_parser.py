"""Conservative, deterministic rules. No HTTP, database access, or AI calls.

Preserve original entry blocks when a pattern is ambiguous. Dates stay verbatim;
we do not guess employers, locations, degree fields, or missing date components.
"""
import re
from email_validator import validate_email, EmailNotValidError
from app.schemas.resume_parse import (
    ResumeDraft, ExperienceDraft, EducationDraft, ProjectDraft, ParseResult, ParseWarning,
)

PARSER_VERSION = 'rules-v1'
MAX_TEXT_LENGTH = 200_000
ALIASES = {
    'summary': {'summary', 'professional summary', 'profile', 'objective', 'about me'},
    'skills': {'skills', 'technical skills', 'technologies', 'core competencies'},
    'experience': {'experience', 'work experience', 'professional experience', 'employment history'},
    'education': {'education', 'academic background', 'qualifications'},
    'projects': {'projects', 'personal projects', 'selected projects'},
}
HEADINGS = {alias: section for section, aliases in ALIASES.items() for alias in aliases}
EMAIL = re.compile(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+')
URL = re.compile(r'(?:https?://|www\.|(?:linkedin\.com|github\.com)/)[^\s<>]+', re.I)
DATE = re.compile(r'^(?:(?:[A-Za-z]+\s+)?(?:19|20)\d{2}|\d{1,2}[/-](?:19|20)\d{2})(?:\s*[-–—]\s*(?:(?:[A-Za-z]+\s+)?(?:19|20)\d{2}|\d{1,2}[/-](?:19|20)\d{2}|present|current|now))?$', re.I)
ROLE = re.compile(r'\b(developer|engineer|designer|analyst|manager|intern|consultant|scientist|specialist|architect|administrator|researcher)\b', re.I)
DEGREE = re.compile(r'^(?:BSc|B\.Sc\.?|MSc|M\.Sc\.?|BA|B\.A\.?|MA|MBA|BTech|B\.Tech|MTech|PhD|Ph\.D\.?|Bachelor|Master|Doctor|Diploma|Associate)\b', re.I)
BULLET = re.compile(r'^\s*[-•●▪◦*]\s+')
UNKNOWN_HEADINGS = {'certifications', 'certificates', 'awards', 'interests', 'languages', 'references', 'volunteering', 'publications', 'achievements'}


def unique(values):
    seen = set()
    output = []
    for value in values:
        value = value.strip()
        if value and value.casefold() not in seen:
            output.append(value)
            seen.add(value.casefold())
    return output


def normalize(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\u00a0', ' ')
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def split_sections(text):
    sections = {'header': []}
    current = 'header'
    for line in text.splitlines():
        heading = line.strip().rstrip(':').casefold()
        if heading in HEADINGS:
            current = HEADINGS[heading]
            sections.setdefault(current, []).append('')
        elif heading in UNKNOWN_HEADINGS or (line.isupper() and 1 <= len(line.split()) <= 4 and line.endswith(':')):
            current = 'unclassified'
            sections.setdefault(current, []).append(line)
        else:
            sections.setdefault(current, []).append(line)
    return {key: '\n'.join(value).strip() for key, value in sections.items()}


def labeled(lines, names):
    for line in lines:
        key, separator, value = line.partition(':')
        if separator and key.strip().casefold() in names and value.strip():
            return value.strip()
    return None


def links(text):
    return unique(match.rstrip('.,);]') for match in URL.findall(text))


def skill_values(text):
    # Only remove known category labels; preserve punctuation inside skill names.
    text = re.sub(r'(?im)^(?:languages|frameworks|tools|databases|technologies|skills)\s*:\s*', '', text)
    return unique(BULLET.sub('', value) for value in re.split(r'[,;\n|•●▪]', text))


def blocks(text, kind):
    """Blank lines separate entries; a new recognizable header also starts one."""
    output, current = [], []
    source_lines = text.splitlines()
    for index, line in enumerate(source_lines):
        if not line.strip() and current:
            following = next((value for value in source_lines[index + 1:] if value.strip()), '')
            if BULLET.match(following):
                continue
        is_start = ((kind == 'experience' and (ROLE.search(line) and len(line.split()) <= 10 and not BULLET.match(line)))
                    or (kind == 'education' and DEGREE.search(line)))
        # Avoid splitting a company name containing a role word before its dates.
        if not line.strip() or (is_start and current and any(DATE.fullmatch(item) for item in current)):
            if current:
                output.append('\n'.join(current))
                current = []
        if line.strip():
            current.append(line)
    if current:
        output.append('\n'.join(current))
    return output


def parse_resume(raw_text: str) -> ParseResult:
    if not raw_text or not raw_text.strip():
        raise ValueError('There is no extracted text to parse')
    if len(raw_text) > MAX_TEXT_LENGTH:
        raise ValueError(f'Resume text exceeds the {MAX_TEXT_LENGTH:,}-character parsing limit')
    warnings = []
    def warn(code, section, message):
        warning = ParseWarning(code=code, section=section, message=message)
        if warning not in warnings:
            warnings.append(warning)

    layout_issue = bool(re.search(r'\S(?:\t| {3,})\S', raw_text))
    if layout_issue:
        warn('POSSIBLE_LAYOUT_ISSUE', 'document', 'Column spacing was detected. Check the original text; entry fields are left empty where layout is uncertain.')
    text = normalize(raw_text)
    sections = split_sections(text)
    draft = ResumeDraft()
    header = sections.get('header', '')
    header_lines = header.splitlines()
    contact = draft.contact
    contact.name = labeled(header_lines, {'name', 'full name'})
    # Names without explicit labels are deliberately left for human review.
    if not contact.name:
        warn('CONTACT_NAME_UNCERTAIN', 'contact', 'No explicitly labeled name was found. Confirm your name in the review step.')
    emails = unique(EMAIL.findall(header))
    valid_emails = []
    for email in emails:
        try:
            validate_email(email, check_deliverability=False)
            valid_emails.append(email)
        except EmailNotValidError:
            pass
    if len(valid_emails) == 1:
        contact.email = valid_emails[0]
    elif len(valid_emails) > 1:
        warn('AMBIGUOUS_EMAIL', 'contact', 'Multiple email addresses were found; no primary email was selected.')
    phone = labeled(header_lines, {'phone', 'mobile', 'tel', 'telephone'})
    if phone and re.fullmatch(r'\+?[\d ()\-.]+', phone) and 7 <= len(re.sub(r'\D', '', phone)) <= 15:
        contact.phone = phone
    elif phone:
        warn('AMBIGUOUS_PHONE', 'contact', 'The labeled phone number could not be validated.')
    contact.location = labeled(header_lines, {'location', 'address'})
    contact.links = links(header)
    draft.summary = sections.get('summary') or None
    draft.skills = [] if layout_issue else skill_values(sections.get('skills', ''))
    unclassified = [header, sections.get('unclassified', '')]
    if sections.get('unclassified'):
        warn('UNRECOGNIZED_SECTION', 'document', 'Additional sections were preserved as unclassified text.')
    if not any(key in sections for key in ALIASES):
        warn('NO_SECTIONS_FOUND', 'document', 'No supported section headings were found. Original text is preserved for review.')

    for block in blocks(sections.get('experience', ''), 'experience'):
        lines = block.splitlines()
        entry = ExperienceDraft(source_text=block)
        if not layout_issue:
            entry.title = labeled(lines, {'title', 'role', 'job title'})
            entry.company = labeled(lines, {'company', 'employer'})
            entry.location = labeled(lines, {'location'})
            entry.date_text = labeled(lines, {'dates', 'date'}) or next((line for line in lines if DATE.fullmatch(line)), None)
            parts = [part.strip() for part in lines[0].split('|')]
            if (len(parts) >= 2 and ROLE.search(parts[0]) and len(parts[0].split()) <= 8
                    and parts[1] and not DATE.fullmatch(parts[1]) and ':' not in parts[1]):
                entry.title = entry.title or parts[0]
                entry.company = entry.company or parts[1]
                if len(parts) == 3 and DATE.fullmatch(parts[2]):
                    entry.date_text = entry.date_text or parts[2]
            elif len(lines) >= 3 and ROLE.search(lines[0]) and len(lines[0].split()) <= 8 and DATE.fullmatch(lines[2]) and not BULLET.match(lines[0]) and not BULLET.match(lines[1]) and not DATE.fullmatch(lines[1]) and ':' not in lines[1]:
                entry.title = entry.title or lines[0]
                entry.company = entry.company or lines[1]
            entry.description = [BULLET.sub('', line) for line in lines if BULLET.match(line)]
            if not entry.description and entry.title and entry.company and entry.date_text:
                date_index = next((index for index, line in enumerate(lines)
                                   if line == entry.date_text or line.casefold().startswith(('dates:', 'date:'))
                                   or ('|' in line and line.split('|')[-1].strip() == entry.date_text)), None)
                if date_index is not None:
                    entry.description = [line for line in lines[date_index + 1:]
                                         if not line.casefold().startswith(('location:', 'company:', 'title:'))]
        if not entry.title or not entry.company:
            warn('AMBIGUOUS_EXPERIENCE', 'experience', 'Some job titles or employers could not be identified. Check each preserved source block.')
        draft.experience.append(entry)

    for block in blocks(sections.get('education', ''), 'education'):
        lines = block.splitlines()
        entry = EducationDraft(source_text=block)
        if not layout_issue:
            entry.degree = labeled(lines, {'degree', 'qualification'})
            entry.institution = labeled(lines, {'institution', 'university', 'school'})
            entry.field_of_study = labeled(lines, {'field', 'field of study', 'major'})
            entry.date_text = labeled(lines, {'dates', 'date'}) or next((line for line in lines if DATE.fullmatch(line)), None)
            if len(lines) >= 3 and DEGREE.search(lines[0]) and DATE.fullmatch(lines[2]) and not DATE.fullmatch(lines[1]) and not BULLET.match(lines[1]):
                entry.degree = entry.degree or lines[0]
                entry.institution = entry.institution or lines[1]
        if not entry.degree or not entry.institution:
            warn('AMBIGUOUS_EDUCATION', 'education', 'Some education details could not be identified. Check the preserved source blocks.')
        draft.education.append(entry)

    for block in blocks(sections.get('projects', ''), 'projects'):
        lines = block.splitlines()
        entry = ProjectDraft(source_text=block)
        if not layout_issue:
            entry.name = labeled(lines, {'project', 'name', 'project name'})
            technologies = labeled(lines, {'technologies', 'tech stack', 'stack'})
            entry.technologies = skill_values(technologies or '')
            entry.description = [BULLET.sub('', line) for line in lines if BULLET.match(line)]
            entry.links = links(block)
        if not entry.name:
            warn('AMBIGUOUS_PROJECT', 'projects', 'A project name could not be identified. Its source text is preserved.')
        draft.projects.append(entry)
    draft.unclassified_text = '\n\n'.join(part for part in unclassified if part) or None
    return ParseResult(draft=draft, warnings=warnings, parser_version=PARSER_VERSION)
