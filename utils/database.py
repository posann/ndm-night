import sqlite3
from utils.helpers import get_data_path

DB_FILE = get_data_path('downloads.db')

def get_connection():
    return sqlite3.connect(DB_FILE, timeout=20)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY,
            url TEXT,
            save_path TEXT,
            filename TEXT,
            total_size INTEGER,
            downloaded INTEGER,
            status TEXT,
            speed INTEGER,
            progress REAL,
            start_time REAL,
            paused BOOLEAN,
            resume_pos INTEGER,
            eta TEXT,
            elapsed_time TEXT,
            created_at TEXT
        )
    ''')
    
    # Simple Migration: check for new columns if they exist
    cursor.execute("PRAGMA table_info(downloads)")
    columns = [col[1] for col in cursor.fetchall()]
    
    for col, ctype in [('eta', 'TEXT'), ('elapsed_time', 'TEXT'), 
                      ('created_at', 'TEXT'), ('threads', 'INTEGER'), 
                      ('segments', 'TEXT')]:
        if col not in columns:
            cursor.execute(f"ALTER TABLE downloads ADD COLUMN {col} {ctype}")
            
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_download(info):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM downloads WHERE id = ?", (info['id'],))
    result = cursor.fetchone()
    
    if result:
        # Update
        cursor.execute('''
            UPDATE downloads SET 
                downloaded = ?, status = ?, speed = ?, progress = ?, 
                start_time = ?, paused = ?, resume_pos = ?,
                eta = ?, elapsed_time = ?, created_at = ?, threads = ?, segments = ?
            WHERE id = ?
        ''', (
            info.get('downloaded', 0), info.get('status', ''),
            info.get('speed', 0), info.get('progress', 0.0), info.get('start_time', 0.0),
            info.get('paused', False), info.get('resume_pos', 0),
            info.get('eta', ''), info.get('elapsed_time', ''), info.get('created_at', ''),
            info.get('threads', 1), info.get('segments', ''),
            info['id']
        ))
    else:
        # Insert
        cursor.execute('''
            INSERT INTO downloads (
                id, url, save_path, filename, total_size, downloaded, status, 
                speed, progress, start_time, paused, resume_pos,
                eta, elapsed_time, created_at, threads, segments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            info['id'], info.get('url', ''), info.get('save_path', ''), info.get('filename', ''),
            info.get('total_size', 0), info.get('downloaded', 0), info.get('status', 'Starting'),
            info.get('speed', 0), info.get('progress', 0.0), info.get('start_time', 0.0),
            info.get('paused', False), info.get('resume_pos', 0),
            info.get('eta', ''), info.get('elapsed_time', ''), info.get('created_at', ''),
            info.get('threads', 1), info.get('segments', '')
        ))
    
    conn.commit()
    conn.close()

def load_downloads():
    return get_all_downloads()

def get_all_downloads():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM downloads ORDER BY id DESC')
    rows = cursor.fetchall()
    
    downloads = {}
    for row in rows:
        down_id = row[0]
        downloads[down_id] = {
            'id': row[0],
            'url': row[1],
            'save_path': row[2],
            'filename': row[3],
            'total_size': row[4],
            'downloaded': row[5],
            'status': row[6],
            'speed': row[7],
            'progress': row[8],
            'start_time': row[9],
            'paused': bool(row[10]),
            'resume_pos': row[11],
            'eta': row[12],
            'elapsed_time': row[13],
            'created_at': row[14],
            'threads': row[15] if len(row) > 15 else 1,
            'segments': row[16] if len(row) > 16 else ''
        }
    
    conn.close()
    return downloads

def delete_download(download_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
    except: return default

def set_setting(key, value):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    except: pass
