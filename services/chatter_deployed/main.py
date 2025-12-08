"""
main.py

Main app file for chatter service as a FastAPI

ENDPOINTS CONTAINED:

@app.get("/health")
For checking whether the app works

@app.post("/api/chatter")
Main chatter endpoint: calls the chatter() function.

@app.websocket("/ws/chat")

@app.post("/api/user/create")

@app.get("/api/user/preferences")

@app.post("/api/user/preferences")

@app.get("/api/user/history")

class FirebaseAuthMiddleware(BaseHTTPMiddleware):



"""

# load_dotenv()  # This loads .env file
from dotenv import load_dotenv
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# uploadfile handels audio file auploads from frontend
from fastapi import (
    FastAPI,
    Body,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)

# from fastapi.responses import StreamingResponse
# streaming response stream audio chunks back to frontend
from speech_to_text_client import audio_to_text  # Speech-to-Text function
from text_to_speech_client import text_to_audio_stream, text_to_audio_bytes  # Google Cloud Text-to-Speech streaming and non-streaming
from gcs_storage import upload_audio_to_gcs  # GCS storage for audio files
from fastapi.middleware.cors import CORSMiddleware
import json
import base64
from firebase_auth import initialize_firebase_admin, verify_token
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from user_db import (
    create_user,
    get_user_preferences,
    save_user_preferences,
    save_audio_history,
    get_audio_history,
    get_preferences_last_updated,
    get_voice_preference_last_updated,
)

# importing helper functions
# from chatter_handler import chatter [Z] we do not need the chatter_handler.py script
from helpers import call_retriever_service, call_gemini_api
from query_enhancement import enhance_query_with_gemini
from retriever import search_articles_by_preferences

# from chatter_handler import model
# from openai import OpenAI [Z] we do not use OpenAI
from vertexai.generative_models import (
    GenerativeModel,
)  # [Z] initialize Gemini model instance


# --------------------------
# Config
# --------------------------

load_dotenv()
ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://www.newsjuiceapp.com").split(",")

# --------------------------
# Gemini Config
# --------------------------
GEMINI_SERVICE_ACCOUNT_PATH = os.environ.get("GEMINI_SERVICE_ACCOUNT_PATH", "/secrets/gemini-service-account.json")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

# --------------------------
# App / Clients
# --------------------------
logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
    allow_credentials=True,  # Required for Authorization header
)
try:
    initialize_firebase_admin()
except Exception as e:
    print(
        f"[firebase-admin-warning] Firebase Admin not initialized: {e}\n"
        "[firebase-admin-warning] Authentication will not work until Firebase Admin is configured"
    )


# --------------------------
# Initialize Gemini Model 
# --------------------------
#try:
#    if os.path.exists(GEMINI_SERVICE_ACCOUNT_PATH):
#        # set credentials file path for Vertex AI
#        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GEMINI_SERVICE_ACCOUNT_PATH
#
#        # initialize model
#        model = GenerativeModel(
#            model_name=(
#                f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_REGION}/"
#                "publishers/google/models/gemini-2.5-flash"
#            )
#        )
#    else:
#        model = None
#except Exception as e:
#    print(f"[gemini-error] Failed to configure service account: {e}")
#    model = None



# --------------------------------------------
# Initialize Gemini Model _ WORKLOAD IDENTITY
# -------------------------------------------
try:
    # Use default credentials (Workload Identity in GKE, service account in Cloud Run)
    model = GenerativeModel(model_name="gemini-2.5-flash")
    print("[gemini] Model initialized with default credentials")
except Exception as e:
    print(f"[gemini-error] Failed to initialize model: {e}")
    model = None
# --------------------------
# Health
# --------------------------

@app.get("/")
async def root() -> Dict[str, bool]:
    return {"ok": True}

@app.get("/healthz")
async def healthz_root() -> Dict[str, bool]:
    return {"ok": True}

@app.get("/health")
async def health_check() -> Dict[str, bool]:
    return {"ok": True}

