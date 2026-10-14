import re
from contextlib import contextmanager
from fastapi import HTTPException
from database import get_db_connection
from security import owner_id

@contextmanager
def transaction():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(503, 'Database unavailable')
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(503, 'Database unavailable') from None
    finally:
        conn.close()

def require_conversation(cur, conversation_id):
    cur.execute('SELECT * FROM conversations WHERE id = %s AND user_id = %s;', (str(conversation_id), owner_id()))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, 'Conversation not found')
    return row

def create_conversation(title='New Conversation', first_message=None):
    title = title.strip()
    if not title or len(title) > 120:
        raise ValueError('Title must contain 1–120 characters')
    if first_message is not None:
        validate_message('user', first_message)
    with transaction() as cur:
        cur.execute('INSERT INTO conversations (title, user_id) VALUES (%s, %s) RETURNING id;', (title, owner_id()))
        cid = cur.fetchone()['id']
        if first_message is not None:
            cur.execute('INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s) RETURNING *;', (cid, 'user', first_message))
        return cid

def validate_message(role, content):
    if role not in ('user', 'assistant', 'system') or not isinstance(content, str) or not content.strip():
        raise ValueError('A supported role and nonblank content are required')

def add_message(conversation_id, role, content):
    validate_message(role, content)
    with transaction() as cur:
        require_conversation(cur, conversation_id)
        cur.execute('INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s) RETURNING *;', (str(conversation_id), role, content))
        row = cur.fetchone()
        cur.execute('UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = %s AND user_id = %s;', (str(conversation_id), owner_id()))
        return row

def get_recent_messages(conversation_id, limit=15):
    if not 1 <= limit <= 100:
        raise ValueError('limit must be 1–100')
    with transaction() as cur:
        require_conversation(cur, conversation_id)
        cur.execute('SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at DESC, id DESC LIMIT %s;', (str(conversation_id), limit))
        return list(reversed(cur.fetchall()))

def list_conversations(limit=50, offset=0):
    with transaction() as cur:
        cur.execute('SELECT * FROM conversations WHERE user_id = %s ORDER BY updated_at DESC, id DESC LIMIT %s OFFSET %s;', (owner_id(), limit, offset))
        return cur.fetchall()

def get_conversation(cid):
    with transaction() as cur:
        return require_conversation(cur, cid)

def delete_conversation(cid):
    with transaction() as cur:
        cur.execute('DELETE FROM conversations WHERE id = %s AND user_id = %s RETURNING id;', (str(cid), owner_id()))
        if not cur.fetchone():
            raise HTTPException(404, 'Conversation not found')

def search_keywords(query):
    return list(dict.fromkeys(w[:64] for w in re.findall(r'[\w]+', query[:10000].lower()) if len(w) > 3))[:8]

def search_previous_conversations(query, current_conversation_id=None, limit=5):
    keywords = search_keywords(query)
    if not keywords:
        return []
    if not 1 <= limit <= 20:
        raise ValueError('limit must be 1–20')
    with transaction() as cur:
        conditions = ' OR '.join(["m.content ILIKE %s ESCAPE '\\'"] * len(keywords))
        params = ['%' + k.replace('_', '\\_') + '%' for k in keywords]
        sql = f'SELECT m.*, c.title FROM messages m JOIN conversations c ON m.conversation_id = c.id WHERE ({conditions}) AND c.user_id = %s'
        params.append(owner_id())
        if current_conversation_id:
            sql += ' AND m.conversation_id != %s'
            params.append(str(current_conversation_id))
        sql += ' ORDER BY m.created_at DESC, m.id DESC LIMIT %s'
        cur.execute(sql, (*params, limit))
        return cur.fetchall()
