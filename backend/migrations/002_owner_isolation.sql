-- Legacy rows remain quarantined (NULL owner), invisible to all signed-in users.
-- Assign conversations to a verified owner explicitly; reconnect old integrations.
ALTER TABLE user_integrations ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE user_integrations DROP CONSTRAINT IF EXISTS user_integrations_integration_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS user_integrations_owner_name ON user_integrations(user_id, integration_name);
CREATE INDEX IF NOT EXISTS idx_messages_history ON messages(conversation_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_activity ON conversations(user_id, updated_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS pending_actions (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    binding TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pending_expiry ON pending_actions(expires_at);
-- These tables are server-only. Do not expose integration credentials via PostgREST.
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_actions ENABLE ROW LEVEL SECURITY;
