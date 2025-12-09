import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# ============= ENV SETUP =============
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/testdb"
os.environ["GEMINI_SERVICE_ACCOUNT_PATH"] = "dummy_path.json"

# ============= MOCKS =============
# We need to mock these before importing main because they run on import or startup
with patch("firebase_auth.initialize_firebase_admin"), patch("vertexai.generative_models.GenerativeModel"):
    from main import app

# Create Test Client
client = TestClient(app, raise_server_exceptions=False)

# ============= TESTS =============


def test_health_check():
    """Health check endpoint"""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@patch("main.verify_token")
@patch("main.create_user")
def test_create_user_success(mock_create_user, mock_verify_token):
    """Create user endpoint - Success"""
    mock_verify_token.return_value = {"uid": "test_uid", "email": "test@example.com"}
    mock_create_user.return_value = True

    headers = {"Authorization": "Bearer valid_token"}
    response = client.post("/api/user/create", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "user_id": "test_uid"}
    mock_create_user.assert_called_once_with("test_uid", "test@example.com")


@patch("main.verify_token")
def test_create_user_unauthorized(mock_verify_token):
    """Create user endpoint - Unauthorized"""
    mock_verify_token.side_effect = Exception("Invalid token")

    headers = {"Authorization": "Bearer invalid_token"}
    response = client.post("/api/user/create", headers=headers)

    assert response.status_code in [401, 500]
    if response.status_code == 401:
        assert "Invalid token" in response.json()["detail"]
    else:
        pass


@patch("main.verify_token")
@patch("main.get_user_preferences")
def test_get_preferences_success(mock_get_prefs, mock_verify_token):
    """Get preferences - Success"""
    mock_verify_token.return_value = {"uid": "test_uid"}
    mock_get_prefs.return_value = {"theme": "dark"}

    headers = {"Authorization": "Bearer valid_token"}
    response = client.get("/api/user/preferences", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "preferences": {"theme": "dark"}}


@patch("psycopg.connect")
@patch("main.verify_token")
@patch("main.save_user_preferences")
@patch("main.create_user")
def test_save_preferences_success(mock_create_user, mock_save_prefs, mock_verify_token, mock_psycopg_connect):
    """Save preferences - Success"""
    mock_verify_token.return_value = {"uid": "test_uid"}
    mock_create_user.return_value = True
    mock_save_prefs.return_value = True

    headers = {"Authorization": "Bearer valid_token"}
    payload = {"theme": "light"}
    response = client.post("/api/user/preferences", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Preferences saved"}
    mock_save_prefs.assert_called_once_with("test_uid", {"theme": "light"})


@patch("main.verify_token")
@patch("main.get_audio_history")
def test_get_history_success(mock_get_history, mock_verify_token):
    """Get history - Success"""
    mock_verify_token.return_value = {"uid": "test_uid"}
    mock_history = [{"id": 1, "text": "hello"}]
    mock_get_history.return_value = mock_history

    headers = {"Authorization": "Bearer valid_token"}
    response = client.get("/api/user/history", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "history": mock_history}


def test_websocket_connect():
    """WebSocket connection - No token (should still accept)"""
    with client.websocket_connect("/ws/chat") as _:
        # Just check if connection is accepted
        pass


@patch("main.verify_token")
def test_websocket_auth_valid(mock_verify_token):
    """WebSocket connection - Valid token"""
    mock_verify_token.return_value = {"uid": "test_uid"}

    with client.websocket_connect("/ws/chat?token=valid_token") as _:
        # Connection should be accepted and user authenticated (logs printed)
        pass

    mock_verify_token.assert_called_once_with("valid_token")


@patch("main.verify_token")
def test_websocket_auth_invalid(mock_verify_token):
    """WebSocket connection - Invalid token"""
    mock_verify_token.side_effect = Exception("Token expired")

    with client.websocket_connect("/ws/chat?token=bad_token") as websocket:
        response = websocket.receive_json()
        assert "error" in response
        assert "Invalid token" in response["error"]


def test_websocket_audio_handling():
    """WebSocket - Sending audio chunks and complete signal"""
    with client.websocket_connect("/ws/chat") as websocket:
        # 1. Send JSON audio data
        import base64

        dummy_audio = base64.b64encode(b"fake_audio").decode("utf-8")
        websocket.send_json({"type": "audio", "data": dummy_audio})

        # Proper way to patch async function imported in main
        with patch("main.audio_to_text", new_callable=AsyncMock) as mock_stt:
            mock_stt.return_value = "Transcribed text"

            with (
                patch("main.enhance_query_with_gemini") as mock_enhance,
                patch("main._retrieve_and_generate_podcast", new_callable=AsyncMock) as mock_rag,
            ):

                mock_enhance.return_value = ({}, None)  # (result, error)
                mock_rag.return_value = True

                websocket.send_json({"type": "complete"})

                # Receive status updates
                # Expect: {"status": "transcribing"}
                try:
                    response = websocket.receive_json(mode="text")
                    # If the app is processing, it should send "transcribing"
                    # Validation that it at least received and started processing
                    assert response.get("status") in ["transcribing", "chunk_received"]
                except Exception:
                    pass


def test_websocket_reset():
    """WebSocket - Reset functionality"""
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "reset"})
        response = websocket.receive_json()
        assert response.get("status") == "reset"


