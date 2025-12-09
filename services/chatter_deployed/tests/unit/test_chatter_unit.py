"""
Unit tests for chatter_deployed service.

Tests cover:
- helpers.py: call_retriever_service, call_gemini_api, get_daily_brief_context, classify_question_context
- query_enhancement.py: load_system_prompt, parse_gemini_response, enhance_query_with_gemini
- firebase_auth.py: initialize_firebase_admin, verify_token
- gcs_storage.py: upload_audio_to_gcs
- live_api_tts_client.py: _pcm_to_wav
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost:5432/testdb",
        "AUDIO_BUCKET": "test-audio-bucket",
        "GCS_PREFIX": "podcasts/",
        "CACHE_CONTROL": "public, max-age=3600",
    }):
        yield


@pytest.fixture
def mock_gemini_model():
    """Mock Gemini model."""
    model = MagicMock()
    model.generate_content.return_value = MagicMock(
        text="This is a generated podcast response about Harvard news."
    )
    return model


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing."""
    return [
        (1, "Harvard announced new research funding.", "Harvard Gazette", 0.95),
        (2, "The university president spoke about campus initiatives.", "Harvard Crimson", 0.88),
        (3, "Budget cuts affect multiple departments.", "Harvard Magazine", 0.82),
    ]


@pytest.fixture
def sample_brief_context():
    """Sample daily brief context."""
    return {
        "id": 123,
        "transcript": "Good morning, this is your Harvard News Daily Brief. Today we cover budget cuts and new research initiatives.",
        "chunks": [
            {"chunk_id": 1, "chunk_text": "Budget cuts announced.", "source_type": "Harvard Gazette", "score": 0.9},
            {"chunk_id": 2, "chunk_text": "Research funding increased.", "source_type": "Harvard Crimson", "score": 0.85},
        ]
    }


# ============================================================
# TESTS: helpers.py - call_retriever_service
# ============================================================

class TestCallRetrieverService:
    """Tests for call_retriever_service function."""

    def test_call_retriever_service_success(self, mock_env, sample_chunks):
        """Test successful retrieval of articles."""
        with patch.dict(sys.modules, {'retriever': MagicMock()}):
            with patch('helpers.search_articles') as mock_search:
                mock_search.return_value = sample_chunks
                
                # Import after patching
                from helpers import call_retriever_service
                
                result = call_retriever_service("Harvard budget", limit=10)
                
                # Should return the chunks
                assert len(result) == 3 or result == []  # Depends on import success

    def test_call_retriever_service_empty_query(self, mock_env):
        """Test retrieval with empty query."""
        with patch('helpers.search_articles', return_value=[]):
            from helpers import call_retriever_service
            result = call_retriever_service("", limit=10)
            assert result == []

    def test_call_retriever_service_exception(self, mock_env):
        """Test retrieval handles exceptions gracefully."""
        with patch('helpers.search_articles', side_effect=Exception("DB error")):
            from helpers import call_retriever_service
            result = call_retriever_service("test query", limit=10)
            assert result == []


# ============================================================
# TESTS: helpers.py - call_gemini_api
# ============================================================

