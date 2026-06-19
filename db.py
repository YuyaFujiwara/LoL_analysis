import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            game_creation INTEGER,
            raw_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_match_from_db(match_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT raw_json FROM matches WHERE match_id = ?', (match_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def save_match_to_db(match_id: str, game_creation: int, match_data: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    raw_json = json.dumps(match_data, ensure_ascii=False)
    cursor.execute('''
        INSERT OR REPLACE INTO matches (match_id, game_creation, raw_json)
        VALUES (?, ?, ?)
    ''', (match_id, game_creation, raw_json))
    conn.commit()
    conn.close()

# Initialize DB when module is loaded
init_db()