# --------------------------
# Helper Functions
# --------------------------
# [Z]
async def _retrieve_and_generate_podcast(
    websocket: WebSocket,
    enhanced_queries: Dict[str, str],
    # dictionary w/ string keys and string values (each enhanced query)
    original_query: str,
    user_id: Optional[str],
    model: GenerativeModel,
    use_brief_context: bool = False,  # NEW: Whether to use daily brief context
    brief_context: Optional[Dict] = None,  # NEW: Daily brief context if available
):
    """Retrieve chunks and generate podcast for normal flow and query enhancement."""

    # Extract all enhanced_query_N keys and sort them
    query_keys = sorted([k for k in enhanced_queries.keys() if k.startswith("enhanced_query_")])

    # ========== NEW: USE BRIEF CONTEXT IF CONTEXTUAL QUESTION ==========
    if use_brief_context and brief_context:
        print("[websocket] Using daily brief context for contextual question")

        # Debug logging for brief_context structure
        print(f"[context-debug] brief_context keys: {brief_context.keys()}")
        print(f"[context-debug] Number of chunks in brief_context: {len(brief_context.get('chunks', []))}")
        if brief_context.get("chunks"):
            first_chunk = brief_context["chunks"][0]
            print(f"[context-debug] First chunk keys: {first_chunk.keys()}")
            print(f"[context-debug] First chunk sample: {first_chunk}")

        # Start with chunks from daily brief
        all_chunks = []
        for chunk_data in brief_context["chunks"]:
            # Handle both possible key naming conventions
            chunk_id = chunk_data.get("chunk_id") or chunk_data.get("id", 0)
            chunk_text = chunk_data.get("chunk_text") or chunk_data.get("text", "")
            source_type = chunk_data.get("source_type") or chunk_data.get("source", "")
            score = chunk_data.get("score", 0.0)

            if not chunk_text:
                print(f"[context-warning] Empty chunk_text for chunk_id {chunk_id}")
                continue  # Skip empty chunks

            # Convert back to tuple format: (id, chunk_text, source_type, score)
            all_chunks.append((chunk_id, chunk_text, source_type, score))

        print(f"[retriever] Using {len(all_chunks)} chunks from daily brief")
        print(f"[context-debug] Converted {len(all_chunks)} chunks to tuple format")
        if all_chunks:
            print(f"[context-debug] First converted chunk: {all_chunks[0]}")
            print(f"[context-debug] First chunk tuple length: {len(all_chunks[0])}")

        # OPTIONAL: Add a few more chunks from fresh retrieval as fallback
        # This ensures we have backup if brief chunks don't fully answer
        # await websocket.send_json({"status": "retrieving_additional"})
        # for query_key in query_keys:
        #     sub_query = enhanced_queries[query_key]
        #     fresh_chunks = call_retriever_service(sub_query, limit=5)  # Fewer chunks
        #     if fresh_chunks:
        #         print(f"[retriever] Adding {len(fresh_chunks)} fresh chunks as fallback")
        #         all_chunks.extend(fresh_chunks)

        # Deduplicate
        seen_ids = set()
        unique_chunks = []
        for chunk in all_chunks:
            chunk_id = chunk[0]
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                unique_chunks.append(chunk)
        all_chunks = unique_chunks

    else:
        # GENERAL QUESTION: Use full retrieval pipeline (existing behavior)
        print("[websocket] Using full retrieval for general question")
        await websocket.send_json({"status": "retrieving"})
        all_chunks = []

        # [Z] assume each sub query runs cosine similarity against the DB to pull chunks
        for query_key in query_keys:
            sub_query = enhanced_queries[query_key]
            print(f"[retriever] Running retrieval for sub-query: {sub_query[:50]}...")
            chunks = call_retriever_service(sub_query)
            if chunks:
                # Print each chunk with its similarity score
                print(f"[retriever] Found {len(chunks)} chunks for '{query_key}':")
                for i, (chunk_id, chunk_text, source_type, score) in enumerate(chunks):
                    print(f"  Chunk {i+1} (ID: {chunk_id}, Source: {source_type}, Score: {score:.4f}): {chunk_text[:100]}...")
                all_chunks.extend(chunks)

        # Remove duplicates based on chunk ID (keep first occurrence)
        seen_ids = set()
        unique_chunks = []
        for chunk in all_chunks:
            chunk_id = chunk[0]  # First element is the ID
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                unique_chunks.append(chunk)
        # makes sense to only have the unique chunks for all enhanced queries
        all_chunks = unique_chunks

    # Print summary of final unique chunks
    print(f"[retriever] After deduplication: {len(all_chunks)} unique chunks")
    for i, (chunk_id, chunk_text, source_type, score) in enumerate(all_chunks):
        print(f"  Final Chunk {i+1} (ID: {chunk_id}, Source: {source_type}, Score: {score:.4f}): {chunk_text}...")

    if not all_chunks:
        await websocket.send_json({"warning": "No relevant articles found"})

    # step 3: call_gemini_api to generate podcast text with all combined chunks
    await websocket.send_json({"status": "generating"})
    # [Z] assuming we combine all these chunks + sub-queries for the podcast generation
    # Combine all enhanced sub-queries for podcast generation
    combined_enhanced_query = "\n".join([enhanced_queries[k] for k in query_keys])
    print(f"This is the enhanced query {combined_enhanced_query}")

    podcast_text, error = call_gemini_api(combined_enhanced_query, all_chunks, model)
    print(f"Here is the Podcast Text {podcast_text}")

    if error or not podcast_text:
        await websocket.send_json({"error": f"LLM error: {error}"})
        return False

    await websocket.send_json({"status": "podcast_generated", "text": podcast_text})

    # step4: convert podcast text to audio
    await websocket.send_json({"status": "converting_to_audio"})
    try:
        # Get user's voice preference if authenticated
        voice_preference = None
        if user_id:
            preferences = get_user_preferences(user_id)
            voice_preference = preferences.get("voice_preference", "en-US-Studio-O")
            print(f"[websocket] Using voice preference: {voice_preference}")
        
        await websocket.send_json({"status": "streaming_audio"})
        result = await text_to_audio_stream(podcast_text, websocket, voice_name=voice_preference)

        if not result:
            await websocket.send_json({"error": "Failed to generate audio stream"})
            return False

        await websocket.send_json({"status": "complete"})

        # Save audio history if user is authenticated
        # [Z] For Q&A we don't save audio to GCS (just the text)

        if user_id:
            save_audio_history(
                user_id=user_id,
                question_text=original_query,
                podcast_text=podcast_text,
                audio_url=None,
            )
            print(f"[websocket] Audio history saved for user: {user_id}")

    except Exception as e:
        await websocket.send_json({"error": f"TTS failed: {str(e)}"})
        return False

    return True


