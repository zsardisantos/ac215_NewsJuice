"""
Shared pytest fixtures and configuration for chatter_deployed tests.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock

# Set environment variables BEFORE any application imports
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_REGION", "us-central1")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AUDIO_BUCKET", "test-audio-bucket")
os.environ.setdefault("GCS_PREFIX", "podcasts/")

# Mock heavy external dependencies at module level
# This prevents import errors when running tests

# Firebase
mock_firebase_admin = MagicMock()
mock_firebase_auth = MagicMock()
sys.modules['firebase_admin'] = mock_firebase_admin
sys.modules['firebase_admin.auth'] = mock_firebase_auth
sys.modules['firebase_admin.credentials'] = MagicMock()

# Google Cloud
sys.modules['google.cloud.speech'] = MagicMock()
sys.modules['google.cloud.speech_v1'] = MagicMock()
sys.modules['google.cloud.texttospeech'] = MagicMock()
sys.modules['google.cloud.texttospeech_v1'] = MagicMock()
sys.modules['google.cloud.storage'] = MagicMock()

# Vertex AI
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.generative_models'] = MagicMock()

# Google GenAI
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()

# Database
sys.modules['psycopg'] = MagicMock()
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.psycopg'] = MagicMock()


@pytest.fixture(autouse=True)
def reset_modules():
    """Reset module state between tests."""
    # Clear any cached imports that might interfere
    modules_to_clear = [
        'main', 'retriever', 'helpers', 'firebase_auth', 
        'user_db', 'gcs_storage', 'query_enhancement'
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            # Don't delete, just note it exists
            pass
    yield


@pytest.fixture
def mock_gemini_model():
    """Mock Gemini GenerativeModel."""
    model = MagicMock()
    model.generate_content.return_value = MagicMock(
        text="This is a generated podcast response about Harvard news."
    )
    return model


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing retrieval."""
    return [
        (1, "Harvard announced new research funding for climate science.", "Harvard Gazette", 0.95),
        (2, "The university president spoke about campus sustainability.", "Harvard Crimson", 0.88),
        (3, "Budget allocations for next fiscal year revealed.", "Harvard Magazine", 0.82),
    ]


@pytest.fixture
def sample_user_preferences():
    """Sample user preferences."""
    return {
        "topics": '["Politics", "Technology", "Science"]',
        "sources": '["Harvard Gazette", "Harvard Crimson"]',
        "voice_preference": "en-US-Studio-O"
    }


@pytest.fixture
def sample_daily_brief_history():
    """Sample daily brief history entry."""
    return [
        {
            "id": 1,
            "question_text": "Daily Brief",
            "podcast_text": "Good morning, this is your Harvard News Daily Brief...",
            "audio_url": "https://storage.googleapis.com/bucket/audio.wav",
            "created_at": "2025-01-01T10:00:00Z",
            "source_chunks": '{"chunks": []}'
        }
    ]


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing."""
    from unittest.mock import AsyncMock
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_bytes = AsyncMock()
    ws.receive = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    return ws
