# Mini JARVIS Event — 60 GitHub Issues

Repository: https://github.com/ramkolipakula/mini-jarvis-event

Counts: Easy 20 · Medium 25 · Advanced 15

**How to use:** Create each GitHub issue using the matching Title and Description. Add the listed labels (create labels if needed). These are task descriptions for fixing controlled defects and hardening behavior; they do not instruct participants to add real credential theft or expose real user data.

## Suggested event workflow
- Assign each issue to one participant; mark it claimed when assigned.
- Require a branch and pull request linked to the issue.
- Run the mock test suite and review the diff before merging.
- Never place production API keys in issue bodies, source code, frontend environment variables, or participant CI.

## Issue 01 — [Easy] Fix empty message handling in chat endpoint

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/server.py`

### Description
Reject blank or whitespace-only chat messages with HTTP 422 unless a valid tool_execution payload is supplied. Keep confirmation-only requests working. Add tests for blank, whitespace, normal text, and confirmation requests.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 02 — [Easy] Validate conversation titles before saving

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/server.py`

### Description
Trim conversation titles, reject whitespace-only values, and enforce a reasonable maximum length. Add API tests for valid, empty, whitespace-only, and oversized titles.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 03 — [Easy] Standardize missing-conversation responses

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/server.py`

### Description
Make GET /api/conversations/{id} return a documented 404 response for unknown IDs. Add tests for existing and missing conversations and keep the response shape consistent.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 04 — [Easy] Return 404 when deleting an unknown conversation

- **Labels:** `backend`, `database`, `bug`
- **Affected files:** `backend/server.py`

### Description
Check the number of rows deleted and return 404 when the conversation does not exist instead of reporting success. Add tests for existing and unknown IDs.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 05 — [Easy] Restrict message roles to supported values

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/server.py`

### Description
Allow only user, assistant, and system roles in MessageRequest. Unsupported values must return 422 without writing to the database. Add model and endpoint tests.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 06 — [Easy] Reject empty conversation messages

- **Labels:** `backend`, `database`, `bug`
- **Affected files:** `backend/memory.py`

### Description
Prevent add_message() from persisting empty or whitespace-only content when called directly. Add tests that valid messages still save and invalid messages are rejected predictably.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 07 — [Easy] Define chronological order for conversation history

- **Labels:** `backend`, `database`, `bug`
- **Affected files:** `backend/server.py,backend/memory.py`

### Description
Return the most recent 100 messages in oldest-to-newest display order. Add a fixture with more than 100 messages and verify both the limit and ordering.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 08 — [Easy] Use timezone-aware UTC for calendar defaults

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/tools_calendar.py`

### Description
Replace deprecated naive UTC timestamp generation with an aware UTC datetime. Add a test for the serialized timeMin value and retain current default-window behavior.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 09 — [Easy] Validate Calendar result limits

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/tools_calendar.py`

### Description
Validate max_results within 1–50 and return a clear validation error for zero, negative, or oversized values. Add boundary tests.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 10 — [Easy] Validate GitHub result limits

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/tools_github.py`

### Description
Apply consistent positive bounds to issue, commit, and pull-request limits. Test defaults, valid boundaries, zero, negative, and oversized values.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 11 — [Easy] Validate GitHub pull-request state

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/tools_github.py`

### Description
Accept only open, closed, or all as the pull-request state. Invalid states should return a clear validation error without calling the provider.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 12 — [Easy] Filter pull requests before applying issue limits

- **Labels:** `backend`, `bug`
- **Affected files:** `backend/tools_github.py`

### Description
Ensure pull requests do not count toward the requested issue limit. Add mock data with mixed issues and pull requests and verify the result contains up to the requested number of actual issues.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 13 — [Easy] Handle commits with missing author metadata

- **Labels:** `backend`, `bug`
- **Affected files:** `backend/tools_github.py`

### Description
Avoid crashing when a commit has no author or an empty message. Use a safe display fallback and add mock tests for missing metadata.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 14 — [Easy] Handle missing email headers safely

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/tools_gmail.py`

### Description
Handle missing or malformed Subject, From, and Date headers without crashing. Use clear fallbacks and add tests for incomplete message metadata.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 15 — [Easy] Handle malformed email body data

- **Labels:** `backend`, `bug`
- **Affected files:** `backend/tools_gmail.py`

### Description
Safely handle absent body.data, malformed base64, and messages without a text/plain body. Add tests for nested multipart messages and malformed fixtures.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 16 — [Easy] Standardize unsupported Drive file-type errors

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/tools_drive.py`

### Description
Return a consistent structured error for unsupported binary or MIME types instead of an ad hoc success-like string. Test Google Docs, plain text, and unsupported file types.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 17 — [Easy] Separate liveness from readiness checks

- **Labels:** `backend`, `api`, `bug`
- **Affected files:** `backend/server.py`

