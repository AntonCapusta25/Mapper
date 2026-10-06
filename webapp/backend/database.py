from supabase import create_client, Client
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    # Fallback to local SQLite if Supabase not configured (only for local dev)
    import sqlite3
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sqlite.db")
    print("WARNING: Supabase credentials missing. Falling back to SQLite.")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_sqlite_connection():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite (legacy) or just confirms Supabase tables should exist."""
    if not supabase:
        conn = get_sqlite_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS searches (id TEXT PRIMARY KEY, intent TEXT NOT NULL, status TEXT DEFAULT 'running', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, search_id TEXT, name TEXT, email TEXT UNIQUE, website TEXT, phone TEXT, location TEXT, query TEXT, is_opened INTEGER DEFAULT 0, last_interaction TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS campaigns (search_id TEXT PRIMARY KEY, subject TEXT, html_body TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, direction TEXT, subject TEXT, body TEXT, thread_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(lead_id) REFERENCES leads(id))''')
        conn.commit()
        conn.close()


def update_search_status(search_id: str, status: str):
    if supabase:
        supabase.table("nexus_searches").update({"status": status}).eq("id", search_id).execute()
    else:
        conn = get_sqlite_connection()
        conn.execute("UPDATE searches SET status = ? WHERE id = ?", (status, search_id))
        conn.commit()
        conn.close()

def save_lead(search_id: str, lead_data: dict):
    """Saves a lead with Global Deduplication via email upsert."""
    data = {
        "search_id": search_id,
        "name": lead_data.get('name'),
        "email": lead_data.get('email'),
        "website": lead_data.get('website'),
        "phone": lead_data.get('phone'),
        "location": lead_data.get('location'),
        "query": lead_data.get('query')
    }
    if supabase:
        # Global deduplication: email is UNIQUE in Supabase
        supabase.table("nexus_leads").upsert(data, on_conflict="email").execute()
    else:
        conn = get_sqlite_connection()
        try:
            conn.execute('''
                INSERT INTO leads (search_id, name, email, website, phone, location, query)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (search_id, data['name'], data['email'], data['website'], data['phone'], data['location'], data['query']))
            conn.commit()
        except Exception: # Handle duplicate email error in SQLite silently
            pass
        finally:
            conn.close()

def get_all_searches() -> List[Dict[str, Any]]:
    """Retrieves all search sessions, sorted by most recent."""
    if not supabase:
        # SQLite fallback
        try:
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM searches ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception: return []

    # Supabase Pagination helper (default max 1000)
    all_rows = []
    chunk_size = 1000
    current_start = 0
    
    while True:
        res = supabase.table("nexus_searches").select("*").order("created_at", desc=True).range(current_start, current_start + chunk_size - 1).execute()
        data = res.data or []
        all_rows.extend(data)
        if len(data) < chunk_size or len(all_rows) >= 10000:
            break
        current_start += chunk_size
        
    return all_rows

def create_search(intent: str, search_id: str = None) -> str:
    """Create a new search session and return its ID."""
    if supabase:
        data = {"intent": intent, "status": "running"}
        if search_id:
            data["id"] = search_id
        res = supabase.table("nexus_searches").insert(data).execute()
        return res.data[0]["id"]
    else:
        import uuid
        final_id = search_id or str(uuid.uuid4())
        conn = get_sqlite_connection()
        conn.execute("INSERT INTO searches (id, intent, status) VALUES (?, ?, ?)", (final_id, intent, "running"))
        conn.commit()
        conn.close()
        return final_id

def get_leads_for_search(search_id: str) -> List[Dict[str, Any]]:
    """Retrieves all leads associated with a search session."""
    if not supabase:
        # SQLite fallback
        try:
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE search_id = ? ORDER BY created_at DESC", (search_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception: return []

    # Supabase Pagination for leads (bypassing the 1000 row limit)
    all_leads = []
    chunk_size = 1000
    current_start = 0
    
    while True:
        import uuid
        try:
            uuid.UUID(search_id)
        except ValueError:
            return [] # Invalid UUID, return empty

        res = supabase.table("nexus_leads").select("*").eq("search_id", search_id).order("created_at", desc=True).range(current_start, current_start + chunk_size - 1).execute()
        data = res.data or []
        all_leads.extend(data)
        if len(data) < chunk_size or len(all_leads) >= 50000:
            break
        current_start += chunk_size
        
    return all_leads

def delete_search(search_id: str):
    if supabase:
        supabase.table("nexus_searches").delete().eq("id", search_id).execute()
    else:
        conn = get_sqlite_connection()
        conn.execute("DELETE FROM leads WHERE search_id = ?", (search_id,))
        conn.execute("DELETE FROM campaigns WHERE search_id = ?", (search_id,))
        conn.execute("DELETE FROM searches WHERE id = ?", (search_id,))
        conn.commit()
        conn.close()

def log_lead_open(lead_id: int):
    if supabase:
        supabase.table("nexus_leads").update({"is_opened": True, "last_interaction": datetime.now().isoformat()}).eq("id", lead_id).execute()
    else:
        conn = get_sqlite_connection()
        conn.execute("UPDATE leads SET is_opened = 1, last_interaction = CURRENT_TIMESTAMP WHERE id = ?", (lead_id,))
        conn.commit()
        conn.close()

def save_message(lead_id: int, direction: str, subject: str, body: str, thread_id: str = None):
    data = {
        "lead_id": lead_id,
        "direction": direction,
        "subject": subject,
        "body": body,
        "thread_id": thread_id
    }
    if supabase:
        supabase.table("nexus_messages").insert(data).execute()
        supabase.table("nexus_leads").update({"last_interaction": datetime.now().isoformat()}).eq("id", lead_id).execute()
    else:
        conn = get_sqlite_connection()
        conn.execute("INSERT INTO messages (lead_id, direction, subject, body, thread_id) VALUES (?, ?, ?, ?, ?)", (lead_id, direction, subject, body, thread_id))
        conn.execute("UPDATE leads SET last_interaction = CURRENT_TIMESTAMP WHERE id = ?", (lead_id,))
        conn.commit()
        conn.close()

def get_lead_history(lead_id: int) -> List[Dict[str, Any]]:
    if supabase:
        res = supabase.table("nexus_messages").select("*").eq("lead_id", lead_id).order("created_at").execute()
        return res.data
    else:
        conn = get_sqlite_connection()
        rows = conn.execute("SELECT * FROM messages WHERE lead_id = ? ORDER BY created_at ASC", (lead_id,)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

def get_lead_by_email(email: str) -> Optional[Dict[str, Any]]:
    if supabase:
        res = supabase.table("nexus_leads").select("*").eq("email", email).execute()
        return res.data[0] if res.data else None
    else:
        conn = get_sqlite_connection()
        row = conn.execute("SELECT * FROM leads WHERE email = ?", (email,)).fetchone()
        conn.close()
        return dict(row) if row else None

def save_campaign(search_id: str, campaign_data: dict):
    data = {
        "search_id": search_id,
        "subject": campaign_data.get('subject', ''),
        "html_body": campaign_data.get('html_body', '')
    }
    if supabase:
        supabase.table("nexus_campaigns").upsert(data).execute()
    else:
        conn = get_sqlite_connection()
        conn.execute("INSERT OR REPLACE INTO campaigns (search_id, subject, html_body) VALUES (?, ?, ?)", (search_id, data['subject'], data['html_body']))
        conn.commit()
        conn.close()

def get_campaign(search_id: str) -> Optional[Dict[str, Any]]:
    if supabase:
        res = supabase.table("nexus_campaigns").select("*").eq("search_id", search_id).execute()
        return res.data[0] if res.data else None
    else:
        conn = get_sqlite_connection()
        row = conn.execute("SELECT * FROM campaigns WHERE search_id = ?", (search_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

# Initialize on import
init_db()
