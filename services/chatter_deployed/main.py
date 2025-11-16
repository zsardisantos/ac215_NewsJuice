

'''
main.py

Main app file for chatter service as a FastAPI

Endpoints:

* /healthz
For checking whether the app works

* /api/chatter
Main chatter endpoint: calls the chatter() function.

'''


#load_dotenv()  # This loads .env file
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from typing import Dict, Any
#uploadfile handels audio file auploads from frontend
from fastapi import FastAPI, Body, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse #streaming response stream audio chunks back to frontend
from speech_to_text_client import audio_to_text  # Speech-to-Text function
from live_api_tts_client import text_to_audio_stream  # LiveAPI Text-to-Audio streaming
import io
from fastapi.middleware.cors import CORSMiddleware
import json
import base64
import asyncio
from typing import Optional 
from firebase_auth import initialize_firebase_admin, verify_token
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from user_db import create_user, get_user_preferences, save_user_preferences, save_audio_history, get_audio_history

#importing helper functions
from chatter_handler import chatter
from helpers import call_retriever_service, call_gemini_api
from chatter_handler import model
from openai import OpenAI
from query_enhancement import enhance_query_with_gemini, is_confirmation
from vertexai.generative_models import GenerativeModel 




# --------------------------
# Config
# --------------------------
ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://www.newsjuiceapp.com").split(",")
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
    print(f"[firebase-admin-warning] Firebase Admin not initialized: {e}")
    print("[firebase-admin-warning] Authentication will not work until Firebase Admin is configured")


# --------------------------
# Health
# --------------------------
@app.get("/healthz")
async def healthz_root() -> Dict[str, bool]:
    return {"ok": True}

# --------------------------
# Query Enhancement Helper Functions
# --------------------------
async def _start_enhancement_loop(
    websocket: WebSocket,
    initial_query: str,
    conversation_history: list,
    iteration: int,
    max_iterations: int,
    model: GenerativeModel,
    enhancement_context: dict
):
    """Start the query enhancement conversation loop."""
    # This will be called synchronously, but we need to set state and wait for async response
    # We'll handle the first iteration here
    await _continue_enhancement_loop(
        websocket, initial_query, conversation_history, 
        iteration, max_iterations, model, enhancement_context
    )

async def _continue_enhancement_loop(
    websocket: WebSocket,
    current_query: str,
    conversation_history: list,
    iteration: int,
    max_iterations: int,
    model: GenerativeModel,
    enhancement_context: dict
):
    """Continue the query enhancement conversation loop."""
    iteration += 1
    print(f"[websocket] Query enhancement iteration {iteration}")
    
    # Update context
    enhancement_context["iteration"] = iteration
    enhancement_context["final_query"] = current_query
    enhancement_context["conversation_history"] = conversation_history
    
    # Call Gemini to enhance the query
    enhancement_result, error = enhance_query_with_gemini(
        current_query,
        model,
        conversation_history if iteration > 1 else None
    )
    
    if error or not enhancement_result:
        print(f"[websocket] Query enhancement error: {error}")
        # If enhancement fails, use original query
        enhancement_context["query_confirmed"] = True
        enhancement_context["final_query"] = current_query
        return
    
    enhanced_query = enhancement_result.get("enhanced_query", current_query)
    clarification_question = enhancement_result.get("clarification_question", "")
    
    # Update context with current enhancement
    enhancement_context["enhanced_query"] = enhanced_query
    enhancement_context["clarification_question"] = clarification_question
    
    print(f"[websocket] Enhanced query: {enhanced_query[:100]}...")
    print(f"[websocket] Clarification question: {clarification_question}")
    
    # Stream the clarification question as audio to the user
    await websocket.send_json({
        "status": "clarification",
        "question": clarification_question,
        "enhanced_query": enhanced_query
    })
    
    # Stream the clarification question as audio
    try:
        await websocket.send_json({"status": "streaming_clarification"})
        await text_to_audio_stream(clarification_question, websocket)
    except Exception as e:
        print(f"[websocket] Error streaming clarification: {e}")
        # Continue anyway - user might still respond
    
    # Set state to wait for user response
    enhancement_context["conversation_state"] = "waiting_response"
    await websocket.send_json({"status": "waiting_for_confirmation"})
    print("[websocket] Waiting for user's confirmation response...")
    
    # The actual waiting and response handling happens in the main message loop
    # We just need to signal that we're waiting