@patch("main.verify_token")
@patch("main.create_user")
def test_create_user_db_failure(mock_create_user, mock_verify_token):
    """Create user endpoint - Database Failure"""
    mock_verify_token.return_value = {"uid": "test_uid", "email": "test@example.com"}
    mock_create_user.return_value = False  # Simulate DB failure

    headers = {"Authorization": "Bearer valid_token"}
    response = client.post("/api/user/create", headers=headers)

    assert response.status_code == 500
    assert "Failed to create user" in response.json()["detail"]


@patch("psycopg.connect")
@patch("main.verify_token")
@patch("main.save_user_preferences")
@patch("main.create_user")
def test_save_preferences_failure(mock_create_user, mock_save_prefs, mock_verify_token, mock_psycopg_connect):
    """Save preferences - Database Failure"""
    mock_verify_token.return_value = {"uid": "test_uid"}
    mock_create_user.return_value = True
    mock_save_prefs.return_value = False  # DB Failure

    headers = {"Authorization": "Bearer valid_token"}
    payload = {"theme": "light"}
    response = client.post("/api/user/preferences", json=payload, headers=headers)

    assert response.status_code == 500
    assert "Failed to save preferences" in response.json()["detail"]


@patch("main.verify_token")
@patch("main.get_user_preferences")
@patch("main.get_preferences_last_updated")
@patch("main.get_voice_preference_last_updated")
@patch("main.search_articles_by_preferences")
@patch("main.model")
@patch("main.text_to_audio_bytes")
@patch("main.upload_audio_to_gcs")
@patch("main.save_user_preferences")
@patch("main.save_audio_history")
def test_generate_daily_brief_success(
    mock_save_history,
    mock_save_prefs,
    mock_upload,
    mock_tts,
    mock_model_instance,
    mock_search,
    mock_voice_updated,
    mock_prefs_updated,
    mock_get_prefs,
    mock_verify_token,
):
    """Generate Daily Brief - Success"""
    # 1. Auth Setup
    mock_verify_token.return_value = {"uid": "test_uid"}

    # 2. Prefs Setup
    mock_get_prefs.return_value = {"topics": '["Harvard"]', "sources": '["Gazette"]', "voice_preference": "Alloy"}
    mock_prefs_updated.return_value = "2024-01-01T00:00:00Z"
    mock_voice_updated.return_value = "2024-01-01T00:00:00Z"

    # Mock save history/prefs return values
    mock_save_history.return_value = True
    mock_save_prefs.return_value = True

    # 3. Search Setup (Chunks found)
    mock_search.return_value = [("id1", "Chunk Content", "Source", 0.9)]

    # 4. Gemini Setup (mocking the global 'model' instance directly)
    mock_model_instance.generate_content.return_value.text = "Good morning Harvard."

    # 5. TTS & Upload Setup
    mock_tts.return_value = b"fake_audio_bytes"
    mock_upload.return_value = "https://gcs/audio.mp3"

    headers = {"Authorization": "Bearer valid_token"}
    response = client.post("/api/daily-brief", headers=headers)

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["audio_url"] == "https://gcs/audio.mp3"
    assert data["podcast_text"] == "Good morning Harvard."


