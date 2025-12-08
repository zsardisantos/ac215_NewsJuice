"Database functions for user mgmt"

import os
import psycopg
from typing import Optional, Dict, List
import json
from datetime import datetime

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

#user_db.py function, get_user_preferences. This literally grabs the user_prefernece
#values from the user_preferences table in our CloudSQL db. 
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

#save user preferences which inserts the user preferred topics + sources into the user_preferences table

def save_user_preferences(user_id: str, preferences: Dict[str, str]) -> bool:
    """Save user preferences (upsert).
    
    Only updates updated_at timestamp if the value actually changed.
    This prevents false positives when only voice preference changes.
    """
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                for key, value in preferences.items():
                    # Convert lists/dicts to JSON strings
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                    
                    value_str = str(value)
                    
                    # Check if value actually changed
                    cur.execute(
                        "SELECT preference_value FROM user_preferences WHERE user_id = %s AND preference_key = %s",
                        (user_id, key)
                    )
                    existing = cur.fetchone()
                    
                    # Only update timestamp if value changed
                    if existing and existing[0] == value_str:
                        # Value unchanged, don't update timestamp - use UPDATE without changing updated_at
                        cur.execute(
                            (
                                "UPDATE user_preferences SET preference_value = %s "
                                "WHERE user_id = %s AND preference_key = %s"
                            ),
                            (value_str, user_id, key),
                        )
                    else:
                        # Value changed or new preference, update timestamp
                        cur.execute(
                            (
                                "INSERT INTO user_preferences (user_id, preference_key, "
                                "preference_value, updated_at) VALUES (%s, %s, %s, NOW()) "
                                "ON CONFLICT (user_id, preference_key) DO UPDATE SET "
                                "preference_value = EXCLUDED.preference_value, updated_at = NOW()"
                            ),
                            (user_id, key, value_str),
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
    source_chunks: Optional[str] = None,  # NEW: JSON string of chunks used for daily brief
) -> bool:
    """Save audio history entry."""
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO audio_history (user_id, question_text, podcast_text, audio_url, source_chunks)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (user_id, question_text, podcast_text, audio_url, source_chunks),
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
                    """SELECT id, question_text, podcast_text, audio_url, source_chunks, created_at
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
                            "source_chunks": row[4],  # NEW: Include source chunks (JSONB/string)
                            "created_at": row[5].isoformat() if row[5] else None,
                        }
                    )
                return history
    except Exception as e:
        print(f"[db-error] Failed to get audio history: {e}")
        return []


def get_preferences_last_updated(user_id: str) -> Optional[str]:
    """Get the most recent updated_at timestamp for topics or sources preferences.
    
    Returns:
        ISO format timestamp string, or None if no preferences exist
    """
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Get max updated_at for topics or sources (the preference keys that affect daily brief)
                cur.execute(
                    """SELECT MAX(updated_at) 
                       FROM user_preferences 
                       WHERE user_id = %s 
                       AND preference_key IN ('topics', 'sources')""",
                    (user_id,),
                )
                result = cur.fetchone()
                if result and result[0]:
                    return result[0].isoformat()
                return None
    except Exception as e:
        print(f"[db-error] Failed to get preferences last updated: {e}")
        return None


def get_voice_preference_last_updated(user_id: str) -> Optional[str]:
    """Get the updated_at timestamp for voice_preference.
    
    Returns:
        ISO format timestamp string, or None if voice preference doesn't exist
    """
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT updated_at 
                       FROM user_preferences 
                       WHERE user_id = %s 
                       AND preference_key = 'voice_preference'""",
                    (user_id,),
                )
                result = cur.fetchone()
                if result and result[0]:
                    return result[0].isoformat()
                return None
    except Exception as e:
        print(f"[db-error] Failed to get voice preference last updated: {e}")
        return None
