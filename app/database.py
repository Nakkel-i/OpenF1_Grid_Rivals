
import json
import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "openf1_cache.db"
)


def initialize_database():
    """Create the cache table if it does not exist."""

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
        """)


def make_cache_key(endpoint, params=None):
    """Create a unique key for each API query."""

    return json.dumps(
        {
            "endpoint": endpoint,
            "params": params or {}
        },
        sort_keys=True,
        default=str
    )


def get_cached_data(endpoint, params=None):
    """Return saved data, or None if it has never been saved."""

    initialize_database()

    key = make_cache_key(endpoint, params)

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("""
            SELECT response_json
            FROM api_cache
            WHERE cache_key = ?
        """, (key,)).fetchone()

    if row is None:
        return None

    return json.loads(row[0])


def save_cached_data(endpoint, params, data):
    """Permanently save or replace an API response."""

    initialize_database()

    key = make_cache_key(endpoint, params)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO api_cache (
                cache_key,
                response_json,
                fetched_at
            )
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(cache_key) DO UPDATE SET
                response_json = excluded.response_json,
                fetched_at = excluded.fetched_at
        """, (
            key,
            json.dumps(data)
        ))

def delete_cached_data(endpoint, params=None):
    initialize_database()
    key = make_cache_key(endpoint, params)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM api_cache WHERE cache_key = ?",
            (key,)
        )