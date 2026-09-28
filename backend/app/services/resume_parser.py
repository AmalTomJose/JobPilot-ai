"""Conservative, deterministic rules. No HTTP, database access, or AI calls.

Preserve original entry blocks when a pattern is ambiguous. Dates stay verbatim;
we do not guess employers, locations, degree fields, or missing date components.
"""
import re
from email_validator import validate_email, EmailNotValidError
from app.services.text_rules import normalize_text, skill_values, unique
from app.schemas.resume_parse import (
    ResumeDraft, ExperienceDraft, EducationDraft, ProjectDraft, ParseResult, ParseWarning,
)

PARSER_VERSION = 'rules-v3'
MAX_TEXT_LENGTH = 200_000
ALIASES = {
    'summary': {'summary', 'professional summary', 'profile', 'objective', 'about me', 'career objective', 'career summary', 'personal profile'},
    'skills': {'skills', 'technical skills', 'technologies', 'core competencies', 'technical expertise', 'skills and technologies', 'technical proficiencies'},
    'experience': {'experience', 'work experience', 'professional experience', 'employment history', 'employment', 'work history', 'internships', 'relevant experience'},
    'education': {'education', 'academic background', 'qualifications', 'academic qualifications', 'educational background', 'education and training'},
    'projects': {'projects', 'personal projects', 'selected projects', 'academic projects', 'key projects'},
}
HEADINGS = {alias: section for section, aliases in ALIASES.items() for alias in aliases}
EMAIL = re.compile(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+')
URL = re.compile(r'(?:https?://|www\.|(?:linkedin\.com|github\.com)/)[^\s<>]+', re.I)
MONTH = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?'
YEAR_DATE = rf'(?:{MONTH}\s+(?:19|20)\d{{2}}|\d{{1,2}}[/-](?:19|20)\d{{2}}|(?:19|20)\d{{2}})'
DATE_PATTERN = rf'{YEAR_DATE}(?:\s*(?:[-–—]|to)\s*(?:{YEAR_DATE}|present|current|now|ongoing))?'
DATE = re.compile(rf'^{DATE_PATTERN}$', re.I)
DATE_IN_LINE = re.compile(rf'(?<![\w/]){DATE_PATTERN}(?![\w/])', re.I)
ROLE = re.compile(r'\b(developer|engineer|designer|analyst|manager|intern|consultant|scientist|specialist|architect|administrator|researcher|associate|executive|technician)\b', re.I)
DEGREE = re.compile(r'^(?:BSc|B\.Sc\.?|MSc|M\.Sc\.?|BA|B\.A\.?|MA|MBA|BTech|B\.Tech\.?|MTech|M\.Tech\.?|BCA|MCA|BCom|MCom|BEng|MEng|PhD|Ph\.D\.?|Bachelor|Master|Doctor|Diploma|Associate|(?:[A-Za-z]+\s+){1,5}Training)\b', re.I)
BULLET = re.compile(r'^\s*(?:[-*]\s+|[•●▪◦\uf0b7]\s*)')
UNKNOWN_HEADINGS = {'certifications', 'certificates', 'awards', 'interests', 'languages', 'references', 'volunteering', 'publications', 'achievements'}


def normalize(text):
    text = normalize_text(text)
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def split_sections(text):
    sections = {'header': []}
    current = 'header'
    for line in text.splitlines():
        clean = re.sub(r'^[-•●▪#*\s]+|[*#]+$', '', line).strip()
        heading = clean.rstrip(':').strip().casefold()
        key, sep, inline = clean.partition(':')
        if current == 'projects' and key.casefold() in {'technologies', 'skills', 'description'} and sep:
            sections.setdefault(current, []).append(line)
            continue
        if sep and key.casefold() in HEADINGS and inline.strip():
            current = HEADINGS[key.casefold()]
            sections.setdefault(current, []).append(inline.strip())
            continue
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
    values = []
    for line in lines:
        key, separator, value = line.partition(':')
        if separator and key.strip().casefold() in names and value.strip():
            values.append(value.strip())
    candidates = unique(values)
    return candidates[0] if len(candidates) == 1 else None


def links(text):
    return unique(match.rstrip('.,);]') for match in URL.findall(text))


def date_value(lines):
    explicit = labeled(lines, {'dates', 'date', 'duration', 'period'})
    if explicit:
        return explicit
    # Dates in achievements are not employment/education dates.
    for line in lines[:4]:
        if not BULLET.match(line):
            match = DATE_IN_LINE.search(line)
            if match:
                return match.group()
    return None


def role_line(line):
    return bool(ROLE.search(line) and len(line.split()) <= 14 and not BULLET.match(line)
                and not re.match(r'(?i)^(?:built|worked|led|helped|managed|collaborated|supported)\b', line))


def company_line(line):
    return bool(line and len(line.split()) <= 8 and ':' not in line and not BULLET.match(line)
                and not DATE.fullmatch(line) and not role_line(line)
                and not re.match(r'(?i)^(?:built|worked|led|helped|managed|collaborated|supported|developed|created|responsible|remote|hybrid|onsite|on-site)\b', line)
                and (not line.endswith('.') or re.search(r'(?i)\b(?:inc|ltd|co|corp)\.$', line)))


def blocks(text, kind):
    """Use entry headers, not incidental blank lines inside an entry."""
    output, current = [], []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            if kind == 'projects' and current:
                following = next((item for item in lines[index + 1:] if item.strip()), '')
                if following and not BULLET.match(following) and not following.lower().startswith(('technologies:', 'stack:', 'http')):
                    output.append('\n'.join(current)); current = []
            continue
        following = next((item for item in lines[index + 1:] if item.strip()), '')
        start = False
        if kind == 'experience':
            start = bool(re.match(r'(?i)^(?:title|role|job title):', line)) or role_line(line)
            # Company-first entries are recognizable when immediately followed by a role.
            if company_line(line) and not DATE_IN_LINE.search(line) and role_line(following):
                start = True
        elif kind == 'education':
            start = bool(DEGREE.search(line) or re.match(r'(?i)^(?:degree|qualification):', line))
            if re.search(r'(?i)\b(university|college|institute|school)\b', line) and DEGREE.search(following):
                start = True
        elif kind == 'projects':
            start = bool(re.match(r'(?i)^(?:project|project name|name):', line))
        complete_header = (any(role_line(item) for item in current) if kind == 'experience'
                           else any(DEGREE.search(item) or re.match(r'(?i)^(?:degree|qualification):', item) for item in current))
        if start and current and (kind == 'projects' or complete_header and date_value(current) or any(BULLET.match(item) for item in current)):
            output.append('\n'.join(current)); current = []
        current.append(line)
    if current:
        output.append('\n'.join(current))
    return output


def header_parts(line):
    without_date = DATE_IN_LINE.sub('', line).strip(' |,–—-')
    return [part.strip(' ,') for part in re.split(r'\s*\|\s*|\s+[–—]\s+|\s+at\s+', without_date) if part.strip(' ,')]


def descriptions(lines):
    result = []
    for line in lines:
        if BULLET.match(line):
            result.append(BULLET.sub('', line))
        elif result and not re.match(r'(?i)^(?:location|dates?|company|title|technologies|stack|https?):', line):
            result[-1] += ' ' + line
    return result


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
    # Scope uncertainty to the section containing wide spacing. One sidebar must
    # not erase unrelated contact, education, or skill information.
    original_sections = split_sections(normalize_text(raw_text))
    uncertain = {key for key, value in original_sections.items() if re.search(r'\S(?:\t| {3,})\S', value)}
    text = normalize(raw_text)
    sections = split_sections(text)
    draft = ResumeDraft()
    header = sections.get('header', '')
    header_lines = [part.strip() for line in header.splitlines() for part in re.split(r'\s*[|•]\s*', line)]
    contact = draft.contact
    contact.name = labeled(header_lines, {'name', 'full name'})
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
    if not contact.name and len(valid_emails) == 1:
        first = next((line for line in header_lines if line.strip()), '')
        words = first.split()
        if (2 <= len(words) <= 4 and all(word[0].isupper() and re.fullmatch(r"[^\W\d_]+(?:[’'-][^\W\d_]+)*\.?", word) for word in words)
                and not ROLE.search(first) and not re.search(r'(?i)\b(resume|curriculum|vitae|contact|profile|looking|seeking|opportunities)\b', first)):
            contact.name = first
            warn('CHECK_NAME', 'contact', 'The first header line was used as your name. Confirm it during review.')
    if not contact.name:
        warn('CONTACT_NAME_UNCERTAIN', 'contact', 'No clear name was found. Confirm your name in the review step.')
    phone = labeled(header_lines, {'phone', 'mobile', 'tel', 'telephone'})
    if phone and re.fullmatch(r'\+?[\d ()\-.]+', phone) and 7 <= len(re.sub(r'\D', '', phone)) <= 15:
        contact.phone = phone
    elif phone:
        warn('AMBIGUOUS_PHONE', 'contact', 'The labeled phone number could not be validated.')
    elif not phone:
        phone_text = '\n'.join(line for line in header_lines if not URL.search(line) and not DATE.fullmatch(line))
        candidates = unique(match.group().strip() for match in re.finditer(r'(?<![\w/])\+?\d[\d () .-]{6,}\d(?![\w/])', phone_text)
                            if 10 <= len(re.sub(r'\D', '', match.group())) <= 15
                            and not DATE.fullmatch(match.group().strip()))
        if len(candidates) == 1:
            contact.phone = candidates[0]
        elif candidates:
            warn('AMBIGUOUS_PHONE', 'contact', 'Multiple phone numbers were found; choose one during review.')
    contact.location = labeled(header_lines, {'location', 'address'})
    contact.links = links(header)
    draft.summary = sections.get('summary') or None
    draft.skills = [] if 'skills' in uncertain else skill_values(sections.get('skills', ''))
    unclassified = [header, sections.get('unclassified', '')]
    if sections.get('unclassified'):
        warn('UNRECOGNIZED_SECTION', 'document', 'Additional sections were preserved as unclassified text.')
    if not any(key in sections for key in ALIASES):
        warn('NO_SECTIONS_FOUND', 'document', 'No supported section headings were found. Original text is preserved for review.')

    for block in blocks(sections.get('experience', ''), 'experience'):
        lines = block.splitlines()
        entry = ExperienceDraft(source_text=block)
        if 'experience' not in uncertain:
            entry.title = labeled(lines, {'title', 'role', 'job title'})
            entry.company = labeled(lines, {'company', 'employer'})
            entry.location = labeled(lines, {'location'})
            entry.date_text = date_value(lines)
            parts = header_parts(lines[0])
            if len(parts) == 2 and role_line(parts[0]) and company_line(parts[1]):
                entry.title = entry.title or parts[0]
                entry.company = entry.company or parts[1]
            elif len(lines) >= 2 and entry.date_text:
                first = header_parts(lines[0])
                second = header_parts(lines[1])
                if len(first) == len(second) == 1 and ':' not in first[0] and ':' not in second[0] and not BULLET.match(lines[1]):
                    if role_line(first[0]) and company_line(second[0]):
                        entry.title = entry.title or first[0]
                        entry.company = entry.company or second[0]
                    elif role_line(second[0]) and company_line(first[0]):
                        entry.title = entry.title or second[0]
                        entry.company = entry.company or first[0]
            entry.description = descriptions(lines)
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
        if 'education' not in uncertain:
            entry.degree = labeled(lines, {'degree', 'qualification'})
            entry.institution = labeled(lines, {'institution', 'university', 'school'})
            entry.field_of_study = labeled(lines, {'field', 'field of study', 'major'})
            entry.date_text = date_value(lines)
            parts = header_parts(lines[0])
            if len(parts) == 2 and DEGREE.search(parts[0]):
                entry.degree = entry.degree or parts[0]
                entry.institution = entry.institution or parts[1]
            elif len(lines) >= 2 and entry.date_text:
                first, second = header_parts(lines[0]), header_parts(lines[1])
                if len(first) == len(second) == 1 and not BULLET.match(lines[1]) and ':' not in second[0]:
                    if DEGREE.search(first[0]):
                        entry.degree = entry.degree or first[0]
                        entry.institution = entry.institution or second[0]
                    elif DEGREE.search(second[0]) and re.search(r'(?i)\b(university|college|institute|school)\b', first[0]):
                        entry.institution = entry.institution or first[0]
                        entry.degree = entry.degree or second[0]
        if not entry.degree or not entry.institution:
            warn('AMBIGUOUS_EDUCATION', 'education', 'Some education details could not be identified. Check the preserved source blocks.')
        draft.education.append(entry)

    for block in blocks(sections.get('projects', ''), 'projects'):
        lines = block.splitlines()
        entry = ProjectDraft(source_text=block)
        if 'projects' not in uncertain:
            entry.name = labeled(lines, {'project', 'name', 'project name'})
            technologies = labeled(lines, {'technologies', 'tech stack', 'stack'})
            entry.technologies = skill_values(technologies or '')
            entry.description = descriptions(lines)
            entry.links = links(block)
            first = lines[0]
            if not entry.name and (entry.technologies or entry.description) and len(first.split('|')[0].split()) <= 8 and not BULLET.match(first) and ':' not in first and not URL.search(first):
                entry.name = first.split('|')[0].strip()
                warn('CHECK_PROJECT_NAME', 'projects', 'An entry heading was used as a project name. Confirm it during review.')
        if not entry.name:
            warn('AMBIGUOUS_PROJECT', 'projects', 'A project name could not be identified. Its source text is preserved.')
        draft.projects.append(entry)
    draft.unclassified_text = '\n\n'.join(part for part in unclassified if part) or None
    return ParseResult(draft=draft, warnings=warnings, parser_version=PARSER_VERSION)
