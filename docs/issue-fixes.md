# Verification record for all 60 repository issues

All 60 implementation items have code changes. This records test evidence and remaining deployment checks; passing offline tests is not a claim of live-provider verification.

| Issue | Implementation and verification |
|---|---|
| 01 — [Easy] Fix empty message handling in chat endpoint | Blank text rejected; valid confirmation-only requests retained. `test_blank_chat`, `test_end_to_end_chat_history_and_approval`. |
| 02 — [Easy] Validate conversation titles before saving | Trimmed titles, nonblank and 120-character limit. `test_titles`, `test_missing_and_owned_conversation`. |
| 03 — [Easy] Standardize missing-conversation responses | Consistent owner-scoped 404. `test_missing_and_owned_conversation`. |
| 04 — [Easy] Return 404 when deleting an unknown conversation | Delete checks RETURNING row. `test_missing_and_owned_conversation`. |
| 05 — [Easy] Restrict message roles to supported values | Literal user/assistant/system roles. `test_bad_roles`. |
| 06 — [Easy] Reject empty conversation messages | Direct memory validation before connecting. `test_empty_direct_message`. |
| 07 — [Easy] Define chronological order for conversation history | Latest 100 reversed into chronological order, stable ID tie-breaker. `test_history_limit_order_activity_and_pagination`. |
| 08 — [Easy] Use timezone-aware UTC for calendar defaults | Aware UTC default. `test_calendar_utc`. |
| 09 — [Easy] Validate Calendar result limits | Calendar limit 1–50. `test_provider_limits`, `test_provider_boundaries`. |
| 10 — [Easy] Validate GitHub result limits | GitHub repository/issue/commit/PR limits 1–50. `test_provider_limits`, `test_provider_boundaries`. |
| 11 — [Easy] Validate GitHub pull-request state | PR state enum before provider dispatch. `test_github_metadata_and_filters`. |
| 12 — [Easy] Filter pull requests before applying issue limits | Count only actual issues. `test_github_metadata_and_filters`. |
| 13 — [Easy] Handle commits with missing author metadata | Author/message fallbacks. `test_github_metadata_and_filters`. |
| 14 — [Easy] Handle missing email headers safely | Malformed/missing headers ignored with fallbacks. `test_gmail_nested_malformed_and_queries`. |
| 15 — [Easy] Handle malformed email body data | Recursive plain-text decoding with safe base64 fallback. `test_gmail_nested_malformed_and_queries`. |
| 16 — [Easy] Standardize unsupported Drive file-type errors | Structured unsupported MIME error. `test_drive_pagination_read_and_failures`. |
| 17 — [Easy] Separate liveness from readiness checks | Public liveness and configuration/database readiness. `test_offline_and_health`. |
| 18 — [Easy] Show integration-status loading and errors | Loading/error/retry and cleared stale indicators. Frontend integration-state test. |
| 19 — [Easy] Add conversation-history loading and empty states | Sidebar loading/empty/error/retry; message fetch states. Frontend history-state test. |
| 20 — [Easy] Make the layout usable on mobile screens | Responsive sidebar, composer, modal and overflow rules. Manual viewport checklist below; real-browser verification blocked. |
| 21 — [Medium] Add request timeouts and useful chat errors | Explicit chat/transcription timeouts and classified errors. Frontend timeout/error tests. |
| 22 — [Medium] Prevent duplicate chat submissions | Synchronous ref guards shared by text and voice. Frontend repeated Enter test. |
| 23 — [Medium] Keep late responses in the correct conversation | Conversation generation IDs discard stale history/chat results. Frontend two race tests. |
| 24 — [Medium] Update conversation activity timestamps | Message insertion updates activity in the same transaction. `test_history_limit_order_activity_and_pagination`. |
| 25 — [Medium] Add a composite index for conversation history | Composite history index, plus activity index. Embedded PostgreSQL migration tests. |
| 26 — [Medium] Handle database failure during new chat creation | Create + first message atomic; unavailable DB returns 503. `test_atomic_create_and_delete_rollback`, `test_offline_and_health`. |
| 27 — [Medium] Make previous-conversation search bounded and deterministic | Deduplicate/cap keywords and lengths; stable ordering and owner scope. `test_search_and_history_budgets`, `test_cross_user_isolation`. |
| 28 — [Medium] Limit historical context sent to the LLM | Configurable history character budget; current input separately preserved. `test_search_and_history_budgets`. |
| 29 — [Medium] Handle malformed LLM tool arguments | JSON object/schema validation before dispatch. `test_malformed_llm_tool_args`, `test_schema_validation`. |
| 30 — [Medium] Validate tool confirmation payloads | Strict confirmation model and registry validation. `test_canceled_and_forged_approvals`. |
| 31 — [Medium] Enforce server-side approval for write tools | Durable server approval bound to owner/conversation/tool/arguments. `test_end_to_end_chat_history_and_approval`, `test_permission_denials_and_retry_policy`. |
| 32 — [Medium] Sanitize tool exceptions shown to users | Sanitized provider error with correlation ID and exception class only in logs. `test_oauth_sanitized_failures`, `test_drive_pagination_read_and_failures`. |
| 33 — [Medium] Paginate conversation listing | Bounded limit/offset and stable ordering, frontend Load more. `test_history_limit_order_activity_and_pagination`. |
| 34 — [Medium] Support Drive search pagination | Explicit page-token Drive contract. `test_drive_pagination_read_and_failures`. |
| 35 — [Medium] Implement a useful mock Drive provider | Mock Drive list/get/media/export/missing/failure. `test_drive_pagination_read_and_failures`. |
| 36 — [Medium] Make mock Gmail search respect its query | Mock Gmail text/from/subject/is:unread subset; invalid syntax rejected. `test_gmail_nested_malformed_and_queries`. |
| 37 — [Medium] Make mock Calendar honor time filters | Mock Calendar honors exclusive end/start window boundaries. `test_mock_calendar_boundaries_and_reset`. |
| 38 — [Medium] Make mock GitHub honor filters and limits | Mock GitHub states, branch filter, empty data, mixed PR/issues. `test_github_metadata_and_filters`. |
| 39 — [Medium] Verify mock reset clears all test state | Fixture/state/failure/latency/ID reset. `test_mock_calendar_boundaries_and_reset`, `test_mock_reset_restores_generated_ids_after_success_and_failure`. |
| 40 — [Medium] Make the network guard safe across test failures | Monkeypatch context restores socket class on teardown/failure. `test_network_patch_cleanup`. |
| 41 — [Medium] Use the browser's actual recording MIME type | MediaRecorder-selected MIME and matching filename. Frontend recording upload and MIME fallback tests. |
| 42 — [Medium] Stop audio visualization on every exit path | Shared cleanup for stream/node/animation/exit/error/unmount. Frontend audio lifecycle tests. |
| 43 — [Medium] Gracefully handle unsupported audio APIs | Audio API detection keeps text chat functional. Frontend unsupported-audio test. |
| 44 — [Medium] Validate transcription upload size and type | Bounded request and upload reads, size/type/empty validation. `test_upload_validation`. |
| 45 — [Medium] Use collision-safe temporary audio files | NamedTemporaryFile, no client-derived paths, finally cleanup. `test_upload_temp_cleanup_and_uniqueness`, `test_concurrent_uploads_never_share_paths`. |
| 46 — [Advanced] Scope conversations to an authenticated owner | Signed authenticated owner identity, scoped APIs/history; legacy quarantine. `test_cross_user_isolation`, `test_session_csrf_and_body_limits`. |
| 47 — [Advanced] Validate Google OAuth state against CSRF | Google random one-time state, owner/session binding and expiry. `test_oauth_success_replay_and_missing_state`, `test_oauth_state_binding_expiry_and_owners`. |
| 48 — [Advanced] Add state validation to GitHub OAuth | Same state validation for GitHub. Same OAuth tests. |
| 49 — [Advanced] Handle OAuth exchange timeouts and HTTP errors | GitHub timeout, HTTP status check, validated JSON/token. `test_oauth_sanitized_failures`. |
| 50 — [Advanced] Confirm token persistence before success redirect | Success redirect only after persistence. `test_oauth_sanitized_failures` database case. |
| 51 — [Advanced] Store integration tokens per user | Composite owner/integration uniqueness and owner-scoped token queries. `test_cross_user_isolation`, embedded PostgreSQL migration tests. |
| 52 — [Advanced] Refresh expired OAuth credentials safely | Shared expiry-aware Google credentials, refresh persistence/rotation, revoked vs transient behavior. `test_google_refresh`, `test_refresh_persistence_failure_never_returns_unsaved_credentials`. |
| 53 — [Advanced] Review and minimize GitHub OAuth scopes | No extra scopes for public GitHub reads; private repo scope is opt-in and documented. `test_github_minimal_scopes`. |
| 54 — [Advanced] Sanitize OAuth callback errors and logs | No raw OAuth body/code/token in errors or diagnostics. `test_oauth_sanitized_failures`. |
| 55 — [Advanced] Enforce global request and tool-argument limits | Bounded ASGI body buffering, chat text, argument bytes/depth/schema. `test_session_csrf_and_body_limits`, `test_depth_and_size`. |
| 56 — [Advanced] Make conversation deletion transactional and verifiable | Explicit commit/rollback with affected row verification and FK cascade. `test_atomic_create_and_delete_rollback`, embedded PostgreSQL tests. |
| 57 — [Advanced] Prevent replay of confirmed side-effecting tools | Atomic consume prevents replay/double submit across workers. `test_concurrent_approval_consumption`, end-to-end approval tests. |
| 58 — [Advanced] Enforce tool permissions centrally | Central provider and scope checks before dispatch. `test_permission_denials_and_retry_policy`. |
| 59 — [Advanced] Add bounded tool timeouts and safe retries | Bounded executor/HTTP timeouts; safe read retry; no write/timeout replay. `test_tool_timeout_no_overlap`, `test_permission_denials_and_retry_policy`. |
| 60 — [Advanced] Add offline end-to-end chat and tool-flow tests | Offline TestClient normal/persisted chat, confirmations/cancel/replay, provider/config/DB failures. End-to-end tests plus CI. |

