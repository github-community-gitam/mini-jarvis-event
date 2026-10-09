import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("No DATABASE_URL found")
    exit(1)

schema_sql = """
-- Create user_integrations table for OAuth tokens
CREATE TABLE IF NOT EXISTS user_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_name TEXT NOT NULL, -- 'google_calendar', 'github', etc.
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    scopes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(integration_name)
);

-- Note: We assume update_updated_at_column function already exists from previous migrations
DO $$ 
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_integrations_updated_at') THEN
    CREATE TRIGGER update_user_integrations_updated_at
    BEFORE UPDATE ON user_integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
  END IF;
END $$;
"""

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(schema_sql)
        print("Migration successful: user_integrations table created.")
except Exception as e:
    print(f"Migration error: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
