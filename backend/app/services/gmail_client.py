"""Bounded Google requests. Provider details and credentials never enter API errors."""
from urllib.parse import urlencode, quote, urlsplit
import base64
import hashlib
import httpx
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'


class GmailError(Exception):
    def __init__(self, message, reconnect=False, invalid_cursor=False, missing=False):
        super().__init__(message)
        self.reconnect = reconnect
        self.invalid_cursor = invalid_cursor
        self.missing = missing


def configured():
    try:
        Fernet(settings.GMAIL_TOKEN_ENCRYPTION_KEY.encode())
        for value in (settings.GMAIL_REDIRECT_URI, settings.FRONTEND_URL):
            url = urlsplit(value)
            if not url.hostname or url.username or url.password or url.query or url.fragment:
                return False
            if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in {'localhost', '127.0.0.1'}):
                return False
        if urlsplit(settings.GMAIL_REDIRECT_URI).path != '/email/gmail/callback' or urlsplit(settings.FRONTEND_URL).path not in {'', '/'}:
            return False
        return bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET)
    except (ValueError, TypeError):
        return False


def encrypt(value):
    return Fernet(settings.GMAIL_TOKEN_ENCRYPTION_KEY.encode()).encrypt(value.encode()).decode()


def decrypt(value):
    try:
        return Fernet(settings.GMAIL_TOKEN_ENCRYPTION_KEY.encode()).decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, AttributeError):
        raise GmailError('The saved connection cannot be opened. Reconnect Gmail.', reconnect=True) from None


class GmailClient:
    def request(self, method, url, **kwargs):
        try:
            with httpx.Client(timeout=8, follow_redirects=False) as client:
                with client.stream(method, url, **kwargs) as response:
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > 2_000_000:
                            raise GmailError('A Gmail response is too large to process safely.')
                    import json
                    try:
                        data = json.loads(content) if content else {}
                    except (ValueError, UnicodeError):
                        raise GmailError('Gmail returned an unreadable response. Try again later.') from None
                    if not isinstance(data, dict):
                        raise GmailError('Gmail returned an unreadable response. Try again later.')
                    if response.status_code >= 400:
                        error = data.get('error')
                        if error == 'invalid_grant' or response.status_code == 401:
                            raise GmailError('Gmail access expired or was revoked. Reconnect Gmail.', reconnect=True)
                        if response.status_code == 400:
                            raise GmailError('Gmail rejected the request. Check the connection and selected label.', invalid_cursor=True)
                        if response.status_code == 404:
                            raise GmailError('The selected Gmail message or label is no longer available.', missing=True)
                        raise GmailError('Gmail is unavailable or has limited requests. Try again later.')
                    return data
        except httpx.HTTPError:
            raise GmailError('Could not reach Gmail. Try again later.') from None

    def authorization_url(self, state, verifier):
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(dict(
            client_id=settings.GMAIL_CLIENT_ID, redirect_uri=settings.GMAIL_REDIRECT_URI,
            response_type='code', scope=SCOPE, state=state, access_type='offline',
            prompt='consent', code_challenge=challenge, code_challenge_method='S256'))

    def exchange(self, code, verifier):
        return self.request('POST', 'https://oauth2.googleapis.com/token', data=dict(
            client_id=settings.GMAIL_CLIENT_ID, client_secret=settings.GMAIL_CLIENT_SECRET,
            redirect_uri=settings.GMAIL_REDIRECT_URI, grant_type='authorization_code', code=code, code_verifier=verifier))

    def refresh(self, refresh_token):
        data = self.request('POST', 'https://oauth2.googleapis.com/token', data=dict(
            client_id=settings.GMAIL_CLIENT_ID, client_secret=settings.GMAIL_CLIENT_SECRET,
            grant_type='refresh_token', refresh_token=refresh_token))
        if not data.get('access_token'):
            raise GmailError('Gmail did not provide access. Reconnect Gmail.', reconnect=True)
        return data['access_token']

    def get(self, path, token, **params):
        return self.request('GET', 'https://gmail.googleapis.com/gmail/v1/users/me/' + path,
                            headers={'Authorization': f'Bearer {token}'}, params=params)

    def profile(self, token):
        return self.get('profile', token)

    def labels(self, token):
        return self.get('labels', token).get('labels', [])

    def messages(self, token, label, since, before, page_token=None):
        params = dict(labelIds=label, q=f'after:{since} before:{before}', maxResults=10, includeSpamTrash='false')
        if page_token:
            params['pageToken'] = page_token
        return self.get('messages', token, **params)

    def message(self, token, message_id):
        return self.get('messages/' + quote(message_id, safe=''), token, format='full')

    def revoke(self, token):
        # Revocation can have an empty success body.
        return self.request('POST', 'https://oauth2.googleapis.com/revoke', data={'token': token})
