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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_profiles (
            riot_id TEXT PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS champion_mastery (
            puuid TEXT PRIMARY KEY,
            raw_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_saved_profiles() -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT riot_id FROM saved_profiles')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_saved_profile(riot_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO saved_profiles (riot_id) VALUES (?)', (riot_id,))
    conn.commit()
    conn.close()

def remove_saved_profile(riot_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM saved_profiles WHERE riot_id = ?', (riot_id,))
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
    cursor.execute('''
        INSERT OR REPLACE INTO matches (match_id, game_creation, raw_json)
        VALUES (?, ?, ?)
    ''', (match_id, game_creation, json.dumps(match_data, ensure_ascii=False)))
    conn.commit()
    conn.close()

def get_mastery_from_db(puuid: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT raw_json FROM champion_mastery WHERE puuid = ?', (puuid,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def save_mastery_to_db(puuid: str, mastery_data: list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO champion_mastery (puuid, raw_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (puuid, json.dumps(mastery_data, ensure_ascii=False)))
    conn.commit()
    conn.close()

# Initialize DB when module is loaded
init_db()