### Description
Keep /api/health as a lightweight liveness endpoint and add a readiness endpoint for required configuration/database availability. Do not expose credentials or internal connection details.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 18 — [Easy] Show integration-status loading and errors

- **Labels:** `frontend`, `ui`, `bug`
- **Affected files:** `frontend/src/App.jsx`

### Description
Add visible loading and retry/error states to the integration status UI. Failed status calls must not silently leave a stale connected indicator.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 19 — [Easy] Add conversation-history loading and empty states

- **Labels:** `frontend`, `ui`, `bug`
- **Affected files:** `frontend/src/App.jsx`

### Description
Show distinct loading, empty, error, and retry states in the conversation sidebar. Preserve the existing visual style and avoid exposing raw server errors.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 20 — [Easy] Make the layout usable on mobile screens

- **Labels:** `frontend`, `ui`, `bug`
- **Affected files:** `frontend/src/App.css`

### Description
Add responsive behavior for narrow screens so the sidebar, chat area, and composer fit without horizontal overflow. Include a manual test checklist for phone and tablet widths.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 21 — [Medium] Add request timeouts and useful chat errors

- **Labels:** `frontend`, `api`, `bug`
- **Affected files:** `frontend/src/App.jsx`

### Description
Set sensible timeouts for chat and transcription requests. Distinguish timeout, network, and server errors while keeping the UI usable for retry.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 22 — [Medium] Prevent duplicate chat submissions

- **Labels:** `frontend`, `ui`, `bug`
- **Affected files:** `frontend/src/App.jsx`

### Description
Prevent rapid Enter presses or repeated clicks from submitting the same message multiple times. Apply the guard to text and voice paths and test duplicate submission attempts.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 23 — [Medium] Keep late responses in the correct conversation

- **Labels:** `frontend`, `bug`
- **Affected files:** `frontend/src/App.jsx`

### Description
Capture the target conversation ID when a request begins and ignore stale responses if the user switches chats before it completes. Add a test for out-of-order responses.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 24 — [Medium] Update conversation activity timestamps

- **Labels:** `backend`, `database`, `bug`
- **Affected files:** `backend/server.py,backend/memory.py`

### Description
Update the conversation activity timestamp when a message is added and order the sidebar by recent activity. Add a test proving an active older conversation moves to the top.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 25 — [Medium] Add a composite index for conversation history

- **Labels:** `database`, `performance`
- **Affected files:** `supabase_schema.sql`

### Description
Review the history query filter and sort pattern and add a suitable composite index if the schema supports it. Document an EXPLAIN-based check or a repeatable query-performance test.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 26 — [Medium] Handle database failure during new chat creation

- **Labels:** `backend`, `database`, `bug`
- **Affected files:** `backend/server.py,backend/memory.py`

### Description
Define consistent behavior when creating a conversation or saving its first message fails. Do not return a conversation ID that was not persisted; add database-offline tests.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 27 — [Medium] Make previous-conversation search bounded and deterministic

- **Labels:** `backend`, `database`, `performance`
- **Affected files:** `backend/memory.py`

### Description
Cap the number and length of search keywords and order results deterministically. Test punctuation, repeated terms, empty queries, and long input.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 28 — [Medium] Limit historical context sent to the LLM

- **Labels:** `backend`, `ai`, `performance`
- **Affected files:** `backend/brain.py`

### Description
Apply a configurable character/token budget to conversation history so old messages cannot crowd out the current request. Preserve recent context and test very long histories.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 29 — [Medium] Handle malformed LLM tool arguments

- **Labels:** `backend`, `ai`, `bug`
- **Affected files:** `backend/brain.py`

### Description
Validate JSON tool arguments and require an object with the registered schema. Handle invalid JSON, arrays, null, and missing required fields without crashing.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 30 — [Medium] Validate tool confirmation payloads

- **Labels:** `backend`, `api`, `security`
- **Affected files:** `backend/server.py,backend/brain.py`

### Description
Validate tool names and argument schemas against the registry before execution. Unknown tools or malformed arguments must be rejected without invoking providers.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 31 — [Medium] Enforce server-side approval for write tools

- **Labels:** `backend`, `ai`, `security`
- **Affected files:** `backend/brain.py,backend/tool_registry.py`

### Description
Ensure every side-effecting tool requires a server-validated approval record. Do not trust a client-supplied approved flag by itself; add tests for skipped and rejected approvals.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 32 — [Medium] Sanitize tool exceptions shown to users

- **Labels:** `backend`, `security`, `bug`
- **Affected files:** `backend/brain.py`

### Description
Log diagnostic details server-side with a correlation ID and return sanitized errors to the client/model. Tests must ensure tokens, request headers, and provider response bodies are not exposed.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 33 — [Medium] Paginate conversation listing

