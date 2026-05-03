import sqlite3
import json
import os
import time

DB_PATH     = os.path.join(os.path.dirname(__file__), "fpl_cache.db")
CACHE_TTL   = 14 * 24 * 3600  # 2 weeks in seconds
MAX_LEAGUES = 50


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS league_cache (
            league_id     TEXT PRIMARY KEY,
            data          TEXT NOT NULL,
            cached_at     REAL NOT NULL,
            last_accessed REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def get(league_id):
    """Return cached league data if present and fresh, else None."""
    conn = _db()
    row = conn.execute(
        "SELECT data, cached_at FROM league_cache WHERE league_id = ?",
        (str(league_id),)
    ).fetchone()
    if row is None:
        conn.close()
        return None
    data_json, cached_at = row
    if time.time() - cached_at > CACHE_TTL:
        conn.execute("DELETE FROM league_cache WHERE league_id = ?", (str(league_id),))
        conn.commit()
        conn.close()
        return None
    conn.execute(
        "UPDATE league_cache SET last_accessed = ? WHERE league_id = ?",
        (time.time(), str(league_id))
    )
    conn.commit()
    conn.close()
    return json.loads(data_json)


def set(league_id, data):
    """Store league data, evicting the least recently accessed entry if at capacity."""
    conn = _db()
    league_id = str(league_id)
    is_new = conn.execute(
        "SELECT 1 FROM league_cache WHERE league_id = ?", (league_id,)
    ).fetchone() is None
    if is_new:
        count = conn.execute("SELECT COUNT(*) FROM league_cache").fetchone()[0]
        if count >= MAX_LEAGUES:
            conn.execute("""
                DELETE FROM league_cache WHERE league_id = (
                    SELECT league_id FROM league_cache ORDER BY last_accessed ASC LIMIT 1
                )
            """)
    now = time.time()
    conn.execute(
        "INSERT OR REPLACE INTO league_cache (league_id, data, cached_at, last_accessed) VALUES (?,?,?,?)",
        (league_id, json.dumps(data), now, now)
    )
    conn.commit()
    conn.close()