# ------------
# Websocket Audio Endpoint
# ------------
# WebSocket route decorator
# /ws/chat - WebSocket endpoint path
@app.websocket("/ws/chat")
async def websocket_chatter(websocket: WebSocket):
    """WebSocket endpoint for real-time audio streaming.

    Protocol:
    - Frontend sends audio chunks as bytes OR JSON with base64 audio
    - Frontend sends {"type": "complete"} when audio is done
    - Backend sends status updates as JSON
    - Backend streams audio response as bytes
    """
    await websocket.accept()

    # get token from query params
    token = websocket.query_params.get("token")
    user_id = None

    if token:
        try:
            decoded_token = verify_token(token)
            user_id = decoded_token["uid"]
            print(f"[websocket] Authenticated user: {user_id}")
        except Exception as e:
            print(f"[websocket-error] Token verification failed: {e}")
            import traceback

            traceback.print_exc()
            await websocket.send_json({"error": f"Invalid token: {str(e)}"})
            await websocket.close()
            return
    else:
        print("[websocket-warning] No token provided, proceeding without auth")

    # Now you have user_id available for the rest of the WebSocket handler
    # Use it to save to CloudSQL:
    # - Save audio history with user_id
    # - Load user preferences with user_id

    audio_buffer = bytearray()  # bytearray data structure is what will hold our audio chunks
    # tts_client = OpenAI()  # Initialize once, reuse in loop
    is_processing = False  # what this is checking is that the backend is already
    # transcribing/generating a response

    try:
        while True:
            # receive audio chunks from frontend
            # data = await websocket.receive_bytes()
            # OR if frontedn sends JSON with audio data
            message = await websocket.receive()
            # the way websocket works is via receiving messages. the backend
            # waits to receive a message from the frontend
            # it could be raw audio bytes, or a JSON message
            if message["type"] == "websocket.receive":  # this is the backend confirming
                # it is a receive event from the frontend

                # handle raw audio bytes
                if "bytes" in message:
                    # if we're processing a previous request, ignore new audio chunks. avoid
                    # overstuffing the audio bujffer
                    if is_processing:
                        print("[websocket] Ignoring audio chunk - still processing previous request")
                        continue
                    chunk_size = len(message["bytes"])
                    audio_buffer.extend(
                        message["bytes"]
                    )  # each audio chunk is appended to this audio_buffer byte array
                    print(
                        "[websocket] Received audio chunk:"
                        f" {chunk_size} bytes, total buffer: {len(audio_buffer)} bytes"
                    )
                    await websocket.send_json({"status": "chunk_received", "size": len(audio_buffer)})

                # Handle JSON control messages
                elif "text" in message:
                    try:
                        data = json.loads(message["text"])
                        print(f"[websocket] Received JSON message: {data}")

                        if data.get("type") == "complete":
                            # Check if we're already processing
                            if is_processing:
                                print("[websocket] Already processing a request, " "ignoring new complete signal")
                                continue
                                
                            # Check if we have audio to process
                            if len(audio_buffer) == 0:
                                print("[websocket] ERROR: No audio received in buffer!")
                                print("[websocket] ERROR: No audio received in buffer!")
                                await websocket.send_json({"error": "No audio received"})
                                continue

                            is_processing = True
                            print(
                                f"""[websocket] Received complete signal, audio buffer size:
                                {len(audio_buffer)} bytes"""
                            )

                            # Step 1: Convert audio to text
                            await websocket.send_json({"status": "transcribing"})
                            # send_json sends a JSON message from backend to frontend
                            # via frontend connection
                            print("[websocket] Starting transcription...")  # backend status print

                            try:
                                # audio_to_text again is the speech_to_text_client.py file,
                                # that converts our frontend audio to text. the transcribed text is
                                # the output from audio_to_text.
                                text = await audio_to_text(
                                    bytes(audio_buffer)
                                )  # and we feed audio_buffer, our chunks of audio, into the
                                # function as input
                                # I think this is what shows up in the backend terminal once the
                                # transcription is complete
                                # so we can monitor progress
                                preview = text[:100] if text else "None"
                                print(f"[websocket] Transcription complete, text: {preview}...")
                            except Exception as e:
                                print(f"[websocket] Transcription error: {e}")
                                await websocket.send_json({"error": f"Transcription failed: {str(e)}"})
                                audio_buffer.clear()
                                is_processing = False
                                continue

                            if not text:
                                await websocket.send_json({"error": "Failed to transcribe audio (empty response)"})
                                audio_buffer.clear()
                                is_processing = False
                                continue
                            # websocket.send_json updates the frontend, status message via websocket
                            # frontend receives this and updates the UI
                            await websocket.send_json({"status": "transcribed", "text": text})

                            # ========== NEW: CHECK FOR DAILY BRIEF CONTEXT ==========
                            daily_brief_id = data.get("daily_brief_id")  # Frontend will send this
                            brief_context = None
                            use_brief_context = False

                            if daily_brief_id or user_id:  # Fallback: fetch by user_id if no ID provided
                                print("[websocket] Checking for daily brief context...")
                                from helpers import get_daily_brief_context
                                brief_context = get_daily_brief_context(user_id)

                                if brief_context:
                                    print(f"[websocket] Found daily brief context: {len(brief_context['chunks'])} chunks")
                                else:
                                    print("[websocket] No daily brief context found for today")

                            # ========== CLASSIFY QUESTION IF BRIEF CONTEXT EXISTS ==========
                            if brief_context:
                                await websocket.send_json({"status": "classifying_question"})
                                from helpers import classify_question_context
                                classification = classify_question_context(text, brief_context["transcript"], model)
                                print(f"\n{'='*60}")
                                print(f"[CLASSIFICATION RESULT] {classification}")
                                print(f"{'='*60}\n")

                                if classification == "CONTEXTUAL":
                                    use_brief_context = True
                                    await websocket.send_json({"status": "using_brief_context"})

                            # NEW STEP: Query Enhancement - conditional based on question type
                            original_query = text  # Keep original for podcast generation

                            if use_brief_context:
                                # CONTEXTUAL question - use original query, no enhancement
                                # Preserves brief-specific references like "what did you say about..."
                                print("\n[STRATEGY] CONTEXTUAL QUESTION - Using daily brief chunks (no query enhancement)")
                                print(f"[STRATEGY] Original query: {text}\n")
                                enhanced_queries = {"enhanced_query_1": text}
                            else:
                                # GENERAL question - enhance query for better retrieval
                                print("\n[STRATEGY] GENERAL QUESTION - Using full retrieval pipeline with query enhancement\n")
                                await websocket.send_json({"status": "enhancing_query"})
                                print("[websocket] Enhancing query for general question...")

                                # Enhance the query once
                                enhancement_result, error = enhance_query_with_gemini(text, model)

                                if error or not enhancement_result:
                                    print("[websocket] Query enhancement error:" f" {error}, using original query")
                                    # Use original query as single sub-query if enhancement fails
                                    enhanced_queries = {"enhanced_query_1": text}
                                else:
                                    # Extract all enhanced_query_N keys from the result
                                    enhanced_queries = {
                                        k: v for k, v in enhancement_result.items() if k.startswith("enhanced_query_")
                                    }
                                    if not enhanced_queries:
                                        # Fallback if format is unexpected
                                        enhanced_queries = {
                                            "enhanced_query_1": enhancement_result.get("enhanced_query", text)
                                        }
                                    print("[websocket] Query enhanced into" f" {len(enhanced_queries)} sub-queries")

                            # Use the helper function to retrieve and generate podcast
                            success = await _retrieve_and_generate_podcast(
                                websocket,
                                enhanced_queries,
                                original_query,
                                user_id,
                                model,
                                use_brief_context=use_brief_context,  # NEW: Pass context flag
                                brief_context=brief_context,  # NEW: Pass daily brief context
                            )

                            if not success:
                                audio_buffer.clear()
                                is_processing = False
                                continue

                            # Reset buffer for next request
                            audio_buffer.clear()
                            is_processing = False
                            print("[websocket] Request processing complete, ready for next" " recording")

                        elif data.get("type") == "audio":
                            # JSON with base64 audio data
                            audio_bytes = base64.b64decode(data["data"])
                            audio_buffer.extend(audio_bytes)

                        elif data.get("type") == "reset":
                            # Frontend wants to reset
                            audio_buffer.clear()
                            is_processing = False
                            await websocket.send_json({"status": "reset"})
                            print("[websocket] Reset signal, cleared buffer & processing flag")

                    except json.JSONDecodeError:
                        await websocket.send_json({"error": "Invalid JSON"})
                    except Exception as e:
                        await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        print("[websocket] Client disconnected")
    except Exception as e:
        print(f"[websocket-error] {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass


# --------------------------
# Main Endpoint
# --------------------------
# [Z] we do not need this /api/chatter endpoint
# @app.post("/api/chatter")
# async def chatter_endpoint(payload: Dict[str, Any] = Body(...)):
#     return await chatter(payload)


# ----------------------
# Firebase middleware class
# ----------------------
class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate Firebase tokens for protected routes."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for OPTIONS (CORS preflight) requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for health check and public endpoints
        # CHANGE CM - if request.url.path in ["/", "/healthz", "/docs", "/openapi.json"]:
        if request.url.path in ["/", "/health", "/healthz", "/api/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # WebSocket handles auth separately (see below)
        if request.url.path.startswith("/ws/"):
            return await call_next(request)

        # Get token from header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        token = auth_header.split("Bearer ")[1]

        try:
            # Verify token
            decoded_token = verify_token(token)
            user_id = decoded_token["uid"]

            # Attach user info to request state
            request.state.user_id = user_id
            request.state.user_email = decoded_token.get("email")

        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

        return await call_next(request)


# Add middleware to app
app.add_middleware(FirebaseAuthMiddleware)


@app.post("/api/user/create")
async def create_user_endpoint(request: Request):
    "create new user in CloudSQL after FIrebase registration"
    try:
        user_id = request.state.user_id
        user_email = request.state.user_email
        success = create_user(user_id, user_email)
        if success:
            return {"status": "success", "user_id": user_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to create user")
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")


@app.get("/api/user/preferences")
async def get_preferences_endpoint(request: Request):
    """Get user preferences."""
    try:
        user_id = request.state.user_id
        preferences = get_user_preferences(user_id)
        return {"status": "success", "preferences": preferences}
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")

#Z [ save user preferences endpoint] its an endpoint because its a separate resource
# CRUD operations; GET /api/user/preferences = read preferences, POST /api/user/preferences = Create/Update preferences
# DELETE /api/user/preferences = could delete preferences 
# we have separate endpoints for /api/users (users mgtmt) /api/articles (aticles management) and /api/daily-brief 
#separate user preferences endpoint from daily brief because user may want to change preferences without generating a dialy brief
@app.post("/api/user/preferences")
async def save_preferences_endpoint(request: Request, preferences: Dict[str, Any] = Body(...)):
    """Save user preferences."""
    try:
        user_id = request.state.user_id
        user_email = request.state.user_email

        # Ensure user exists in database (fallback in case frontend call failed)
        # This uses ON CONFLICT DO NOTHING, so it's safe to call even if user exists
        create_user(user_id, user_email)

        #[Z] this saves the user preferences in our user_preferences table in CloudSQL
#         user_id  | preference_key | preference_value
#    ---------|----------------|------------------
#    abc123   | topics         | ["Politics","Tech"]
#    abc123   | sources        | ["Harvard Gazette"]
        success = save_user_preferences(user_id, preferences)
        if success:
            return {"status": "success", "message": "Preferences saved"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save preferences")
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")


@app.get("/api/user/history")
async def get_history_endpoint(request: Request, limit: int = 10):
    """Get user's audio history."""
    try:
        user_id = request.state.user_id
        history = get_audio_history(user_id, limit)
        return {"status": "success", "history": history}
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")


# --------------------------
# Daily Brief Endpoints
# --------------------------

@app.post("/api/daily-brief")
async def generate_daily_brief_endpoint(request: Request):
    """Generate a personalized daily news briefing based on user preferences.
    
    If only voice preference changed (not topics/sources), regenerates audio from existing transcript.
    Otherwise, generates a new transcript and audio.
    """
    try:
        user_id = request.state.user_id
        print(f"[daily-brief] Generating for user: {user_id}")

        # Load user preferences from user_preferences table in CloudSQL
        #  (this function comes from the user_db.py script)
        preferences = get_user_preferences(user_id)
        
        # Check if only voice preference changed (not topics/sources)
        # We check by comparing when voice was updated vs when content preferences were updated
        # If voice was updated more recently than content preferences, it's a voice-only change
        content_prefs_updated = get_preferences_last_updated(user_id)
        voice_pref_updated = get_voice_preference_last_updated(user_id)
        
        voice_only_change = False
        if voice_pref_updated:
            try:
                voice_updated = datetime.fromisoformat(voice_pref_updated.replace('Z', '+00:00'))
                
                # If content preferences exist, compare timestamps
                if content_prefs_updated:
                    content_updated = datetime.fromisoformat(content_prefs_updated.replace('Z', '+00:00'))
                    # Voice updated more recently than content = voice only change
                    if voice_updated > content_updated:
                        voice_only_change = True
                        print(f"[daily-brief] Only voice preference changed (voice: {voice_updated}, content: {content_updated}), will regenerate audio from existing transcript")
                else:
                    # No content preferences exist, check if there's a recent brief to regenerate
                    # If voice was updated and we have a brief from today, it's likely a voice-only change
                    last_generated_str = preferences.get("last_daily_brief_generated")
                    if last_generated_str:
                        last_generated = datetime.fromisoformat(last_generated_str.replace('Z', '+00:00'))
                        today = datetime.now(timezone.utc).date()
                        last_date = last_generated.date()
                        # If brief was generated today and voice was updated, assume voice-only change
                        if last_date == today:
                            voice_only_change = True
                            print(f"[daily-brief] Voice preference changed (no content prefs, brief from today), will regenerate audio from existing transcript")
            except (ValueError, AttributeError) as e:
                print(f"[daily-brief] Error parsing timestamps: {e}")
                pass
        
        # If only voice changed, get latest transcript and regenerate audio
        if voice_only_change:
            # Get the most recent daily brief transcript
            history = get_audio_history(user_id, limit=50)
            daily_briefs = [h for h in history if h.get("question_text") == "Daily Brief"]
            
            if daily_briefs and daily_briefs[0].get("podcast_text"):
                latest_brief = daily_briefs[0]
                
                # Check if we've already regenerated audio for this voice change
                # If the brief's created_at is after the voice preference was updated, we've already handled it
                if voice_pref_updated and latest_brief.get("created_at"):
                    try:
                        voice_updated = datetime.fromisoformat(voice_pref_updated.replace('Z', '+00:00'))
                        brief_created = datetime.fromisoformat(latest_brief.get("created_at").replace('Z', '+00:00'))
                        
                        # If brief was created after voice was updated, we've already regenerated it
                        if brief_created >= voice_updated:
                            print(f"[daily-brief] Audio already regenerated for current voice preference (brief: {brief_created}, voice updated: {voice_updated})")
                            # Return the existing brief without regenerating
                            return {
                                "success": True,
                                "podcast_text": latest_brief.get("podcast_text"),
                                "audio_url": latest_brief.get("audio_url"),
                                "created_at": latest_brief.get("created_at"),
                                "voice_only_update": False,  # Already handled
                                "already_regenerated": True
                            }
                    except (ValueError, AttributeError) as e:
                        print(f"[daily-brief] Error comparing timestamps, proceeding with regeneration: {e}")
                        pass
                
                podcast_text = latest_brief.get("podcast_text")
                print(f"[daily-brief] Using existing transcript ({len(podcast_text)} chars)")
                
                # Regenerate audio with new voice
                voice_preference = preferences.get("voice_preference", "en-US-Studio-O")
                print(f"[daily-brief] Regenerating audio with voice: {voice_preference}")
                audio_bytes = text_to_audio_bytes(podcast_text, voice_name=voice_preference)
                
                if not audio_bytes:
                    raise HTTPException(status_code=500, detail="Failed to generate audio from text")
                
                # Upload new audio
                audio_url = upload_audio_to_gcs(audio_bytes, user_id, filename_prefix="daily-brief")
                
                if not audio_url:
                    raise HTTPException(status_code=500, detail="Failed to upload audio to storage")
                
                # Update the existing audio_history entry with new audio URL
                # Note: We keep the same transcript but update the audio
                # Since save_audio_history creates a new entry, we'll create a new entry
                # but this is fine - it shows the voice change in history
                source_chunks = latest_brief.get("source_chunks")
                # Ensure source_chunks is a string (it might already be JSON string from DB)
                if isinstance(source_chunks, dict):
                    source_chunks = json.dumps(source_chunks)
                elif source_chunks is None:
                    source_chunks = None
                # If it's already a string, use it as-is
                
                save_audio_history(
                    user_id=user_id,
                    question_text="Daily Brief",
                    podcast_text=podcast_text,
                    audio_url=audio_url,
                    source_chunks=source_chunks  # Keep same chunks
                )
                
                # Don't update last_daily_brief_generated timestamp for voice-only changes
                # This allows subsequent calls to still detect voice-only changes
                # We only update it for full regenerations
                # Use the existing last_generated timestamp for the response
                last_generated_str = preferences.get("last_daily_brief_generated")
                
                print(f"[daily-brief] Successfully regenerated audio with new voice")
                return {
                    "success": True,
                    "podcast_text": podcast_text,
                    "audio_url": audio_url,
                    "created_at": last_generated_str or datetime.now(timezone.utc).isoformat(),
                    "voice_only_update": True
                }
            else:
                # Fall through to full generation if no existing brief found
                print(f"[daily-brief] No existing transcript found, generating new brief")
        
        # Full generation path (new transcript + audio)
        """
        Example rows for a single user in user_preferences table is 
        ──────────┬────────────────────────────────┬─────────────────────────────────────────┬─────────────────────┐
│ user_id  │ preference_key                 │ preference_value                        │ updated_at          │
├──────────┼────────────────────────────────┼─────────────────────────────────────────┼─────────────────────┤
│ abc123   │ topics                         │ ["Politics","Technology","Health"]      │ 2025-12-02 10:30:00 │
├──────────┼────────────────────────────────┼─────────────────────────────────────────┼─────────────────────┤
│ abc123   │ sources                        │ ["Harvard Gazette","Harvard Crimson"]   │ 2025-12-02 10:30:00 │
├──────────┼────────────────────────────────┼─────────────────────────────────────────┼─────────────────────┤
│ abc123   │ last_daily_brief_generated     │ 2025-12-02T14:25:00Z                    │ 2025-12-02 14:25:00 │

so this function is literally pulling the values from the associated preference
topics_str = preference.get("topics", "[]") pulls the list of preferred topics (inside preference_value) based on the preference_key, "topics".
        
        """

        # parse topics and sources from the preferences
        topics_str = preferences.get("topics", "[]")
        sources_str = preferences.get("sources", "[]")

        try:
            #these arrays of topics and sources are stored as JSON strings, so they need to be parsed back
            #via json.loads()
            topics = json.loads(topics_str) if isinstance(topics_str, str) else topics_str
            sources = json.loads(sources_str) if isinstance(sources_str, str) else sources_str
        except json.JSONDecodeError:
            topics = []
            sources = []

        print(f"[daily-brief] Topics: {topics}")
        print(f"[daily-brief] Sources: {sources}")

        if not topics or not sources:
            raise HTTPException(
                status_code=400,
                detail="No preferences set. Please configure topics and sources first."
            )
        #in this search_articles_by_preferneces function we combine topics into a single string
        #i.e. "politics technology", generate an embedding vector, and do hybrid retrieval SQL query

        # retreive the chunks based on their preferred topics and sources
        #w/ associated parameters (30 chunks, 2 days back)
        """
        SELECT id, chunk, source_type, embedding <=> %s AS score
        FROM vector_table
        WHERE source_type = ANY(['Harvard Gazette', 'Harvard Crimson'])  -- Exact source filter
        AND summary->>'category' = ANY(['Politics', 'Technology'])      -- Exact category filter
        ORDER BY
            embedding <=> %s,  -- Semantic ranking by similarity
            id DESC            -- Newest first
        LIMIT 30;
        """

        chunks = search_articles_by_preferences(
            topics=topics,
            sources=sources,
            limit=30,
            days_back=2
        )

        if not chunks:
            raise HTTPException(
                status_code=404,
                detail="No articles found matching your preferences"
            )

        print(f"[daily-brief] Retrieved {len(chunks)} chunks")

        # format context for Gemini API so that the podcast generation accuratelty mentions the news source title where the info came from
        #so context_text is literally a list of [Article Title: "title" \n "chunk"] for however many chunks we return
        context_text = "\n\n".join([
            f"Article Title: {source_type}\n{chunk}"
            for _, chunk, source_type, score in chunks
        ])

        
        try:
            # Create custom prompt for daily brief
            today_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
            
            # build the full prompt for the gemini API call using the DAILY_BRIEF_PROMPT
            
            DAILY_BRIEF_PROMPT = """
        You are a professional news anchor creating a daily briefing for Harvard community members.

        OBJECTIVE:
        Create an engaging, comprehensive daily news summary covering the most important Harvard news stories from the provided articles.

        STRUCTURE:
        1. Opening: Brief welcome and overview of today's top stories (mention the date)
        2. Main stories: Cover 3-5 major developments in detail with proper context
        3. Quick hits: Mention 2-3 additional noteworthy items briefly
        4. Closing: Brief wrap-up

        DELIVERY STYLE:
        - Professional yet conversational tone (like NPR's "The Daily")
        - Natural narration - NO markdown formatting (**bold**, *italics*, ### headers, etc.)
        - DO NOT use special characters or formatting - write in plain text only
        - This will be converted to speech, so write for listening, not reading
        - Clearly attribute information by naturally mentioning article sources
        - Example: "According to the Harvard Gazette article 'Research Breakthrough,' scientists have discovered..."
        - Smooth transitions between topics
        - Appropriate pacing for audio consumption

        IMPORTANT:
        - Focus on the most significant and interesting stories
        - Provide context and explain why stories matter to the Harvard community
        - Keep total length around 3-5 minutes when spoken (approximately 500-750 words)
        - Be authoritative and well-informed
        - Make it engaging - this is the user's personalized morning briefing

        Begin with: "Good morning, this is your Harvard News Daily Brief for [today's date]..."

        End with: "That's your Harvard News Daily Brief. Have a great day!"
        """

            full_prompt = f"""{DAILY_BRIEF_PROMPT} 

Today's date: {today_date}

Here are the news articles to summarize:

{context_text}

Now generate your daily briefing:"""
            #this is literally calling the gemini_api directly to generate a podcast
            # the call_gemini_api() is a script that is solely used for the interactive Q&A
            #creating a separate helper for one use case is "overkill" according to claude, I think it is actually helpful, but eh
            response = model.generate_content(full_prompt)
            podcast_text = response.text

            if not podcast_text:
                raise HTTPException(status_code=500, detail="Failed to generate briefing text")

            print(f"[daily-brief] Generated text: {len(podcast_text)} chars")

        except Exception as e:
            print(f"[daily-brief] Gemini error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate briefing: {str(e)}")

        # Convert to audio and upload to GCS
        
        print("[daily-brief] Converting text to audio...")
        """what audio bytes does is check if text lenght > 4000 bytes, if so
        split into chunks.
        for each chunk, call Google TTS API, get PCM audio data, add 0.8s silence between chunks
        Then join all audio chunks together
        Convert them from PCM to WAV format with headers
        Complete WAV file as bytes
        """
        # Get user's voice preference
        voice_preference = preferences.get("voice_preference", "en-US-Studio-O")
        print(f"[daily-brief] Using voice preference: {voice_preference}")
        audio_bytes = text_to_audio_bytes(podcast_text, voice_name=voice_preference)

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate audio from text")

        print("[daily-brief] Uploading audio to GCS...")
        """
        What upload_audio_to_gcs does is initialize GCS client w/ service account credentials
        Generates a unique audio filename
        Uploads the audio to ac215-audio-bucket
        Sets cache control & signed URL (who can access, how long the audio file lives for inside bucket)
        Returns URL (audio_url)
        
        """
        audio_url = upload_audio_to_gcs(audio_bytes, user_id, filename_prefix="daily-brief")

        if not audio_url:
            raise HTTPException(status_code=500, detail="Failed to upload audio to storage")

        print(f"[daily-brief] Audio uploaded successfully: {audio_url}")

        # [Z] save the chunks for storage (for context-aware Q&A)
        chunks_data = {
            "chunks": [
                {
                    "chunk_id": chunk_id,
                    "chunk_text": chunk_text,
                    "source_type": source_type,
                    "score": float(score)
                }
                for chunk_id, chunk_text, source_type, score in chunks
            ]
        }
        print(f"[daily-brief] Serialized {len(chunks)} chunks for storage")

        # Save to audio_history with question_text="Daily Brief"
        save_audio_history(
            user_id=user_id,
            question_text="Daily Brief",
            podcast_text=podcast_text,
            audio_url=audio_url,
            source_chunks=json.dumps(chunks_data)  # NEW: Save chunks for context-aware Q&A
        )
        # [Z] GCS bucket also keeps track of q+a audio files for each user

        # Update last_daily_brief_generated timestamp
        current_time = datetime.now(timezone.utc).isoformat()
        save_user_preferences(user_id, {"last_daily_brief_generated": current_time})

        print(f"[daily-brief] Successfully generated and saved")
        #return the success of generating daily brief to frontend via Websocket
        return {
            "success": True,
            "podcast_text": podcast_text,
            "audio_url": audio_url,
            "created_at": current_time,
            "voice_only_update": False
        }

    except HTTPException:
        raise
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")
    except Exception as e:
        print(f"[daily-brief-error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate daily brief: {str(e)}")


#we check status first to avoid regenerating the same brief multiple times
#one brief per user per day
#podcast page CHECKS this endpoint on load to avoid re-generating if already done today
@app.get("/api/daily-brief/status")
async def check_daily_brief_status_endpoint(request: Request):
    """Check if daily brief was generated today and if preferences have been updated since."""
    try:
        user_id = request.state.user_id

        # Load last_daily_brief_generated timestamp
        preferences = get_user_preferences(user_id)
        last_generated_str = preferences.get("last_daily_brief_generated")

        # Get when preferences (topics/sources) were last updated
        preferences_updated_str = get_preferences_last_updated(user_id)
        voice_pref_updated_str = get_voice_preference_last_updated(user_id)

        generated_today = False
        preferences_changed = False
        voice_only_changed = False

        if last_generated_str:
            # Parse timestamp and check if it's today
            try:
                last_generated = datetime.fromisoformat(last_generated_str.replace('Z', '+00:00'))
                today = datetime.now(timezone.utc).date()
                last_date = last_generated.date()
                generated_today = (last_date == today)

                # Check if content preferences (topics/sources) were updated after last brief
                if preferences_updated_str:
                    try:
                        prefs_updated = datetime.fromisoformat(preferences_updated_str.replace('Z', '+00:00'))
                        if prefs_updated > last_generated:
                            preferences_changed = True
                            print(f"[daily-brief-status] Content preferences updated after last brief: {prefs_updated} > {last_generated}")
                    except (ValueError, AttributeError):
                        pass
                
                # Check if only voice changed (voice updated but content preferences not)
                if voice_pref_updated_str and preferences_updated_str:
                    try:
                        voice_updated = datetime.fromisoformat(voice_pref_updated_str.replace('Z', '+00:00'))
                        content_updated = datetime.fromisoformat(preferences_updated_str.replace('Z', '+00:00'))
                        if voice_updated > last_generated and content_updated <= last_generated:
                            voice_only_changed = True
                            print(f"[daily-brief-status] Only voice preference changed: {voice_updated} > {last_generated}, content unchanged")
                    except (ValueError, AttributeError):
                        pass
                elif voice_pref_updated_str:
                    # If voice was updated but we don't have content update time, check voice only
                    try:
                        voice_updated = datetime.fromisoformat(voice_pref_updated_str.replace('Z', '+00:00'))
                        if voice_updated > last_generated:
                            voice_only_changed = True
                            print(f"[daily-brief-status] Voice preference changed: {voice_updated} > {last_generated}")
                    except (ValueError, AttributeError):
                        pass

            except (ValueError, AttributeError):
                pass

        return {
            "generated_today": generated_today,
            "preferences_changed": preferences_changed,
            "voice_only_changed": voice_only_changed,
            "last_generated": last_generated_str,
            "preferences_updated": preferences_updated_str
        }

    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")
    except Exception as e:
        print(f"[daily-brief-status-error] {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check status: {str(e)}")

#retrieve most recent daily brief from user's history to display existing brief without regenerating
@app.get("/api/daily-brief/latest")
async def get_latest_daily_brief_endpoint(request: Request):
    """Get the most recent daily brief from history."""
    try:
        user_id = request.state.user_id

        # Get all history and filter for "Daily Brief"
        history = get_audio_history(user_id, limit=50)

        # Find most recent daily brief
        daily_briefs = [h for h in history if h.get("question_text") == "Daily Brief"]

        if not daily_briefs:
            raise HTTPException(status_code=404, detail="No daily brief found")

        # Return most recent (first in list since get_audio_history returns newest first)
        latest_brief = daily_briefs[0]

        return {
            "id": latest_brief.get("id"),
            "question_text": latest_brief.get("question_text"),
            "podcast_text": latest_brief.get("podcast_text"),
            "audio_url": latest_brief.get("audio_url"),
            "created_at": latest_brief.get("created_at")
        }

    except HTTPException:
        raise
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")
    except Exception as e:
        print(f"[daily-brief-latest-error] {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get latest brief: {str(e)}")
