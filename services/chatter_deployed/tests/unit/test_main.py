"""
Minimal unit tests for main.py - Chatter service FastAPI application.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Set environment variables BEFORE any imports
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/testdb"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
os.environ["GOOGLE_CLOUD_REGION"] = "us-central1"
os.environ["CORS_ALLOW_ORIGINS"] = "http://localhost:3000"

# Mock all external dependencies
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.auth'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.generative_models'] = MagicMock()
sys.modules['google.cloud.speech'] = MagicMock()
sys.modules['google.cloud.speech_v1'] = MagicMock()
sys.modules['google.cloud.texttospeech'] = MagicMock()
sys.modules['google.cloud.texttospeech_v1'] = MagicMock()
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['psycopg'] = MagicMock()
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.psycopg'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()


@pytest.fixture
def client():
    """Create test client."""
    with patch('main.initialize_firebase_admin'):
        with patch('main.GenerativeModel'):
            from fastapi.testclient import TestClient
            from main import app
            return TestClient(app, raise_server_exceptions=False)


def test_root(client):
    """Test root returns ok."""
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_health(client):
    """Test health returns ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_healthz(client):
    """Test healthz returns ok."""
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
