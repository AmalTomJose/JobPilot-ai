"""Extract MIME bodies without executing HTML or downloading links/attachments."""
import base64
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit


class BodyError(ValueError):
    pass


class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.hidden = 0
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'head'}:
            self.hidden += 1
        if self.hidden:
            return
        if tag in {'p', 'div', 'br', 'li', 'tr', 'h1', 'h2', 'h3', 'h4'}:
            self.output.append('\n')
        if tag == 'a':
            href = dict(attrs).get('href', '')
            try:
                url = urlsplit(href)
                self.links.append(href if url.scheme in {'http', 'https'} and url.hostname and not url.username else '')
            except ValueError:
                self.links.append('')

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'head'} and self.hidden:
            self.hidden -= 1
            return
        if self.hidden:
            return
        if tag == 'a' and self.links:
            href = self.links.pop()
            if href:
                self.output.append(' ' + href)
        if tag in {'p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4'}:
            self.output.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.output.append(data)


def decode_body(part):
    body = part.get('body', {})
    if body.get('attachmentId') and not body.get('data'):
        raise BodyError('The email body requires an attachment download. Paste the job text manually.')
    data = body.get('data', '')
    try:
        decoded = base64.b64decode(data + '=' * (-len(data) % 4), altchars=b'-_', validate=True)
        content_type = next((header.get('value', '') for header in part.get('headers', []) if header.get('name', '').lower() == 'content-type'), '')
        charset = re.search(r'charset=["\']?([^;\s"\']+)', content_type, re.I)
        text = decoded.decode(charset.group(1) if charset else 'utf-8', errors='strict')
    except (ValueError, UnicodeError, LookupError):
        raise BodyError('The email text encoding could not be read. Paste the job text manually.') from None
    if len(text) > 100000:
        raise BodyError('This email is too long for extraction. Paste one opening at a time.')
    return text


def body_text(part, depth=0):
    if depth > 20:
        raise BodyError('This email has an unsupported nested format.')
    if part.get('filename'):
        return ''
    mime = part.get('mimeType', '').lower()
    if mime.startswith('multipart/'):
        children = part.get('parts', [])
        if mime == 'multipart/alternative':
            # Use one representation, never concatenate plain and HTML duplicates.
            plain = [child for child in children if child.get('mimeType') == 'text/plain' and not child.get('filename')]
            if plain:
                text = body_text(plain[0], depth+1)
                if text.strip():
                    return text
            children = [child for child in children if child.get('mimeType') == 'text/html'] or children[:1]
        return '\n'.join(body_text(child, depth+1) for child in children)
    if mime == 'text/plain':
        return decode_body(part)
    if mime == 'text/html':
        parser = HTMLText()
        parser.feed(decode_body(part))
        return re.sub(r'\n{3,}', '\n\n', ''.join(parser.output)).strip()
    return ''


def extract_message(payload):
    text = body_text(payload).strip()
    if not text:
        raise BodyError('No supported email body was found. Paste the job text manually.')
    subject = next((h.get('value', '') for h in payload.get('headers', []) if h.get('name', '').lower() == 'subject'), '')
    result = f'Subject: {subject}\n{text}' if subject else text
    if len(result) > 100000:
        raise BodyError('This email is too long for extraction. Paste one opening at a time.')
    return result
