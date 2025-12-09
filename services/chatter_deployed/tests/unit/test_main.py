"""
Unit tests for main.py - Chatter service FastAPI application.
Target: 50%+ code coverage
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

# Set environment variables BEFORE any imports
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/testdb"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
os.environ["GOOGLE_CLOUD_REGION"] = "us-central1"
os.environ["CORS_ALLOW_ORIGINS"] = "http://localhost:3000"

# Mock all external dependencies before importing main
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.auth'] = MagicMock()
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.generative_models'] = MagicMock()
sys.modules['google.cloud.speech'] = MagicMock()
sys.modules['google.cloud.texttospeech'] = MagicMock()
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['psycopg'] = MagicMock()
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.psycopg'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_dependencies():
    """Mock all external dependencies."""
    with patch('main.initialize_firebase_admin'):
        with patch('main.GenerativeModel') as mock_model:
            mock_model.return_value = MagicMock()
            yield mock_model


@pytest.fixture
def test_client(mock_dependencies):
    """Create test client for FastAPI app."""
    # Import after mocking
    with patch('main.initialize_firebase_admin'):
        with patch('main.GenerativeModel'):
            from fastapi.testclient import TestClient
            from main import app
            return TestClient(app)


@pytest.fixture
def authenticated_request():
    """Create a mock authenticated request."""
    request = MagicMock()
    request.state.user_id = "test_user_123"
    request.state.user_email = "test@harvard.edu"
    return request


# ============================================================
# TESTS: Health Endpoints
# ============================================================

class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns ok."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_health_endpoint(self, test_client):
        """Test /health endpoint returns ok."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_healthz_endpoint(self, test_client):
        """Test /healthz endpoint returns ok."""
        response = test_client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"ok": True}


# ============================================================
# TESTS: User Endpoints (Authentication Required)
# ============================================================

class TestUserEndpoints:
    """Tests for user-related endpoints."""

    def test_create_user_unauthorized(self, test_client):
        """Test create user without authentication."""
        response = test_client.post("/api/user/create")
        assert response.status_code == 401

    def test_get_preferences_unauthorized(self, test_client):
        """Test get preferences without authentication."""
        response = test_client.get("/api/user/preferences")
        assert response.status_code == 401

    def test_save_preferences_unauthorized(self, test_client):
        """Test save preferences without authentication."""
        response = test_client.post(
            "/api/user/preferences",
            json={"topics": ["Politics"]}
        )
        assert response.status_code == 401

    def test_get_history_unauthorized(self, test_client):
        """Test get history without authentication."""
        response = test_client.get("/api/user/history")
        assert response.status_code == 401

    def test_create_user_success(self, test_client):
        """Test successful user creation with valid token."""
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.create_user', return_value=True):
                response = test_client.post(
                    "/api/user/create",
                    headers={"Authorization": "Bearer valid_token"}
                )
                assert response.status_code == 200
                assert response.json()["status"] == "success"

    def test_get_preferences_success(self, test_client):
        """Test successful get preferences."""
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_user_preferences', return_value={"topics": '["Politics"]'}):
                response = test_client.get(
                    "/api/user/preferences",
                    headers={"Authorization": "Bearer valid_token"}
                )
                assert response.status_code == 200
                assert response.json()["status"] == "success"

    def test_save_preferences_success(self, test_client):
        """Test successful save preferences."""
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.create_user', return_value=True):
                with patch('main.save_user_preferences', return_value=True):
                    response = test_client.post(
                        "/api/user/preferences",
                        headers={"Authorization": "Bearer valid_token"},
                        json={"topics": ["Politics", "Technology"]}
                    )
                    assert response.status_code == 200
                    assert response.json()["status"] == "success"

    def test_get_history_success(self, test_client):
        """Test successful get history."""
        mock_history = [
            {"id": 1, "question_text": "Test", "podcast_text": "Response", "created_at": "2025-01-01"}
        ]
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_audio_history', return_value=mock_history):
                response = test_client.get(
                    "/api/user/history",
                    headers={"Authorization": "Bearer valid_token"}
                )
                assert response.status_code == 200
                assert response.json()["status"] == "success"
                assert len(response.json()["history"]) == 1


# ============================================================
# TESTS: Daily Brief Endpoints
# ============================================================

