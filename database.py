import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "voice_notes.db")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_str TEXT NOT NULL,
            time_str TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            location_name TEXT,
            audio_path TEXT,
            transcription TEXT NOT NULL,
            summary TEXT NOT NULL,
            theme TEXT NOT NULL,
            tasks_json TEXT DEFAULT '[]',
            duration_sec REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    conn.close()

def insert_note(
    date_str: str,
    time_str: str,
    transcription: str,
    summary: str,
    theme: str,
    tasks: List[str],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_name: Optional[str] = None,
    audio_path: Optional[str] = None,
    duration_sec: float = 0.0
) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notes (
            date_str, time_str, latitude, longitude, location_name,
            audio_path, transcription, summary, theme, tasks_json, duration_sec
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        date_str,
        time_str,
        latitude,
        longitude,
        location_name,
        audio_path,
        transcription,
        summary,
        theme,
        json.dumps(tasks, ensure_ascii=False),
        duration_sec
    ))
    note_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    conn.close()
    return dict_from_row(row)

def dict_from_row(row) -> Dict[str, Any]:
    if not row:
        return {}
    data = dict(row)
    try:
        data["tasks"] = json.loads(data.get("tasks_json") or "[]")
    except Exception:
        data["tasks"] = []
    return data

def get_all_notes(target_date: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    if target_date:
        cursor.execute("SELECT * FROM notes WHERE date_str = ? ORDER BY time_str DESC, id DESC", (target_date,))
    else:
        cursor.execute("SELECT * FROM notes ORDER BY date_str DESC, time_str DESC, id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]

def get_available_dates() -> List[str]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date_str FROM notes ORDER BY date_str DESC")
    rows = cursor.fetchall()
    conn.close()
    return [r["date_str"] for r in rows]

def delete_note_by_id(note_id: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT audio_path FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    if row and row["audio_path"] and os.path.exists(row["audio_path"]):
        try:
            os.remove(row["audio_path"])
        except Exception:
            pass
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