- **Labels:** `backend`, `api`, `performance`
- **Affected files:** `backend/server.py`

### Description
Add bounded pagination and stable ordering to GET /api/conversations. Test default page size, invalid limits, empty results, and subsequent pages.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 34 — [Medium] Support Drive search pagination

- **Labels:** `backend`, `api`, `feature`
- **Affected files:** `backend/tools_drive.py`

### Description
Handle nextPageToken or explicitly define a single-page contract. Validate page size and test multiple pages using the mock Drive provider.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 35 — [Medium] Implement a useful mock Drive provider

- **Labels:** `backend`, `testing`, `bug`
- **Affected files:** `backend/tests/mocks/providers.py`

### Description
Implement deterministic mock list/get/export behavior for Drive tools, including missing files and provider failures. Tests must not access the network or real Drive credentials.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 36 — [Medium] Make mock Gmail search respect its query

- **Labels:** `backend`, `testing`, `bug`
- **Affected files:** `backend/tests/mocks/providers.py`

### Description
Have the mock Gmail provider filter fixtures for the supported query subset instead of returning every message. Test matches, no matches, and malformed query handling.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 37 — [Medium] Make mock Calendar honor time filters

- **Labels:** `backend`, `testing`, `bug`
- **Affected files:** `backend/tests/mocks/providers.py`

### Description
Filter mock events using timeMin and timeMax and return stable ordering. Test events before, inside, after, and exactly on the boundaries.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 38 — [Medium] Make mock GitHub honor filters and limits

- **Labels:** `backend`, `testing`, `bug`
- **Affected files:** `backend/tests/mocks/providers.py`

### Description
Extend GitHub fixtures to support issue/PR state and result limits predictably. Test empty repositories, mixed issue/PR entries, and provider failures.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 39 — [Medium] Verify mock reset clears all test state

- **Labels:** `backend`, `testing`, `bug`
- **Affected files:** `backend/tests/mocks/providers.py`

### Description
Add tests proving reset clears failures and latency, restores fixtures, and resets generated IDs after both successful and failed operations.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 40 — [Medium] Make the network guard safe across test failures

- **Labels:** `backend`, `testing`, `bug`
- **Affected files:** `backend/tests/conftest.py`

### Description
Ensure network-blocking patches are always restored and do not unexpectedly break unrelated test tooling. Add a test that deliberately fails inside a fixture and verifies cleanup.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 41 — [Medium] Use the browser's actual recording MIME type

- **Labels:** `frontend`, `audio`, `bug`
- **Affected files:** `frontend/src/App.jsx`

### Description
Use MediaRecorder's selected MIME type and matching filename when uploading audio. Provide a supported fallback and test browser-specific MIME behavior.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 42 — [Medium] Stop audio visualization on every exit path

- **Labels:** `frontend`, `audio`, `bug`
- **Affected files:** `frontend/src/App.jsx`

### Description
Centralize visualizer animation cleanup when voice mode stops, recording fails, TTS ends, or the component unmounts. Verify no animation loop continues after cleanup.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 43 — [Medium] Gracefully handle unsupported audio APIs

- **Labels:** `frontend`, `audio`, `bug`
- **Affected files:** `frontend/src/App.jsx`

### Description
Feature-detect AudioContext, MediaRecorder, and getUserMedia. Show a clear message and keep text chat functional when voice features are unsupported.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 44 — [Medium] Validate transcription upload size and type

- **Labels:** `backend`, `api`, `security`
- **Affected files:** `backend/server.py`

### Description
Enforce a maximum upload size and accepted audio types using bounded reads. Return a clear 413/415 response and test oversized, empty, and invalid uploads.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 45 — [Medium] Use collision-safe temporary audio files

- **Labels:** `backend`, `api`, `security`
- **Affected files:** `backend/server.py`

### Description
Stop deriving a shared temporary path from the client filename. Use a secure temporary-file API, ensure cleanup on all paths, and test concurrent uploads and hostile filenames.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 46 — [Advanced] Scope conversations to an authenticated owner

- **Labels:** `backend`, `security`, `advanced`
- **Affected files:** `backend/server.py,supabase_schema.sql`

### Description
Design owner-scoped authorization for list, read, create, and delete endpoints. The current schema has optional user identity, so define the identity source and migration; add cross-user isolation tests before deployment.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 47 — [Advanced] Validate Google OAuth state against CSRF

- **Labels:** `backend`, `oauth`, `security`, `advanced`
- **Affected files:** `backend/oauth.py`

### Description
Persist a one-time random state bound to the initiating browser/session and validate it in the callback. Reject missing, mismatched, expired, or replayed state; tests must use mocked OAuth flows.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 48 — [Advanced] Add state validation to GitHub OAuth

- **Labels:** `backend`, `oauth`, `security`, `advanced`
- **Affected files:** `backend/oauth.py`

