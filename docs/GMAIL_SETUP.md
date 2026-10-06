# Gmail setup — Sprint 6

## 1. Create your Google OAuth client

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select/create a project.
2. Enable **Gmail API** for that project.
3. Configure Google Auth Platform branding, audience, and data access. For a personal learning app, use external testing and add your Gmail address as a test user.
4. Add the scope `https://www.googleapis.com/auth/gmail.readonly`.
5. Create an OAuth client with application type **Web application**.
6. Add this exact authorized redirect URI: `http://localhost:8000/email/gmail/callback`.
7. Copy the client ID and client secret into your local backend environment file. Do not paste secrets into chat or commit them.

The read-only scope permits mailbox reading; Google does not offer a per-label version of it. JobPilot applies your chosen label and date filter itself. It cannot send, delete, or mark email as read with this scope. See [Google's scope reference](https://developers.google.com/workspace/gmail/api/auth/scopes) and [web-server OAuth guide](https://developers.google.com/identity/protocols/oauth2/web-server).

This scope is restricted. A public production release has additional Google verification requirements; this local learning setup does not complete those requirements. External testing grants can expire and require reconnection. Consult the current Google console and linked OAuth guide when changing publication status.

## 2. Configure JobPilot

Add these to `backend/.env` locally:

```dotenv
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_TOKEN_ENCRYPTION_KEY=your-generated-key
GMAIL_REDIRECT_URI=http://localhost:8000/email/gmail/callback
FRONTEND_URL=http://localhost:5173
```

Generate the encryption key once, from `backend/`:

```sh
./venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Keep this key separate from the database and JWT secret. The API and worker must use the same key. Losing/changing it makes existing saved Gmail credentials unreadable; reconnect those accounts. Tokens are encrypted; imported message content is ordinary database data and needs normal database protection/backups.

Use **localhost consistently** for the browser, API, and callback. Set `frontend/.env` to `VITE_API_URL=http://localhost:8000`. Mixing localhost and 127.0.0.1 breaks the browser-bound OAuth cookie. The configured frontend origin must also be in `CORS_ORIGINS`.

For deployment use HTTPS, a same-site frontend/API arrangement, and an exact registered callback URL. Do not enable request-body logging for token calls. JobPilot removes callback query parameters from Uvicorn access logs; configure any reverse proxy to avoid logging callback query strings too.

## 3. Apply migration and restart

From `backend/`:

```sh
./venv/bin/python -m alembic upgrade head
./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Restart your existing backend instead of starting a second process on the same port. Restart Vite after changing its environment.

## 4. Connect and import

1. In Gmail, create a custom label such as **Job Alerts**. Apply it to job notification emails. You can create a Gmail filter to label future matching mail.
2. In JobPilot **Settings → Gmail job alerts**, select **Connect Gmail**.
3. Complete Google's consent screen using your test-user account.
4. Back in Settings, choose the custom label and import start date. The date starts at midnight UTC.
5. Save import settings, then choose **Sync now**.
6. Each batch lists up to 10 emails. Use **Continue sync** while another page remains.
7. Open **Job inbox → Discovered jobs**, review an opening and choose **Approve and add to jobs**. For older imports, use **Discover from existing emails**. Add the full description through the existing capture/paste workflow when needed.
8. Run matching from Matches after saving jobs.

The first version supports one connected Gmail mailbox and one selected custom label per JobPilot user. Disconnect before changing mailbox accounts. Discovered openings, existing drafts and jobs remain after disconnect.

## 5. Automatic syncing

From another terminal, in `backend/`:

```sh
./venv/bin/python -m app.workers.gmail_worker
```

Then enable **automatic syncing** in Settings and save. The worker checks for due accounts every 30 seconds. A completed scan is scheduled again after 15 minutes; a scan with more pages continues after 5 minutes. Provider failures back off, up to six hours. Revoked access requires reconnection.

To process due accounts once and exit:

```sh
./venv/bin/python -m app.workers.gmail_worker --once
```

The checkbox alone does not launch the worker. Keep that process running for automatic imports. Without credentials, the worker exits with configuration instructions. Manual sync works without a worker.

## Limitations and recovery

- This version rescans the selected date range, remembering message IDs to prevent duplicate imports. It does not use Gmail push notifications or history IDs. Large date ranges take more requests and multiple batches; start with a recent range.
- A scan freezes its upper date boundary and retains its page token. A failed page rolls back its imports and checkpoint. A rejected cursor starts a fresh scan safely.
- Plain text is preferred; HTML is converted to text while retaining ordinary application links. Scripts, tracking images, links, and attachments are never fetched.
- Large responses (over 2 MB), body text over 100,000 characters, invalid encoding, attachment-only bodies, and multi-opening digests have limits. Unsupported body formats receive a review warning; a provider response over the limit fails the batch. Remove an oversized message from the selected label to continue, then paste its relevant opening manually.
- Recognized direct links in multi-opening emails become separate discovered openings. Unknown details remain empty. Unsupported links require opening the original email and importing a description manually.
- A deleted message or a message whose label changed between listing and retrieval is skipped.
- Syncing preserves the source MIME payload and decoded text, then creates separate discovered openings. It no longer automatically creates editable drafts. You approve jobs manually; parsing still uses rules, not AI.
- Disconnect attempts Google's token revocation and always removes local credentials and stops scheduling. If revocation fails, remove JobPilot access in your Google Account permissions.
- Live Google consent/refresh cannot be verified until your own client is configured. Automated tests use synthetic mail and mocked Google responses.


### Source views

Use **Job discovery → LinkedIn / Naukri / Indeed / Other sources** to review individual openings. Open the website, paste or receive a permitted extension preview, then review and approve. If the URL changed, choose the original opening in **Attach to a discovered opening** before saving. Approved and dismissed openings remain out of Pending when recognized on later imports. Gmail messages are not deleted.
