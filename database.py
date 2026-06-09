import sqlite3

DB_NAME = "music_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица истории поиска
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT
        )
    ''')
    
    # Таблица личного плейлиста (сохраняем file_id для избежания повторных скачиваний)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            file_id TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def add_to_history(user_id, query):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO search_history (user_id, query) VALUES (?, ?)", (user_id, query))
    conn.commit()
    conn.close()

def get_history(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT query FROM search_history WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_to_playlist(user_id, title, file_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM playlist WHERE user_id = ? AND file_id = ?", (user_id, file_id))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO playlist (user_id, title, file_id) VALUES (?, ?, ?)", (user_id, title, file_id))
        conn.commit()
    conn.close()

def get_playlist(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, file_id FROM playlist WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def remove_from_playlist(playlist_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM playlist WHERE id = ?", (playlist_id,))
    conn.commit()
    conn.close()