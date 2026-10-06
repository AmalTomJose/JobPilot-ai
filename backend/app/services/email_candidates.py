"""Conservative extraction of individual job links. Never follow email redirects."""
from dataclasses import dataclass
from html.parser import HTMLParser
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit
from app.services.email_text import decode_body, BodyError
from app.services.job_parser import ROLE_WORD
from app.services.job_sources import source_site, provider_job_id

MAX_CANDIDATES = 50


def job_link(value):
    """Return a safe direct job URL or None; unrelated email links are excluded."""
    try:
        url = urlsplit(value.strip())
        host = (url.hostname or '').lower()
        if url.scheme not in {'http', 'https'} or not host or url.username or url.password or url.port not in {None, 80, 443}:
            return None
        if any(char.isspace() or ord(char) < 32 for char in value) or len(value) > 2048:
            return None
        if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
            return None
        try:
            ipaddress.ip_address(host)
            return None  # Job links are hostnames, never literal addresses.
        except ValueError:
            pass
        if host == 'linkedin.com' or host.endswith('.linkedin.com'):
            match = re.fullmatch(r'/(?:comm/)?jobs/view/(?:[^/]*-)?(\d+)/?', url.path)
            return f'https://www.linkedin.com/jobs/view/{match[1]}' if match else None
        provider = provider_job_id(value)
        if source_site(value) == 'naukri':
            return urlunsplit(('https', 'www.naukri.com', url.path.rstrip('/'), '', '')) if provider else None
        if source_site(value) == 'indeed':
            return urlunsplit(('https', host, '/viewjob', 'jk=' + provider[1], '')) if provider else None
        if host in {'boards.greenhouse.io', 'job-boards.greenhouse.io'}:
            if not re.fullmatch(r'/[\w-]+/jobs/\d+/?', url.path):
                return None
            return urlunsplit(('https', host, url.path.rstrip('/'), '', ''))
        if host in {'jobs.lever.co', 'jobs.eu.lever.co'}:
            if not re.fullmatch(r'/[\w-]+/[a-fA-F0-9-]{36}(?:/apply)?/?', url.path):
                return None
            path = url.path.rstrip('/').removesuffix('/apply')
            return urlunsplit(('https', host, path, '', ''))
        # Unsupported public job links can still be opened manually; never fetched.
        if not re.search(r'/(?:jobs?|careers?|positions?)/[^/]+', url.path, re.I):
            return None
        if re.search(r'(?i)(unsubscribe|preferences|search|alerts)', url.path):
            return None
        return urlunsplit((url.scheme, host, url.path, url.query, ''))
    except (ValueError, UnicodeError):
        return None


@dataclass
class Opening:
    title: str | None
    job_url: str


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current = None
        self.text = []
        self.items = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'head'}:
            self.hidden += 1
        if not self.hidden and tag == 'a':
            self.current = dict(attrs).get('href', '')
            self.text = []

    def handle_data(self, data):
        if self.current is not None and not self.hidden:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'head'} and self.hidden:
            self.hidden -= 1
        if tag == 'a' and self.current is not None:
            link = job_link(self.current)
            label = re.sub(r'\s+', ' ', ' '.join(self.text)).strip()
            if link:
                title = label if ROLE_WORD.search(label) and len(label) <= 255 and not re.search(r'(?i)\b(see all|view all|new jobs|job alert)\b', label) else None
                self.items.append(Opening(title, link))
            self.current = None


def html_parts(part, depth=0):
    if depth > 20 or part.get('filename'):
        return
    if part.get('mimeType', '').lower() == 'text/html':
        yield decode_body(part)
    for child in part.get('parts', []):
        yield from html_parts(child, depth+1)


def extract_openings(payload, raw_text=None):
    """Read HTML even when MIME has a preferred plain-text alternative."""
    found = {}
    try:
        for html in html_parts(payload):
            parser = Anchors()
            parser.feed(html)
            for item in parser.items:
                if item.job_url not in found or not found[item.job_url].title:
                    found[item.job_url] = item
    except BodyError:
        pass
    # Plain-text messages sometimes carry title and link on the same line.
    for line in (raw_text or '').splitlines():
        for match in re.finditer(r'https?://[^\s<>"\']+', line):
            link = job_link(match[0].rstrip(').,'))
            if link and link not in found:
                label = line[:match.start()].strip(' :-')
                title = label if ROLE_WORD.search(label) and len(label) <= 255 else None
                found[link] = Opening(title, link)
    return list(found.values())[:MAX_CANDIDATES]