## Manual phone/tablet checklist (not yet executed)

A real Chromium run was attempted but the browser binary was absent and its download failed with a truncated archive. JSDOM does not verify CSS layout.

- At 320, 375, 768 and 1280 pixels wide, confirm no horizontal page overflow.
- Open a long conversation title and a long unbroken message; composer and send controls remain visible.
- At phone widths, scroll the compact history region separately from messages.
- Open integrations and a tool confirmation; scroll long content without clipping buttons.
- Verify microphone permission denial, recording start/stop, voice exit and continuous-mode stop on Chrome and Safari with real microphones.
- Confirm TTS completion/error stops the animation and exiting voice mode never restarts playback from a late response.

## Recorded results

- `python -m pytest -q`: 74 passed.
- `npm test --prefix frontend`: 15 passed (13 UI tests, 2 PostgreSQL migration tests).
- `npm run lint --prefix frontend`: passed without diagnostics.
- `npm run build --prefix frontend`: passed.
- `git diff --check`: passed.

## Verification boundaries

- API → owner-scoped data → response: deterministic SQLite-backed API tests, plus separate real PostgreSQL-engine SQL checks using PGlite.
- UI → API contract → rendered result: mocked Vitest/Testing Library interaction tests.
- Fresh and legacy migration: PGlite runs both migrations twice, verifies composite ownership, approval consumption, rollback, cascade and indexes.
- Hosted PostgreSQL role grants/RLS, secure cross-site cookies, OAuth consent, real Groq/STT/TTS and microphone hardware need a deployment smoke test with configured accounts.
- Authentication and migration are required before deploying this branch. See the README; no production data or deployment was changed by this work.