### Description
Use a cryptographically random, one-time state value and verify it on callback. Reject tampered and replayed callbacks and add tests without live GitHub requests.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 49 — [Advanced] Handle OAuth exchange timeouts and HTTP errors

- **Labels:** `backend`, `oauth`, `advanced`
- **Affected files:** `backend/oauth.py`

### Description
Set a timeout for the GitHub token exchange, check HTTP status before parsing JSON, and handle malformed provider responses safely. Add mocked success, timeout, 4xx, 5xx, and invalid-JSON tests.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 50 — [Advanced] Confirm token persistence before success redirect

- **Labels:** `backend`, `oauth`, `database`, `advanced`
- **Affected files:** `backend/oauth.py,backend/integrations.py`

### Description
Only redirect with an OAuth success status when token persistence has succeeded. Simulate database failures and verify the user receives a sanitized failure response.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 51 — [Advanced] Store integration tokens per user

- **Labels:** `backend`, `database`, `oauth`, `security`, `advanced`
- **Affected files:** `backend/integrations.py,supabase_schema.sql,backend/migrate.py`

### Description
Replace global uniqueness by integration name with a user-scoped relationship and composite uniqueness. Add migration and tests proving one user's Google/GitHub token cannot be returned for another user.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 52 — [Advanced] Refresh expired OAuth credentials safely

- **Labels:** `backend`, `oauth`, `advanced`
- **Affected files:** `backend/integrations.py,backend/tools_calendar.py,backend/tools_gmail.py,backend/tools_drive.py`

### Description
Centralize expiry-aware token refresh, refresh-token rotation, and revoked-token handling. Add deterministic tests for valid, expired, revoked, and refresh-failure cases.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 53 — [Advanced] Review and minimize GitHub OAuth scopes

- **Labels:** `backend`, `oauth`, `security`, `advanced`
- **Affected files:** `backend/oauth.py`

### Description
Audit actual feature requirements and request the narrowest practical GitHub permissions. Document any unavoidable broader scope and test the authorization URL's requested scopes.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 54 — [Advanced] Sanitize OAuth callback errors and logs

- **Labels:** `backend`, `oauth`, `security`, `advanced`
- **Affected files:** `backend/oauth.py`

### Description
Do not return raw provider exceptions or token-exchange response bodies to clients. Add structured server-side diagnostics and tests that codes, tokens, secrets, and raw response bodies are absent from responses.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 55 — [Advanced] Enforce global request and tool-argument limits

- **Labels:** `backend`, `api`, `security`, `advanced`
- **Affected files:** `backend/server.py,backend/brain.py`

### Description
Add configurable limits for chat text, tool argument size/depth, and request bodies. Return documented 413/422 errors and add tests for boundary and oversized payloads.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 56 — [Advanced] Make conversation deletion transactional and verifiable

- **Labels:** `backend`, `database`, `advanced`
- **Affected files:** `backend/server.py,backend/memory.py`

### Description
Use a clear transaction contract, verify affected rows, and ensure related messages are handled consistently. Test successful deletion, missing IDs, and rollback after a simulated database error.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 57 — [Advanced] Prevent replay of confirmed side-effecting tools

- **Labels:** `backend`, `ai`, `security`, `advanced`
- **Affected files:** `backend/server.py,backend/brain.py,backend/tool_registry.py`

### Description
Introduce a one-time server-side approval/action ID or idempotency key for write operations. Replays and double submissions must not create duplicate calendar events or other side effects.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 58 — [Advanced] Enforce tool permissions centrally

- **Labels:** `backend`, `security`, `advanced`
- **Affected files:** `backend/tool_registry.py,backend/brain.py`

### Description
Enforce registry permission metadata before dispatch based on authenticated provider connection and operation type. Add denial tests for disconnected integrations and insufficient permissions.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 59 — [Advanced] Add bounded tool timeouts and safe retries

- **Labels:** `backend`, `api`, `advanced`
- **Affected files:** `backend/brain.py,backend/tool_registry.py`

### Description
Define per-tool timeout and retry policies. Retry only safe read operations, avoid automatic retries of writes without idempotency protection, and test timeout and retry exhaustion with mocks.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---

## Issue 60 — [Advanced] Add offline end-to-end chat and tool-flow tests

- **Labels:** `backend`, `testing`, `advanced`
- **Affected files:** `backend/tests`

### Description
Add FastAPI TestClient coverage for normal chat, persisted history, approved/rejected tool calls, provider failures, and missing dependencies. Stub LLM/TTS and ensure the suite uses no live credentials or external network.

### Acceptance criteria
- Add or update automated tests for the reported behavior.
- Keep existing working chat/voice behavior and API contracts unless the issue explicitly changes them.
- Do not use real provider credentials in tests; use deterministic mocks.
- Include a short summary of the fix and test command/results in the pull request.

---