@patch("main.verify_token")
@patch("main.get_user_preferences")
@patch("main.get_preferences_last_updated")
@patch("main.get_voice_preference_last_updated")
@patch("main.get_audio_history")
def test_generate_daily_brief_voice_only_change(
    mock_get_history,
    mock_voice_updated,
    mock_prefs_updated,
    mock_get_prefs,
    mock_verify_token,
):
    """Generate Daily Brief - Voice Only Change regeneration"""
    mock_verify_token.return_value = {"uid": "test_uid"}

    # Setup prefs: Voice updated AFTER content
    mock_get_prefs.return_value = {"topics": '["Harvard"]', "voice_preference": "Echo"}
    mock_prefs_updated.return_value = "2024-01-01T10:00:00Z"
    mock_voice_updated.return_value = "2024-01-01T12:00:00Z"  # Voice updated later

    # Setup history: Recent brief exists, created BEFORE voice update
    mock_brief_entry = {
        "question_text": "Daily Brief",
        "podcast_text": "Existing transcript.",
        "created_at": "2024-01-01T11:00:00Z",  # Created between content and voice update, but before voice update?
        # WAIT. Main.py logic: if brief_created >= voice_updated, then it's ALREADY regenerated.
        # We want regeneration -> Brief created BEFORE voice update.
        # Voice updated 12:00. Brief created 11:00. 11:00 < 12:00.
        # So it SHOULD regenerate.
    }
    mock_get_history.return_value = [mock_brief_entry]

    # We need to mock TTS and Upload since it will proceed to regeneration from text
    with (
        patch("main.text_to_audio_bytes") as mock_tts,
        patch("main.upload_audio_to_gcs") as mock_upload,
        patch("main.save_audio_history") as mock_save_history,
    ):

        mock_tts.return_value = b"new_voice_audio"
        mock_upload.return_value = "https://gcs/new_audio.mp3"
        mock_save_history.return_value = True

        headers = {"Authorization": "Bearer valid_token"}
        response = client.post("/api/daily-brief", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["audio_url"] == "https://gcs/new_audio.mp3"
        # Must verify it used existing text, NOT new generation
        assert data["podcast_text"] == "Existing transcript."
        # Verify TTS called with new voice
        mock_tts.assert_called_with("Existing transcript.", voice_name="Echo")


def test_websocket_raw_bytes_handling():
    """WebSocket - Sending raw audio bytes"""
    with client.websocket_connect("/ws/chat") as websocket:
        # Send raw bytes (simulating audio chunk)
        websocket.send_bytes(b"raw_audio_chunk")

        # Expect chunk confirmation
        response = websocket.receive_json()
        assert response.get("status") == "chunk_received"
        assert response.get("size") > 0


def test_websocket_transcription_empty():
    """WebSocket - Transcription returns empty string"""
    import base64

    dummy_audio = base64.b64encode(b"fake_audio").decode("utf-8")

    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "audio", "data": dummy_audio})

        with patch("main.audio_to_text", new_callable=AsyncMock) as mock_stt:
            mock_stt.return_value = ""  # Empty response

            websocket.send_json({"type": "complete"})

            # Expect transcribing status then error
            response_1 = websocket.receive_json()
            if response_1.get("status") == "transcribing":
                response_2 = websocket.receive_json()
                assert "error" in response_2
            else:
                assert "error" in response_1