class TestDailyBriefEndpoints:
    """Tests for daily brief endpoints."""

    def test_daily_brief_unauthorized(self, test_client):
        """Test daily brief without authentication."""
        response = test_client.post("/api/daily-brief")
        assert response.status_code == 401

    def test_daily_brief_status_unauthorized(self, test_client):
        """Test daily brief status without authentication."""
        response = test_client.get("/api/daily-brief/status")
        assert response.status_code == 401

    def test_daily_brief_latest_unauthorized(self, test_client):
        """Test get latest daily brief without authentication."""
        response = test_client.get("/api/daily-brief/latest")
        assert response.status_code == 401

    def test_daily_brief_status_success(self, test_client):
        """Test successful daily brief status check."""
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_user_preferences', return_value={}):
                with patch('main.get_preferences_last_updated', return_value=None):
                    with patch('main.get_voice_preference_last_updated', return_value=None):
                        response = test_client.get(
                            "/api/daily-brief/status",
                            headers={"Authorization": "Bearer valid_token"}
                        )
                        assert response.status_code == 200
                        assert "generated_today" in response.json()

    def test_daily_brief_status_with_timestamp(self, test_client):
        """Test daily brief status with existing timestamp."""
        today = datetime.now(timezone.utc).isoformat()
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_user_preferences', return_value={"last_daily_brief_generated": today}):
                with patch('main.get_preferences_last_updated', return_value=None):
                    with patch('main.get_voice_preference_last_updated', return_value=None):
                        response = test_client.get(
                            "/api/daily-brief/status",
                            headers={"Authorization": "Bearer valid_token"}
                        )
                        assert response.status_code == 200
                        assert response.json()["generated_today"] == True

    def test_daily_brief_latest_success(self, test_client):
        """Test successful get latest daily brief."""
        mock_history = [
            {
                "id": 1,
                "question_text": "Daily Brief",
                "podcast_text": "Good morning...",
                "audio_url": "https://storage.example.com/audio.wav",
                "created_at": "2025-01-01T10:00:00Z"
            }
        ]
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_audio_history', return_value=mock_history):
                response = test_client.get(
                    "/api/daily-brief/latest",
                    headers={"Authorization": "Bearer valid_token"}
                )
                assert response.status_code == 200
                assert response.json()["question_text"] == "Daily Brief"

    def test_daily_brief_latest_not_found(self, test_client):
        """Test get latest daily brief when none exists."""
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_audio_history', return_value=[]):
                response = test_client.get(
                    "/api/daily-brief/latest",
                    headers={"Authorization": "Bearer valid_token"}
                )
                assert response.status_code == 404

    def test_daily_brief_no_preferences(self, test_client):
        """Test daily brief generation without preferences set."""
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_user_preferences', return_value={"topics": "[]", "sources": "[]"}):
                with patch('main.get_preferences_last_updated', return_value=None):
                    with patch('main.get_voice_preference_last_updated', return_value=None):
                        response = test_client.post(
                            "/api/daily-brief",
                            headers={"Authorization": "Bearer valid_token"}
                        )
                        assert response.status_code == 400
                        assert "No preferences set" in response.json()["detail"]


# ============================================================
# TESTS: Firebase Auth Middleware
# ============================================================

class TestFirebaseAuthMiddleware:
    """Tests for Firebase authentication middleware."""

    def test_options_request_bypasses_auth(self, test_client):
        """Test that OPTIONS requests bypass authentication."""
        response = test_client.options("/api/user/preferences")
        # OPTIONS should not return 401
        assert response.status_code != 401

    def test_invalid_token(self, test_client):
        """Test request with invalid token."""
        with patch('main.verify_token', side_effect=Exception("Invalid token")):
            response = test_client.get(
                "/api/user/preferences",
                headers={"Authorization": "Bearer invalid_token"}
            )
            assert response.status_code == 401

    def test_missing_bearer_prefix(self, test_client):
        """Test request with missing Bearer prefix."""
        response = test_client.get(
            "/api/user/preferences",
            headers={"Authorization": "invalid_token"}
        )
        assert response.status_code == 401


# ============================================================
# TESTS: WebSocket Endpoint
# ============================================================