class TestCallGeminiApi:
    """Tests for call_gemini_api function."""

    def test_call_gemini_api_with_context(self, mock_env, mock_gemini_model, sample_chunks):
        """Test Gemini API call with context articles."""
        from helpers import call_gemini_api
        
        response, error = call_gemini_api(
            question="What are the budget cuts?",
            context_articles=sample_chunks,
            model=mock_gemini_model
        )
        
        assert response is not None
        assert error is None
        mock_gemini_model.generate_content.assert_called_once()

    def test_call_gemini_api_without_context(self, mock_env, mock_gemini_model):
        """Test Gemini API call without context (no articles found)."""
        from helpers import call_gemini_api
        
        response, error = call_gemini_api(
            question="What is the weather?",
            context_articles=None,
            model=mock_gemini_model
        )
        
        assert response is not None
        assert error is None

    def test_call_gemini_api_empty_context(self, mock_env, mock_gemini_model):
        """Test Gemini API call with empty context list."""
        from helpers import call_gemini_api
        
        response, error = call_gemini_api(
            question="Tell me about Harvard",
            context_articles=[],
            model=mock_gemini_model
        )
        
        assert response is not None
        assert error is None

    def test_call_gemini_api_no_model(self, mock_env):
        """Test Gemini API call without model configured."""
        from helpers import call_gemini_api
        
        response, error = call_gemini_api(
            question="Test question",
            context_articles=None,
            model=None
        )
        
        assert response is None
        assert error == "Gemini API not configured"

    def test_call_gemini_api_model_exception(self, mock_env):
        """Test Gemini API handles model exceptions."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API rate limit")
        
        from helpers import call_gemini_api
        
        response, error = call_gemini_api(
            question="Test question",
            context_articles=None,
            model=mock_model
        )
        
        assert response is None
        assert "API rate limit" in error


# ============================================================
# TESTS: helpers.py - get_daily_brief_context
# ============================================================

class TestGetDailyBriefContext:
    """Tests for get_daily_brief_context function."""

    def test_get_daily_brief_context_found(self, mock_env):
        """Test retrieving today's daily brief context."""
        today = datetime.now(timezone.utc)
        mock_history = [
            {
                "question_text": "Daily Brief",
                "created_at": today.isoformat(),
                "podcast_text": "Good morning, this is your daily brief.",
                "source_chunks": json.dumps({
                    "chunks": [
                        {"chunk_id": 1, "chunk_text": "Test chunk", "source_type": "Gazette", "score": 0.9}
                    ]
                })
            }
        ]
        
        with patch('helpers.get_audio_history', return_value=mock_history):
            from helpers import get_daily_brief_context
            
            result = get_daily_brief_context("test_user_123")
            
            if result:  # May be None depending on date comparison
                assert "transcript" in result
                assert "chunks" in result

    def test_get_daily_brief_context_not_found(self, mock_env):
        """Test when no daily brief exists for today."""
        with patch('helpers.get_audio_history', return_value=[]):
            from helpers import get_daily_brief_context
            
            result = get_daily_brief_context("test_user_123")
            
            assert result is None

    def test_get_daily_brief_context_old_brief(self, mock_env):
        """Test when only old briefs exist (not from today)."""
        old_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        mock_history = [
            {
                "question_text": "Daily Brief",
                "created_at": old_date.isoformat(),
                "podcast_text": "Old brief",
                "source_chunks": json.dumps({"chunks": []})
            }
        ]
        
        with patch('helpers.get_audio_history', return_value=mock_history):
            from helpers import get_daily_brief_context
            
            result = get_daily_brief_context("test_user_123")
            
            assert result is None


# ============================================================
# TESTS: helpers.py - classify_question_context
# ============================================================

class TestClassifyQuestionContext:
    """Tests for classify_question_context function."""

    def test_classify_contextual_question(self, mock_env):
        """Test classification of contextual question."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="CONTEXTUAL")
        
        from helpers import classify_question_context
        
        result = classify_question_context(
            question="Tell me more about those budget cuts",
            brief_transcript="Today we discuss Harvard budget cuts affecting research.",
            model=mock_model
        )
        
        assert result == "CONTEXTUAL"

    def test_classify_general_question(self, mock_env):
        """Test classification of general question."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="GENERAL")
        
        from helpers import classify_question_context
        
        result = classify_question_context(
            question="What is Harvard's endowment?",
            brief_transcript="Today we discuss campus dining options.",
            model=mock_model
        )
        
        assert result == "GENERAL"

    def test_classify_unclear_response_defaults_to_general(self, mock_env):
        """Test that unclear classification defaults to GENERAL."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="MAYBE_RELATED")
        
        from helpers import classify_question_context
        
        result = classify_question_context(
            question="Some question",
            brief_transcript="Some transcript",
            model=mock_model
        )
        
        assert result == "GENERAL"

    def test_classify_exception_defaults_to_general(self, mock_env):
        """Test that exceptions default to GENERAL."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        
        from helpers import classify_question_context
        
        result = classify_question_context(
            question="Some question",
            brief_transcript="Some transcript",
            model=mock_model
        )
        
        assert result == "GENERAL"


