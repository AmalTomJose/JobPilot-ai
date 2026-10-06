"""Classify job websites and recognize explicit provider job IDs; no network."""
import re
from urllib.parse import urlsplit, parse_qs

SOURCES = ('linkedin', 'naukri', 'indeed', 'other')
INDEED_DOMAINS = ('indeed.com', 'indeed.co.in', 'indeed.co.uk', 'indeed.ca', 'indeed.com.au')


def source_site(value):
    try:
        url = urlsplit(value or '')
        if url.scheme not in {'http', 'https'} or url.username or url.password:
            return 'other'
        host = (url.hostname or '').lower()
        for site, domains in (('linkedin', ('linkedin.com',)), ('naukri', ('naukri.com',)), ('indeed', INDEED_DOMAINS)):
            if any(host == domain or host.endswith('.' + domain) for domain in domains):
                return site
    except ValueError:
        pass
    return 'other'


def provider_job_id(value):
    site = source_site(value)
    if site not in {'naukri', 'indeed'}:
        return None
    url = urlsplit(value or '')
    if site == 'naukri':
        match = re.fullmatch(r'/(?:jd/)?job-listings-[^/]+-(\d{12})/?', url.path, re.I)
        return ('naukri', match[1]) if match else None
    if site == 'indeed' and url.path.rstrip('/') in {'/viewjob', '/rc/clk', '/pagead/clk'}:
        keys = parse_qs(url.query).get('jk', [])
        if len(keys) == 1 and re.fullmatch(r'[a-fA-F0-9]{16}', keys[0]):
            return ('indeed', keys[0].lower())
    return None
