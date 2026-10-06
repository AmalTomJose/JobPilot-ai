"""Build links to Gmail using stored identifiers; never fetch email here."""
from urllib.parse import quote


def original_email_url(message):
    base = 'https://mail.google.com/mail/?authuser=' + quote(message.mailbox_email, safe='')
    for header in (message.payload_data or {}).get('headers', []):
        if header.get('name', '').lower() == 'message-id':
            value = header.get('value', '').strip().strip('<>')
            if value and len(value) <= 998 and not any(char.isspace() for char in value):
                return base + '#search/' + quote('in:anywhere rfc822msgid:' + value, safe='')
    # Older imports may lack the RFC Message-ID header. Gmail's message route
    # is a best-effort fallback; its web UI routes are not an API contract.
    return base + '#all/' + quote(message.provider_message_id, safe='')