class TestWebSocketEndpoint:
    """Tests for WebSocket chat endpoint."""

    def test_websocket_connect_without_token(self, test_client):
        """Test WebSocket connection without token."""
        with test_client.websocket_connect("/ws/chat") as websocket:
            # Should connect but log warning about no token
            websocket.send_json({"type": "reset"})
            data = websocket.receive_json()
            assert data["status"] == "reset"

    def test_websocket_reset_message(self, test_client):
        """Test WebSocket reset message."""
        with test_client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json({"type": "reset"})
            data = websocket.receive_json()
            assert data["status"] == "reset"

    def test_websocket_invalid_json(self, test_client):
        """Test WebSocket with invalid JSON."""
        with test_client.websocket_connect("/ws/chat") as websocket:
            websocket.send_text("not valid json")
            data = websocket.receive_json()
            assert "error" in data

    def test_websocket_complete_without_audio(self, test_client):
        """Test WebSocket complete signal without audio."""
        with test_client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json({"type": "complete"})
            data = websocket.receive_json()
            assert data["error"] == "No audio received"

    def test_websocket_audio_chunk_received(self, test_client):
        """Test WebSocket receives audio chunk."""
        with test_client.websocket_connect("/ws/chat") as websocket:
            # Send some audio bytes
            websocket.send_bytes(b"fake audio data")
            data = websocket.receive_json()
            assert data["status"] == "chunk_received"
            assert data["size"] > 0


# ============================================================
# TESTS: Helper Function - _retrieve_and_generate_podcast
# ============================================================

class TestRetrieveAndGeneratePodcast:
    """Tests for the _retrieve_and_generate_podcast helper function."""

    @pytest.mark.asyncio
    async def test_retrieve_with_brief_context(self):
        """Test retrieval using daily brief context."""
        # Import after setting up mocks
        with patch('main.initialize_firebase_admin'):
            with patch('main.GenerativeModel'):
                from main import _retrieve_and_generate_podcast
                
                mock_websocket = AsyncMock()
                mock_model = MagicMock()
                mock_model.generate_content.return_value = MagicMock(text="Test podcast")
                
                brief_context = {
                    "chunks": [
                        {"chunk_id": 1, "chunk_text": "Test chunk", "source_type": "Gazette", "score": 0.9}
                    ]
                }
                
                with patch('main.call_gemini_api', return_value=("Test podcast", None)):
                    with patch('main.get_user_preferences', return_value={}):
                        with patch('main.text_to_audio_stream', new_callable=AsyncMock, return_value=True):
                            with patch('main.save_audio_history'):
                                result = await _retrieve_and_generate_podcast(
                                    websocket=mock_websocket,
                                    enhanced_queries={"enhanced_query_1": "test query"},
                                    original_query="test",
                                    user_id="test_user",
                                    model=mock_model,
                                    use_brief_context=True,
                                    brief_context=brief_context
                                )
                                
                                assert result == True

    @pytest.mark.asyncio
    async def test_retrieve_general_question(self):
        """Test retrieval for general question (not using brief context)."""
        with patch('main.initialize_firebase_admin'):
            with patch('main.GenerativeModel'):
                from main import _retrieve_and_generate_podcast
                
                mock_websocket = AsyncMock()
                mock_model = MagicMock()
                
                with patch('main.call_retriever_service', return_value=[
                    (1, "Chunk text", "Harvard Gazette", 0.9)
                ]):
                    with patch('main.call_gemini_api', return_value=("Test podcast", None)):
                        with patch('main.get_user_preferences', return_value={}):
                            with patch('main.text_to_audio_stream', new_callable=AsyncMock, return_value=True):
                                with patch('main.save_audio_history'):
                                    result = await _retrieve_and_generate_podcast(
                                        websocket=mock_websocket,
                                        enhanced_queries={"enhanced_query_1": "test query"},
                                        original_query="test",
                                        user_id="test_user",
                                        model=mock_model,
                                        use_brief_context=False,
                                        brief_context=None
                                    )
                                    
                                    assert result == True

    @pytest.mark.asyncio
    async def test_retrieve_no_chunks_found(self):
        """Test retrieval when no chunks are found."""
        with patch('main.initialize_firebase_admin'):
            with patch('main.GenerativeModel'):
                from main import _retrieve_and_generate_podcast
                
                mock_websocket = AsyncMock()
                mock_model = MagicMock()
                
                with patch('main.call_retriever_service', return_value=[]):
                    with patch('main.call_gemini_api', return_value=("No articles found response", None)):
                        with patch('main.get_user_preferences', return_value={}):
                            with patch('main.text_to_audio_stream', new_callable=AsyncMock, return_value=True):
                                with patch('main.save_audio_history'):
                                    result = await _retrieve_and_generate_podcast(
                                        websocket=mock_websocket,
                                        enhanced_queries={"enhanced_query_1": "test"},
                                        original_query="test",
                                        user_id="test_user",
                                        model=mock_model,
                                        use_brief_context=False,
                                        brief_context=None
                                    )
                                    
                                    # Should still succeed (with warning)
                                    mock_websocket.send_json.assert_any_call({"warning": "No relevant articles found"})

    @pytest.mark.asyncio
    async def test_retrieve_llm_error(self):
        """Test retrieval when LLM returns error."""
        with patch('main.initialize_firebase_admin'):
            with patch('main.GenerativeModel'):
                from main import _retrieve_and_generate_podcast
                
                mock_websocket = AsyncMock()
                mock_model = MagicMock()
                
                with patch('main.call_retriever_service', return_value=[]):
                    with patch('main.call_gemini_api', return_value=(None, "API Error")):
                        result = await _retrieve_and_generate_podcast(
                            websocket=mock_websocket,
                            enhanced_queries={"enhanced_query_1": "test"},
                            original_query="test",
                            user_id=None,
                            model=mock_model,
                            use_brief_context=False,
                            brief_context=None
                        )
                        
                        assert result == False