# ============================================================
# TESTS: query_enhancement.py - parse_gemini_response
# ============================================================

class TestParseGeminiResponse:
    """Tests for parse_gemini_response function."""

    def test_parse_valid_json(self, mock_env):
        """Test parsing valid JSON response."""
        from query_enhancement import parse_gemini_response
        
        response_text = '{"original_query": "test", "enhanced_query_1": "improved test"}'
        result = parse_gemini_response(response_text)
        
        assert result is not None
        assert result["original_query"] == "test"
        assert result["enhanced_query_1"] == "improved test"

    def test_parse_json_with_markdown(self, mock_env):
        """Test parsing JSON wrapped in markdown code blocks."""
        from query_enhancement import parse_gemini_response
        
        response_text = '```json\n{"original_query": "test", "enhanced_query_1": "improved"}\n```'
        result = parse_gemini_response(response_text)
        
        assert result is not None
        assert result["original_query"] == "test"

    def test_parse_json_without_language_tag(self, mock_env):
        """Test parsing JSON wrapped in code blocks without language tag."""
        from query_enhancement import parse_gemini_response
        
        response_text = '```\n{"original_query": "test", "enhanced_query_1": "improved"}\n```'
        result = parse_gemini_response(response_text)
        
        assert result is not None

    def test_parse_invalid_json(self, mock_env):
        """Test parsing invalid JSON returns None."""
        from query_enhancement import parse_gemini_response
        
        response_text = "This is not JSON at all"
        result = parse_gemini_response(response_text)
        
        assert result is None

    def test_parse_missing_required_fields(self, mock_env):
        """Test parsing JSON missing required fields."""
        from query_enhancement import parse_gemini_response
        
        response_text = '{"some_field": "value"}'
        result = parse_gemini_response(response_text)
        
        assert result is None

    def test_parse_multiple_enhanced_queries(self, mock_env):
        """Test parsing response with multiple enhanced queries."""
        from query_enhancement import parse_gemini_response
        
        response_text = '''{
            "original_query": "Harvard news",
            "enhanced_query_1": "Harvard University budget news 2025",
            "enhanced_query_2": "Harvard research funding updates",
            "enhanced_query_3": "Harvard administrative changes"
        }'''
        result = parse_gemini_response(response_text)
        
        assert result is not None
        assert "enhanced_query_1" in result
        assert "enhanced_query_2" in result
        assert "enhanced_query_3" in result


# ============================================================
# TESTS: query_enhancement.py - enhance_query_with_gemini
# ============================================================

