"""Explainable exact/alias skill coverage. No inference from titles or prose."""
import re
import unicodedata

MATCHER_VERSION = 'skill-coverage-v1'
ALIASES = {
    'postgres': 'postgresql', 'react.js': 'react', 'reactjs': 'react',
    'nodejs': 'node.js', 'node js': 'node.js', 'nextjs': 'next.js',
    'next js': 'next.js', 'js': 'javascript', 'ts': 'typescript',
    'c sharp': 'c#', 'csharp': 'c#', 'cplusplus': 'c++',
    'amazon web services': 'aws', 'ms sql server': 'sql server',
    'microsoft sql server': 'sql server', 'mssql': 'sql server',
    'rest api': 'rest apis', 'restful api': 'rest apis', 'restful apis': 'rest apis',
}


def skill_key(value):
    value = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', value)).strip().casefold()
    return ALIASES.get(value, value)


def skill_map(values):
    result = {}
    for value in values:
        key = skill_key(value)
        if key:
            result.setdefault(key, value.strip())
    return result


def match_skills(profile_skills, job_skills):
    profile, job = skill_map(profile_skills), skill_map(job_skills)
    reason = 'profile_skills_missing' if not profile else 'job_skills_missing' if not job else None
    if reason:
        return dict(score=None, matched_skills=[], missing_skills=[], reason=reason)
    matched = [dict(job_skill=label, profile_skill=profile[key]) for key, label in job.items() if key in profile]
    missing = [label for key, label in job.items() if key not in profile]
    return dict(score=round(100 * len(matched) / len(job), 1), matched_skills=matched, missing_skills=missing, reason=None)