async def _retrieve_and_generate_podcast(
    websocket: WebSocket,
    query_text: str,
    user_id: Optional[str],
    model: GenerativeModel
):
    """Helper function to retrieve chunks and generate podcast - used by both normal flow and query enhancement."""
    #step2: call the retriever using the query text
    await websocket.send_json({"status": "retrieving"})
    chunks = call_retriever_service(query_text)
    
    if not chunks:
        await websocket.send_json({"warning": "No relevant articles found"})
    
    #step 3: call_gemini_api to generate podcast text
    await websocket.send_json({"status": "generating"})
    podcast_text, error = call_gemini_api(query_text, chunks, model)
    
    if error or not podcast_text:
        await websocket.send_json({"error": f"LLM error: {error}"})
        return False
    
    await websocket.send_json({"status": "podcast_generated", "text": podcast_text})
    
    #step4: convert podcast text to audio
    await websocket.send_json({"status": "converting_to_audio"})
    try:
        await websocket.send_json({"status": "streaming_audio"})
        result = await text_to_audio_stream(podcast_text, websocket)
        
        if not result:
            await websocket.send_json({"error": "Failed to generate audio stream"})
            return False
        
        await websocket.send_json({"status": "complete"})
        
        # Save audio history if user is authenticated
        if user_id:
            save_audio_history(
                user_id=user_id,
                question_text=query_text,
                podcast_text=podcast_text,
                audio_url=None
            )
            print(f"[websocket] Audio history saved for user: {user_id}")
    
    except Exception as e:
        await websocket.send_json({"error": f"TTS failed: {str(e)}"})
        return False
    
    return True