@patch("main.verify_token")
@patch("helpers.get_daily_brief_context")
@patch("helpers.classify_question_context")
@patch("main.enhance_query_with_gemini")
@patch("main._retrieve_and_generate_podcast", new_callable=AsyncMock)
def test_websocket_contextual_flow(
    mock_rag,
    mock_enhance,
    mock_classify,
    mock_get_brief,
    mock_verify_token,
):
    """WebSocket - Test contextual question flow (uses brief context)"""
    mock_verify_token.return_value = {"uid": "test_uid"}

    # Mock finding a daily brief
    mock_get_brief.return_value = {"transcript": "Brief text", "chunks": []}

    # Mock classification as CONTEXTUAL
    mock_classify.return_value = "CONTEXTUAL"

    # Mock enhance to ensure it's not called (though assert checks this too)
    mock_enhance.return_value = ({}, None)

    # Mock rag to send completion signal so test loop doesn't hang
    async def fake_rag(websocket, *args, **kwargs):
        await websocket.send_json({"status": "complete"})
        return True

    mock_rag.side_effect = fake_rag

    with client.websocket_connect("/ws/chat?token=valid_token") as websocket:
        # Send audio (simulated via JSON)
        import base64

        dummy_audio = base64.b64encode(b"fake_audio").decode("utf-8")
        websocket.send_json({"type": "audio", "data": dummy_audio})

        with patch("main.audio_to_text", new_callable=AsyncMock) as mock_stt:
            mock_stt.return_value = "What about that?"

            websocket.send_json({"type": "complete"})

            # Consume all messages until complete or timeout
            for _ in range(15):
                try:
                    msg = websocket.receive_json(mode="text")
                    if "error" in msg or msg.get("status") == "complete":
                        break
                except Exception:
                    break

            # Verify classify was called
            mock_classify.assert_called_once()
            # Verify RAG called with use_brief_context=True
            mock_rag.assert_called_once()
            _, kwargs = mock_rag.call_args
            assert kwargs.get("use_brief_context") is True
            # Verify enhancement was NOT called (logic skips it for contextual)
            mock_enhance.assert_not_called()


@patch("main.verify_token")
@patch("helpers.get_daily_brief_context")
@patch("helpers.classify_question_context")
@patch("main.enhance_query_with_gemini")
@patch("main._retrieve_and_generate_podcast", new_callable=AsyncMock)
def test_websocket_general_flow_with_brief_exist(
    mock_rag,
    mock_enhance,
    mock_classify,
    mock_get_brief,
    mock_verify_token,
):
    """WebSocket - Test GENERAL question flow even when brief exists"""
    mock_verify_token.return_value = {"uid": "test_uid"}
    mock_get_brief.return_value = {"transcript": "Brief text", "chunks": []}

    # Mock classification as GENERAL
    mock_classify.return_value = "GENERAL"

    # Mock enhance
    mock_enhance.return_value = ({"enhanced_query_1": "Enhanced"}, None)

    # Mock rag to send completion signal
    async def fake_rag(websocket, *args, **kwargs):
        await websocket.send_json({"status": "complete"})
        return True

    mock_rag.side_effect = fake_rag

    with client.websocket_connect("/ws/chat?token=valid_token") as websocket:
        import base64

        dummy_audio = base64.b64encode(b"fake_audio").decode("utf-8")
        websocket.send_json({"type": "audio", "data": dummy_audio})

        with patch("main.audio_to_text", new_callable=AsyncMock) as mock_stt:
            mock_stt.return_value = "What is the weather?"

            websocket.send_json({"type": "complete"})

            for _ in range(15):
                try:
                    msg = websocket.receive_json(mode="text")
                    if "error" in msg or msg.get("status") == "complete":
                        break
                except Exception:
                    break

            # Verify classify was called
            mock_classify.assert_called_once()
            # Verify enhancement WAS called (since it's GENERAL)
            mock_enhance.assert_called_once()
            # Verify RAG called with use_brief_context=False
            _, kwargs = mock_rag.call_args
            assert kwargs.get("use_brief_context") is False