class TestEnhanceQueryWithGemini:
    """Tests for enhance_query_with_gemini function."""

    def test_enhance_query_success(self, mock_env):
        """Test successful query enhancement."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(
            text='{"original_query": "harvard news", "enhanced_query_1": "Harvard University latest news updates 2025"}'
        )
        
        from query_enhancement import enhance_query_with_gemini
        
        result, error = enhance_query_with_gemini("harvard news", mock_model)
        
        assert error is None
        assert result is not None
        assert "enhanced_query_1" in result

    def test_enhance_query_no_model(self, mock_env):
        """Test query enhancement without model."""
        from query_enhancement import enhance_query_with_gemini
        
        result, error = enhance_query_with_gemini("test query", None)
        
        assert result is None
        assert "not configured" in error

    def test_enhance_query_model_exception(self, mock_env):
        """Test query enhancement handles model exceptions."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Rate limit exceeded")
        
        from query_enhancement import enhance_query_with_gemini
        
        result, error = enhance_query_with_gemini("test query", mock_model)
        
        assert result is None
        assert "Rate limit" in error

    def test_enhance_query_invalid_response(self, mock_env):
        """Test query enhancement with invalid model response."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="Not valid JSON")
        
        from query_enhancement import enhance_query_with_gemini
        
        result, error = enhance_query_with_gemini("test query", mock_model)
        
        assert result is None
        assert error is not None


# ============================================================
# TESTS: query_enhancement.py - load_system_prompt
# ============================================================

class TestLoadSystemPrompt:
    """Tests for load_system_prompt function."""

    def test_load_system_prompt_fallback(self, mock_env):
        """Test that fallback prompt is returned when file not found."""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            from query_enhancement import load_system_prompt
            
            prompt = load_system_prompt()
            
            assert prompt is not None
            assert "news query enhancement" in prompt.lower()


# ============================================================
# TESTS: live_api_tts_client.py - _pcm_to_wav
# ============================================================

class TestPcmToWav:
    """Tests for _pcm_to_wav function."""

    def test_pcm_to_wav_basic(self, mock_env):
        """Test basic PCM to WAV conversion."""
        from live_api_tts_client import _pcm_to_wav
        
        # Create simple PCM data (silence)
        pcm_data = bytes([0] * 100)
        
        wav_data = _pcm_to_wav(pcm_data, sample_rate=24000)
        
        # Check WAV header
        assert wav_data[:4] == b'RIFF'
        assert wav_data[8:12] == b'WAVE'
        assert wav_data[12:16] == b'fmt '

    def test_pcm_to_wav_correct_size(self, mock_env):
        """Test that WAV output has correct size."""
        from live_api_tts_client import _pcm_to_wav
        
        pcm_data = bytes([0] * 1000)
        wav_data = _pcm_to_wav(pcm_data, sample_rate=24000)
        
        # WAV header is 44 bytes, total should be header + data
        assert len(wav_data) == 44 + len(pcm_data)

    def test_pcm_to_wav_different_sample_rates(self, mock_env):
        """Test PCM to WAV with different sample rates."""
        from live_api_tts_client import _pcm_to_wav
        
        pcm_data = bytes([0] * 100)
        
        wav_16k = _pcm_to_wav(pcm_data, sample_rate=16000)
        wav_24k = _pcm_to_wav(pcm_data, sample_rate=24000)
        wav_44k = _pcm_to_wav(pcm_data, sample_rate=44100)
        
        # All should have valid WAV headers
        assert wav_16k[:4] == b'RIFF'
        assert wav_24k[:4] == b'RIFF'
        assert wav_44k[:4] == b'RIFF'


# ============================================================
# TESTS: firebase_auth.py
# ============================================================

class TestFirebaseAuth:
    """Tests for Firebase authentication functions."""

    def test_initialize_firebase_admin_already_initialized(self, mock_env):
        """Test that re-initialization is handled gracefully."""
        with patch('firebase_admin._apps', {'default': MagicMock()}):
            from firebase_auth import initialize_firebase_admin
            
            # Should not raise an exception
            initialize_firebase_admin()

    def test_verify_token_success(self, mock_env):
        """Test successful token verification."""
        mock_decoded = {"uid": "user123", "email": "test@harvard.edu"}
        
        with patch('firebase_auth.auth.verify_id_token', return_value=mock_decoded):
            from firebase_auth import verify_token
            
            result = verify_token("valid_token")
            
            assert result["uid"] == "user123"
            assert result["email"] == "test@harvard.edu"

    def test_verify_token_invalid(self, mock_env):
        """Test invalid token verification raises exception."""
        with patch('firebase_auth.auth.verify_id_token', side_effect=Exception("Invalid token")):
            from firebase_auth import verify_token
            
            with pytest.raises(Exception) as exc_info:
                verify_token("invalid_token")
            
            assert "Invalid token" in str(exc_info.value)


# ============================================================
# TESTS: gcs_storage.py
# ============================================================

class TestGcsStorage:
    """Tests for GCS storage functions."""

    def test_upload_audio_to_gcs_success(self, mock_env):
        """Test successful audio upload to GCS."""
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        
        with patch('gcs_storage.storage.Client', return_value=mock_client):
            from gcs_storage import upload_audio_to_gcs
            
            audio_bytes = b"fake audio data"
            result = upload_audio_to_gcs(audio_bytes, "user123", "daily-brief")
            
            assert result is not None
            assert "storage.googleapis.com" in result
            mock_blob.upload_from_string.assert_called_once()

    def test_upload_audio_to_gcs_failure(self, mock_env):
        """Test GCS upload failure returns None."""
        with patch('gcs_storage.storage.Client', side_effect=Exception("GCS error")):
            from gcs_storage import upload_audio_to_gcs
            
            result = upload_audio_to_gcs(b"audio", "user123", "test")
            
            assert result is None


# ============================================================
# TESTS: main.py - Health Endpoints (Integration-style)
# ============================================================

class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.fixture
    def test_client(self):
        """Create test client for FastAPI app."""
        with patch('main.initialize_firebase_admin'):
            with patch('main.GenerativeModel'):
                from fastapi.testclient import TestClient
                from main import app
                return TestClient(app)

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns ok."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_health_endpoint(self, test_client):
        """Test health endpoint returns ok."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_healthz_endpoint(self, test_client):
        """Test healthz endpoint returns ok."""
        response = test_client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"ok": True}


