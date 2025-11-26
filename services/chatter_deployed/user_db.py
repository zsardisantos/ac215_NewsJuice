"Database functions for user mgmt"

import os
import psycopg
from typing import Optional, Dict, List
import json

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")


def create_user(user_id: str, email: str) -> bool:
    "create new user in database"
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    ("INSERT INTO users (user_id, email) VALUES (%s, %s) " "ON CONFLICT (user_id) DO NOTHING"),
                    (user_id, email),
                )
                print(f"[db] User created: {user_id}")
                return True
    except Exception as e:
        print(f"[db-error] Failed to create user: {e}")
        return False


def get_user_preferences(user_id: str) -> Dict[str, str]:
    "Get all preferences for a user."
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    ("SELECT preference_key, preference_value FROM user_preferences " "WHERE user_id = %s"),
                    (user_id,),
                )
                preferences = {}
                for row in cur.fetchall():
                    key, value = row
                    preferences[key] = value
                return preferences
    except Exception as e:
        print(f"[db-error] Failed to get preferences: {e}")
        return {}


def save_user_preferences(user_id: str, preferences: Dict[str, str]) -> bool:
    """Save user preferences (upsert)."""
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                for key, value in preferences.items():
                    # Convert lists/dicts to JSON strings
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)

                    cur.execute(
                        (
                            "INSERT INTO user_preferences (user_id, preference_key, "
                            "preference_value, updated_at) VALUES (%s, %s, %s, NOW()) "
                            "ON CONFLICT (user_id, preference_key) DO UPDATE SET "
                            "preference_value = EXCLUDED.preference_value, updated_at = NOW()"
                        ),
                        (user_id, key, str(value)),
                    )
                print(f"[db] Preferences saved for user: {user_id}")
                return True
    except Exception as e:
        print(f"[db-error] Failed to save preferences: {e}")
        return False


def save_audio_history(
    user_id: str,
    question_text: str,
    podcast_text: str,
    audio_url: Optional[str] = None,
) -> bool:
    """Save audio history entry."""
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO audio_history (user_id, question_text, podcast_text, audio_url)
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, question_text, podcast_text, audio_url),
                )
                print(f"[db] Audio history saved for user: {user_id}")
                return True
    except Exception as e:
        print(f"[db-error] Failed to save audio history: {e}")
        return False


def get_audio_history(user_id: str, limit: int = 10) -> List[Dict]:
    """Get audio history for a user."""
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, question_text, podcast_text, audio_url, created_at
                       FROM audio_history
                       WHERE user_id = %s
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (user_id, limit),
                )
                history = []
                for row in cur.fetchall():
                    history.append(
                        {
                            "id": row[0],
                            "question_text": row[1],
                            "podcast_text": row[2],
                            "audio_url": row[3],
                            "created_at": row[4].isoformat() if row[4] else None,
                        }
                    )
                return history
    except Exception as e:
        print(f"[db-error] Failed to get audio history: {e}")
        return []
