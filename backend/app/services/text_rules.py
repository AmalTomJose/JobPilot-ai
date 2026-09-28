"""Small shared text helpers. Normalization is for parsing, never source storage."""
import re
import unicodedata

BULLET = re.compile(r'^\s*[-•●▪◦*‣►]\s*')
SKILL_CATEGORIES = r'backend and databases|cloud and tools|languages|programming languages|frameworks|libraries|tools|developer tools|databases|technologies|technical skills|skills|cloud|cloud platforms|platforms|backend|frontend|devops'
# Used only for extracting explicitly mentioned skills from prose, not inferring them.
KNOWN_SKILLS = (
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', '.NET', 'Node.js',
    'React', 'React.js', 'Next.js', 'Angular', 'Vue.js', 'HTML', 'CSS', 'SQL',
    'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'FastAPI', 'Django', 'Flask',
    'Spring Boot', 'Docker', 'Kubernetes', 'AWS', 'Azure', 'Google Cloud',
    'Git', 'GitHub Actions', 'CI/CD', 'Linux', 'REST', 'GraphQL', 'Terraform',
    'Pandas', 'NumPy', 'TensorFlow', 'PyTorch', 'Excel', 'Power BI', 'Tableau',
    'Figma', 'Kotlin', 'Swift', 'Rust', 'Golang', 'Ruby', 'PHP', 'Laravel',
)


def normalize_text(text):
    return unicodedata.normalize('NFKC', text).replace('\r\n', '\n').replace('\r', '\n').replace('\u200b', '').replace('\ufeff', '').replace('\u00ad', '').replace('\uf0b7', '•')


def unique(values):
    seen, output = set(), []
    for value in values:
        value = value.strip()
        if value and value.casefold() not in seen:
            output.append(value)
            seen.add(value.casefold())
    return output


def mentioned_skills(text):
    matches = []
    for skill in KNOWN_SKILLS:
        for match in re.finditer(r'(?<![\w.+#])' + re.escape(skill) + r'(?![\w+#]|\.[A-Za-z])', text, re.I):
            matches.append((match.start(), match.group()))
    return unique(value for _, value in sorted(matches))


def skill_values(text):
    output = []
    for line in text.splitlines():
        line = BULLET.sub('', line).strip()
        line = re.sub(rf'^(?:{SKILL_CATEGORIES})\s*:\s*', '', line, flags=re.I)
        # Prose requirements are not single skill names. Keep only named technologies.
        if (len(line.split()) > 8 and not re.search(r'[,;|]', line)) or re.match(r'(?i)^(?:experience|knowledge|proficiency|familiarity|strong|must|ability|proficient)\b', line):
            output.extend(mentioned_skills(line))
        else:
            output.extend(re.split(r'[,;|•●▪]|\s+[·/]\s+|\s+and\s+', line))
    return unique(output)