# ============================================================
# TESTS: Daily Brief Generation
# ============================================================

class TestDailyBriefGeneration:
    """Tests for daily brief generation logic."""

    def test_daily_brief_voice_only_change(self, test_client):
        """Test daily brief regeneration for voice-only change."""
        now = datetime.now(timezone.utc)
        past = datetime(2025, 1, 1, tzinfo=timezone.utc)
        
        mock_history = [
            {
                "question_text": "Daily Brief",
                "podcast_text": "Existing transcript",
                "audio_url": "https://old-url.com/audio.wav",
                "created_at": past.isoformat(),
                "source_chunks": json.dumps({"chunks": []})
            }
        ]
        
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_user_preferences', return_value={
                "topics": '["Politics"]',
                "sources": '["Harvard Gazette"]',
                "voice_preference": "en-US-Studio-Q",
                "last_daily_brief_generated": past.isoformat()
            }):
                with patch('main.get_preferences_last_updated', return_value=past.isoformat()):
                    with patch('main.get_voice_preference_last_updated', return_value=now.isoformat()):
                        with patch('main.get_audio_history', return_value=mock_history):
                            with patch('main.text_to_audio_bytes', return_value=b"audio"):
                                with patch('main.upload_audio_to_gcs', return_value="https://new-url.com/audio.wav"):
                                    with patch('main.save_audio_history'):
                                        response = test_client.post(
                                            "/api/daily-brief",
                                            headers={"Authorization": "Bearer valid_token"}
                                        )
                                        assert response.status_code == 200
                                        assert response.json()["voice_only_update"] == True

    def test_daily_brief_full_generation(self, test_client):
        """Test full daily brief generation."""
        mock_chunks = [
            (1, "Article chunk 1", "Harvard Gazette", 0.95),
            (2, "Article chunk 2", "Harvard Crimson", 0.88),
        ]
        
        mock_model_response = MagicMock()
        mock_model_response.text = "Good morning, this is your daily brief..."
        
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_user_preferences', return_value={
                "topics": '["Politics"]',
                "sources": '["Harvard Gazette"]'
            }):
                with patch('main.get_preferences_last_updated', return_value=None):
                    with patch('main.get_voice_preference_last_updated', return_value=None):
                        with patch('main.search_articles_by_preferences', return_value=mock_chunks):
                            with patch('main.model') as mock_model:
                                mock_model.generate_content.return_value = mock_model_response
                                with patch('main.text_to_audio_bytes', return_value=b"audio"):
                                    with patch('main.upload_audio_to_gcs', return_value="https://url.com/audio.wav"):
                                        with patch('main.save_audio_history'):
                                            with patch('main.save_user_preferences'):
                                                response = test_client.post(
                                                    "/api/daily-brief",
                                                    headers={"Authorization": "Bearer valid_token"}
                                                )
                                                assert response.status_code == 200
                                                assert response.json()["success"] == True

    def test_daily_brief_no_articles_found(self, test_client):
        """Test daily brief when no articles match preferences."""
        with patch('main.verify_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_user", "email": "test@test.com"}
            with patch('main.get_user_preferences', return_value={
                "topics": '["Politics"]',
                "sources": '["Harvard Gazette"]'
            }):
                with patch('main.get_preferences_last_updated', return_value=None):
                    with patch('main.get_voice_preference_last_updated', return_value=None):
                        with patch('main.search_articles_by_preferences', return_value=[]):
                            response = test_client.post(
                                "/api/daily-brief",
                                headers={"Authorization": "Bearer valid_token"}
                            )
                            assert response.status_code == 404
                            assert "No articles found" in response.json()["detail"]