#------------
#Websocket Audio Endpoint
#------------
#WebSocket route decorator
#/ws/chat - WebSocket endpoint path
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

    #get token from query params
    token = websocket.query_params.get("token")
    user_id = None
    
    if token:
        try:
            decoded_token = verify_token(token)
            user_id = decoded_token['uid']
            print(f"[websocket] Authenticated user: {user_id}")
        except Exception as e:
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close()
            return
    else:
        print("[websocket-warning] No token provided, proceeding without auth")
    
    # Now you have user_id available for the rest of the WebSocket handler
    # Use it to save to CloudSQL:
    # - Save audio history with user_id
    # - Load user preferences with user_id
    
    audio_buffer = bytearray()
    tts_client = OpenAI()  # Initialize once, reuse in loop
    is_processing = False  # Track if we're currently processing a request
    conversation_state = None  # Track conversation state: None, "enhancing", "waiting_response"
    enhancement_context = {}  # Store enhancement conversation context

    try: 
        while True:
            #receive audio chunks from frontend
            # data = await websocket.receive_bytes()
            #OR if frontedn sends JSON with audio data
            message = await websocket.receive()
            if message["type"] == "websocket.receive":
                # Handle raw audio bytes
                if "bytes" in message:
                    # If we're in conversation enhancement and waiting for response, accept audio
                    if (conversation_state == "waiting_response" or 
                        enhancement_context.get("conversation_state") == "waiting_response"):
                        chunk_size = len(message["bytes"])
                        audio_buffer.extend(message["bytes"])
                        print(f"[websocket] Received response audio chunk: {chunk_size} bytes")
                        await websocket.send_json({"status": "chunk_received", "size": len(audio_buffer)})
                    # If we're processing a previous request, ignore new audio chunks
                    elif is_processing:
                        print(f"[websocket] Ignoring audio chunk - still processing previous request")
                        continue
                    else:
                        chunk_size = len(message["bytes"])
                        audio_buffer.extend(message["bytes"])
                        print(f"[websocket] Received audio chunk: {chunk_size} bytes, total buffer: {len(audio_buffer)} bytes")
                        await websocket.send_json({"status": "chunk_received", "size": len(audio_buffer)})
                
                # Handle JSON control messages
                elif "text" in message:
                    try:
                        data = json.loads(message["text"])
                        print(f"[websocket] Received JSON message: {data}")

                        if data.get("type") == "complete":
                            # Handle completion during query enhancement conversation
                            # Check enhancement_context for state if it exists
                            if enhancement_context.get("conversation_state") == "waiting_response" or conversation_state == "waiting_response":
                                # This is a response to a clarification question
                                if len(audio_buffer) > 0:
                                    await websocket.send_json({"status": "transcribing_response"})
                                    user_response_text = await audio_to_text(bytes(audio_buffer))
                                    print(f"[websocket] User response: {user_response_text}")
                                    
                                    # Process the response in enhancement context
                                    final_query = enhancement_context.get("final_query", "")
                                    enhanced_query = enhancement_context.get("enhanced_query", "")
                                    clarification_question = enhancement_context.get("clarification_question", "")
                                    conversation_history = enhancement_context.get("conversation_history", [])
                                    iteration = enhancement_context.get("iteration", 0)
                                    max_iterations = enhancement_context.get("max_iterations", 5)
                                    
                                    # Check if user confirmed
                                    if user_response_text and is_confirmation(user_response_text):
                                        # User confirmed - use the enhanced query
                                        final_query = enhanced_query
                                        conversation_state = None
                                        enhancement_context["conversation_state"] = None
                                        enhancement_context["query_confirmed"] = True
                                        enhancement_context["final_query"] = final_query
                                        print(f"[websocket] Query confirmed! Final query: {final_query}")
                                        await websocket.send_json({
                                            "status": "query_confirmed",
                                            "final_query": final_query
                                        })
                                        # Set is_processing to False temporarily to allow retrieval to proceed
                                        # We'll set it back after
                                    elif user_response_text and user_response_text.lower().strip() in ["skip"]:
                                        # User wants to skip enhancement
                                        conversation_state = None
                                        enhancement_context["conversation_state"] = None
                                        enhancement_context["query_confirmed"] = True
                                        enhancement_context["final_query"] = final_query
                                        print("[websocket] User skipped enhancement, using original query")
                                        await websocket.send_json({"status": "query_skipped"})
                                    else:
                                        # User provided additional context or said no
                                        if user_response_text:
                                            conversation_history.append({
                                                "user": final_query,
                                                "assistant": clarification_question
                                            })
                                            if user_response_text.lower().strip() not in ["no", "nope"]:
                                                final_query = user_response_text
                                        
                                        # Continue enhancement loop
                                        iteration += 1
                                        if iteration >= max_iterations:
                                            # Max iterations reached, use current query
                                            conversation_state = None
                                            enhancement_context["conversation_state"] = None
                                            enhancement_context["query_confirmed"] = True
                                            enhancement_context["final_query"] = final_query
                                            await websocket.send_json({"status": "query_max_iterations"})
                                        else:
                                            # Continue the enhancement loop
                                            await _continue_enhancement_loop(
                                                websocket, final_query, conversation_history, 
                                                iteration, max_iterations, model, enhancement_context
                                            )
                                            continue
                                    
                                    audio_buffer.clear()
                                    
                                    # If query is confirmed, proceed directly to retrieval
                                    if enhancement_context.get("query_confirmed"):
                                        final_query = enhancement_context.get("final_query")
                                        conversation_state = None
                                        enhancement_context["conversation_state"] = None
                                        # Use the final enhanced query for retrieval
                                        text = final_query
                                        print(f"[websocket] Query confirmed! Proceeding with enhanced query: {text}")
                                        
                                        # Proceed directly to retrieval and podcast generation
                                        success = await _retrieve_and_generate_podcast(websocket, text, user_id, model)
                                        
                                        # Reset buffer for next request
                                        audio_buffer.clear()
                                        is_processing = False
                                        if success:
                                            print("[websocket] Request processing complete, ready for next recording")
                                        continue
                                    else:
                                        continue
                                else:
                                    print("[websocket] Complete signal received but no audio in buffer during conversation")
                                    continue
                            
                            # Check if we're already processing
                            if is_processing:
                                print("[websocket] Already processing a request, ignoring new complete signal")
                                continue
                            
                            # Check if we have audio to process
                            if len(audio_buffer) == 0:
                                print("[websocket] ERROR: No audio received in buffer!")
                                await websocket.send_json({"error": "No audio received"})
                                continue
                            
                            is_processing = True
                            print(f"[websocket] Received complete signal, audio buffer size: {len(audio_buffer)} bytes")
                            
                            # Step 1: Convert audio to text
                            await websocket.send_json({"status": "transcribing"})
                            print("[websocket] Starting transcription...")
                            
                            try:
                                #audio_to_text again is the speech_to_text_client.py file, that converts our frontend
                                #audio to text. the transcribed text is the output from audio_to_text.
                                text = await audio_to_text(bytes(audio_buffer))
                                #I think this is what shows up in the backend terminal once the transcription is complete
                                #so we can monitor progress
                                print(f"[websocket] Transcription complete, text: {text[:100] if text else 'None'}...")
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
                            #websocket.send_json updates the frontend, status message via websocket
                            #frontend receives this and updates the UI
                            await websocket.send_json({"status": "transcribed", "text": text})
                            
                            # NEW STEP: Query Enhancement Conversation Loop
                            # Have a conversation with Gemini to refine the query before retrieval
                            await websocket.send_json({"status": "enhancing_query"})
                            print("[websocket] Starting query enhancement conversation...")
                            
                            final_query = text  # Start with original query
                            conversation_history = []
                            max_iterations = 5  # Prevent infinite loops
                            iteration = 0
                            
                            # Initialize enhancement context
                            enhancement_context = {
                                "final_query": final_query,
                                "conversation_history": conversation_history,
                                "iteration": iteration,
                                "max_iterations": max_iterations,
                                "query_confirmed": False
                            }
                            
                            # Start the enhancement loop
                            await _start_enhancement_loop(
                                websocket, final_query, conversation_history, 
                                iteration, max_iterations, model, enhancement_context
                            )
                            
                            # Check if query was confirmed during enhancement, otherwise use original
                            if enhancement_context.get("query_confirmed"):
                                text = enhancement_context.get("final_query", text)
                                print(f"[websocket] Using final enhanced query: {text}")
                            else:
                                print(f"[websocket] Using original query: {text}")
                            
                            # Use the helper function to retrieve and generate podcast
                            success = await _retrieve_and_generate_podcast(websocket, text, user_id, model)
                            
                            if not success:
                                audio_buffer.clear()
                                is_processing = False
                                continue
                            
                            # Reset buffer for next request
                            audio_buffer.clear()
                            is_processing = False
                            print("[websocket] Request processing complete, ready for next recording")
                            
                        elif data.get("type") == "audio":
                            # JSON with base64 audio data
                            audio_bytes = base64.b64decode(data["data"])
                            audio_buffer.extend(audio_bytes)
                            
                        elif data.get("type") == "reset":
                            # Frontend wants to reset
                            audio_buffer.clear()
                            is_processing = False
                            await websocket.send_json({"status": "reset"})
                            print("[websocket] Reset signal received, cleared buffer and processing flag")
                            
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
        except:
            pass
    
         
            

# --------------------------
# Main Endpoint
# --------------------------
@app.post("/api/chatter")
async def chatter_endpoint(payload: Dict[str, Any] = Body(...)):
    return await chatter(payload)


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
        if request.url.path in ["/", "/healthz", "/docs", "/openapi.json"]:
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
            user_id = decoded_token['uid']
            
            # Attach user info to request state
            request.state.user_id = user_id
            request.state.user_email = decoded_token.get('email')
            
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
            return{"status":"success", "user_id":user_id}
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

@app.post("/api/user/preferences")
async def save_preferences_endpoint(request: Request, preferences: Dict[str, Any] = Body(...)):
    """Save user preferences."""
    try:
        user_id = request.state.user_id
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