"""Apply the base schema and repeatable upgrade in one transaction."""
import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

def main():
    load_dotenv()
    root = Path(__file__).resolve().parent
    with psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute((root.parent / 'supabase_schema.sql').read_text())
            for path in sorted((root / 'migrations').glob('*.sql')):
                cur.execute(path.read_text())
    conn.close()
    print('Migration completed.')

if __name__ == '__main__': main()
