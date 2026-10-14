# Mini JARVIS 🎙️

A voice-first AI assistant designed to feel like a real cinematic AI. It features an interactive web interface with a custom-built Web Audio API visualizer, PostgreSQL (Supabase) long-term memory persistence, and lightning-fast text-to-speech using ElevenLabs and Groq.

## Features ✨
- **Voice Mode**: A dedicated, distraction-free UI with a real-time audio visualizer that syncs perfectly with JARVIS's voice.
- **Continuous Conversation**: Talk to JARVIS completely hands-free.
- **Contextual Memory**: Powered by Supabase. JARVIS remembers what you said in previous conversations.
- **Ultra-Low Latency**: Uses Groq Whisper (STT) and Groq LLaMA/GPT (LLM) for blazing-fast inference.

## Local Development 💻

### 1. Backend (Python/FastAPI)
The backend manages the database connections, memory, Groq integrations, and the ElevenLabs TTS API.

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

**Environment Variables**:
Create a `.env` file in the `backend/` directory:
```env
GROQ_API_KEY=your_groq_key
TTS_API_KEY=your_elevenlabs_key
DATABASE_URL="postgresql://postgres.xxx:password@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
```

Start the backend:
```bash
python server.py
# (Runs on http://localhost:8000)
```

### 2. Frontend (React/Vite)
The frontend provides the sleek dark-mode UI and Web Audio API graph routing for the visualizer.

```bash
cd frontend
npm install
npm run dev
# (Runs on http://localhost:5173)
```

---

## Deployment Instructions 🚀

### 1. Deploy the Backend (Render)
1. Push this repository to GitHub.
2. Create a new **Web Service** on [Render](https://render.com/).
3. Settings:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables: `GROQ_API_KEY`, `TTS_API_KEY`, and `DATABASE_URL`.
5. Deploy and copy the live URL (e.g., `https://jarvis-backend.onrender.com`).

### 2. Deploy the Frontend (Vercel)
1. Go to [Vercel](https://vercel.com/) and create a **New Project**.
2. Import the same GitHub repository.
3. Settings:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
4. Add Environment Variable:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://jarvis-backend.onrender.com/api` *(Make sure to use your Render URL + /api)*
5. Deploy!

## Required upgrade setup

This version fixes the 60 items in `mini_jarvis_event_60_github_issues.md`.
See [the issue-by-issue verification record](docs/issue-fixes.md).

1. Back up your database, then run `python backend/migrate.py` from the repository root with `DATABASE_URL` set. The migration is transactional and repeatable. Use a server database role with access to the tables; browser/PostgREST access is denied by RLS.
2. Set `SESSION_SECRET` to at least 32 random characters (for example, generate locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"`). Never put it in frontend variables.
3. Run `python backend/provision_user.py` locally for each user. Merge the printed hash-to-UUID entry into the server's `AUTH_USERS` JSON object. Give each person their own generated access code; do not commit codes or configuration. A code is a password-equivalent bearer secret. This is provisioned-user sign-in, not public self-registration.
4. Set `FRONTEND_URL` to your exact frontend origin. For local HTTP development only, set `COOKIE_SECURE=false`; production defaults to secure HttpOnly cookies (`SameSite=None`). Keep `VITE_API_URL` pointing to your backend `/api`. Cross-site cookies must be permitted by the browser; for browsers blocking them, serve frontend/API on the same site through a reverse proxy. Never use frontend API keys to bypass authentication.
5. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` and GitHub OAuth client credentials. Register the backend `/api/auth/google/callback` and `/api/auth/github/callback` URLs in the providers. Sign in before connecting integrations.
6. Reconnect integrations after migration. Old global tokens have no owner and are inaccessible. Old conversations also remain quarantined until an administrator explicitly assigns each conversation's `user_id` to its verified owner's UUID. No automatic ownership inference or data deletion is performed.

Sessions expire after 24 hours. Rotating `SESSION_SECRET` invalidates all sessions and pending OAuth browser bindings. Removing an access-code hash prevents new sessions; existing signed sessions remain valid until expiry or key rotation. Keep the server-only database connection credentials private.

GitHub public repository reads request no additional scopes. Set `GITHUB_PRIVATE_REPOS=true` only if private repositories are required: OAuth's `repo` scope also grants write access, even though this application registers only GitHub read tools. Google requests Calendar event-write/read, Gmail-read, and Drive-read scopes; Gmail send is not requested.

`GROQ_MODEL` defaults to `llama-3.3-70b-versatile`; configure an available model for your Groq account. Groq and the database are required for readiness. TTS is optional; failure leaves text chat usable. The CLI (`backend/main.py`) prompts for the same access code and requires a database.

### API changes and limits

- All application APIs require a signed session except `/api/health`, `/api/ready`, and `/api/session/login`. Login accepts `{"access_code":"..."}`. Requests use credentials/cookies; client-supplied user IDs are never accepted.
- Missing or inaccessible conversations return `404 {"detail":"Conversation not found"}`. Validation uses HTTP 422; oversized bodies/uploads use 413; unsupported audio uses 415; unavailable database/configuration uses 503. Provider failures are sanitized.
- Conversation listing remains an array and accepts `limit=1..100` (default 50) and `offset=0..100000`, ordered by activity and ID. History returns the latest 100 messages in chronological order.
- `MAX_CHAT_CHARS` defaults to 10000, `MAX_BODY_BYTES` to 65536, `MAX_AUDIO_BYTES` to 20 MiB, `HISTORY_CHAR_BUDGET` to 12000, `MAX_ARGUMENT_BYTES` to 16384 and `MAX_ARGUMENT_DEPTH` to 8. Audio MIME types: webm, ogg, mp4, mpeg, wav/x-wav. Client filenames are never used as disk paths.
- Write confirmation payloads must return the server's `action_id`, unchanged `tool_name`/`arguments`, `conversation_id`, and strict boolean `approved`. Approvals expire after 10 minutes and are consumed atomically; replay returns 409. A write is never automatically retried. If a provider times out after accepting a write, verify its outcome before requesting another action.
- Read tools have a 15-second per-attempt ceiling and at most one retry after provider failures. Timed-out worker threads cannot be forcibly killed; they retain one of eight bounded worker slots until the provider returns. No overlapping timeout retries are started. Provider HTTP calls also have explicit timeouts.
- Drive search returns `files`, `next_page_token`, and `summary`; pass the token as `page_token` to continue. `max_results` is the page size (1–50). Unsupported document types return a structured `error` object.

### Offline verification

From the repository root:

```bash
pip install -r backend/requirements.txt -r backend/requirements-test.txt
python -m pytest -q
npm ci --prefix frontend
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```

No production credentials are used. Backend tests stub providers and block external socket connections, use SQLite as a transactional API-test adapter, and separately test both fresh and legacy SQL migrations in embedded PostgreSQL (PGlite). Frontend tests cover request races, duplicate submits, loading/retry states, and audio lifecycles. CI runs the same checks. Real OAuth consent, microphone hardware, and hosted Supabase/Render/Vercel wiring still require a configured deployment smoke test.
