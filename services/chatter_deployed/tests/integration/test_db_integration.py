import os
import pytest
import psycopg
import json
from user_db import create_user, get_user_preferences, save_user_preferences, save_audio_history, get_audio_history


@pytest.mark.integration
class TestUserDBIntegration:

    @pytest.fixture(scope="class")
    def db_url(self):
        """Ensure we have a database URL for testing."""
        url = os.environ.get("DATABASE_URL")
        if not url:
            pytest.fail("DATABASE_URL environment variable not set for integration tests.")
        return url

    @pytest.fixture(autouse=True)
    def clean_db(self, db_url):
        """Clean up tables before and after each test."""

        def truncate():
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("TRUNCATE TABLE audio_history, user_preferences, users RESTART IDENTITY CASCADE;")

        truncate()
        yield
        truncate()

    def test_user_lifecycle(self):
        """Test creating a user and checking if they exist (via foreign key constraints or just success)."""
        uid = "integ_test_user"
        email = "integ@example.com"

        # 1. Create User
        assert create_user(uid, email) is True

        # 2. Try to create duplicate (should handle gracefully per code: DO NOTHING)
        assert create_user(uid, "other@example.com") is True

    def test_preferences_lifecycle(self):
        """Test saving and retrieving preferences."""
        uid = "pref_user"
        create_user(uid, "pref@example.com")

        prefs = {"theme": "dark", "topics": ["tech", "ai"]}

        # 1. Save
        assert save_user_preferences(uid, prefs) is True

        # 2. Retrieve
        saved = get_user_preferences(uid)
        assert saved["theme"] == "dark"
        assert "tech" in saved["topics"]

        # 3. Update existing
        new_prefs = {"theme": "light"}
        assert save_user_preferences(uid, new_prefs) is True
        updated = get_user_preferences(uid)
        assert updated["theme"] == "light"
        assert "tech" in updated["topics"]

    def test_audio_history_lifecycle(self):
        """Test saving and retrieving audio history."""
        uid = "audio_user"
        create_user(uid, "audio@example.com")

        q_text = "What is up?"
        p_text = "Sky is up."
        url = "http://audio.mp3"
        chunks = json.dumps([{"id": 1}])

        # 1. Save
        assert save_audio_history(uid, q_text, p_text, url, chunks) is True

        # 2. Get
        history = get_audio_history(uid)
        assert len(history) == 1
        entry = history[0]
        assert entry["question_text"] == q_text
        assert entry["podcast_text"] == p_text
        assert entry["audio_url"] == url
        assert entry["source_chunks"] == chunks