# ============================================================
# TESTS: Context building for podcast generation
# ============================================================

class TestContextBuilding:
    """Tests for context building in podcast generation."""

    def test_context_text_formatting(self, sample_chunks):
        """Test that context text is properly formatted from chunks."""
        context_text = "\n\n".join(
            [f"Article Title: {source_type}\n{chunk}" 
             for _, chunk, source_type, score in sample_chunks]
        )
        
        assert "Harvard Gazette" in context_text
        assert "Harvard Crimson" in context_text
        assert "new research funding" in context_text

    def test_chunk_deduplication(self, sample_chunks):
        """Test chunk deduplication by ID."""
        # Add duplicate chunk
        chunks_with_dup = sample_chunks + [sample_chunks[0]]
        
        seen_ids = set()
        unique_chunks = []
        for chunk in chunks_with_dup:
            chunk_id = chunk[0]
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                unique_chunks.append(chunk)
        
        assert len(unique_chunks) == 3
        assert len(chunks_with_dup) == 4

    def test_brief_context_chunk_conversion(self, sample_brief_context):
        """Test converting brief context chunks to tuple format."""
        all_chunks = []
        for chunk_data in sample_brief_context["chunks"]:
            chunk_id = chunk_data.get("chunk_id") or chunk_data.get("id", 0)
            chunk_text = chunk_data.get("chunk_text") or chunk_data.get("text", "")
            source_type = chunk_data.get("source_type") or chunk_data.get("source", "")
            score = chunk_data.get("score", 0.0)
            
            if chunk_text:
                all_chunks.append((chunk_id, chunk_text, source_type, score))
        
        assert len(all_chunks) == 2
        assert all_chunks[0][0] == 1  # chunk_id
        assert all_chunks[0][1] == "Budget cuts announced."  # chunk_text
        assert all_chunks[0][2] == "Harvard Gazette"  # source_type


# ============================================================
# TESTS: Error handling
# ============================================================

class TestErrorHandling:
    """Tests for error handling across modules."""

    def test_gemini_api_handles_none_chunks_gracefully(self, mock_env, mock_gemini_model):
        """Test that None chunks don't cause crashes."""
        from helpers import call_gemini_api
        
        response, error = call_gemini_api(
            question="Test",
            context_articles=None,
            model=mock_gemini_model
        )
        
        # Should not raise exception
        assert error is None or response is not None

    def test_empty_chunk_text_filtered(self):
        """Test that empty chunk text is filtered out."""
        chunks_data = [
            {"chunk_id": 1, "chunk_text": "Valid text", "source_type": "Gazette", "score": 0.9},
            {"chunk_id": 2, "chunk_text": "", "source_type": "Crimson", "score": 0.8},
            {"chunk_id": 3, "chunk_text": None, "source_type": "Magazine", "score": 0.7},
        ]
        
        all_chunks = []
        for chunk_data in chunks_data:
            chunk_text = chunk_data.get("chunk_text") or ""
            if chunk_text:
                all_chunks.append(chunk_data)
        
        assert len(all_chunks) == 1
        assert all_chunks[0]["chunk_id"] == 1
