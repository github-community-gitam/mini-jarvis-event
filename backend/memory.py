from database import get_db_connection

def create_conversation(title="New Conversation"):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (title) VALUES (%s) RETURNING id;",
                (title,)
            )
            return cur.fetchone()['id']
    except Exception as e:
        print(f"\n[DB Error - Create Conversation]: {e}")
    finally:
        conn.close()
    return None

def add_message(conversation_id, role, content):
    conn = get_db_connection()
    if not conn or not conversation_id:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s) RETURNING *;",
                (conversation_id, role, content)
            )
            return cur.fetchone()
    except Exception as e:
        print(f"\n[DB Error - Add Message]: {e}")
    finally:
        conn.close()
    return None

def get_recent_messages(conversation_id, limit=15):
    conn = get_db_connection()
    if not conn or not conversation_id:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM messages 
                WHERE conversation_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s;
                """,
                (conversation_id, limit)
            )
            rows = cur.fetchall()
            return list(reversed(rows))
    except Exception as e:
        print(f"\n[DB Error - Get Recent Messages]: {e}")
    finally:
        conn.close()
    return []

def search_previous_conversations(query, current_conversation_id=None, limit=5):
    conn = get_db_connection()
    if not conn:
        return []
        
    keywords = [word for word in query.lower().split() if len(word) > 3]
    if not keywords:
        return []
        
    try:
        with conn.cursor() as cur:
            # Build ILIKE conditions for each keyword
            conditions = " OR ".join(["content ILIKE %s"] * len(keywords))
            params = [f"%{kw}%" for kw in keywords]
            
            sql = f"""
                SELECT m.*, c.title 
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE ({conditions})
            """
            
            if current_conversation_id:
                sql += " AND m.conversation_id != %s"
                params.append(current_conversation_id)
                
            sql += " LIMIT %s"
            params.append(limit)
            
            cur.execute(sql, tuple(params))
            return cur.fetchall()
    except Exception as e:
        print(f"\n[DB Error - Search History]: {e}")
    finally:
        conn.close()
    return []
