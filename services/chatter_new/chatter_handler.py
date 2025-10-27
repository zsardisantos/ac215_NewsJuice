'''
chatter_handler.py
==================

contains the chatter() function, which does the following:

* connects to SQL DB
* receives a text from frontend
* calls retriever to obtain relevant articles
* calls Gemini API to generate a podcast text (using model gemini-2.5-flash)
* calls TTS to convert podcast text to an mp3 file
* uploads the mp3 to GCS bucket
* returns public URL to frontend

'''

# Only load .env for local development
import os
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

#print(f"DEBUG: GEMINI_SERVICE_ACCOUNT_PATH from env = '{os.getenv('GEMINI_SERVICE_ACCOUNT_PATH')}'")
#print(f"DEBUG: Does ../secrets/gemini-service-account.json exist? {os.path.exists('../secrets/gemini-service-account.json')}")

import time
import uuid
import logging
from typing import Dict, Any

from google.cloud import storage
from openai import OpenAI
from fastapi import HTTPException

# NEW
import sys
import psycopg
from datetime import datetime, timezone
from typing import Optional, List, Tuple
import json
import requests
import subprocess
import tempfile
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel


# NEW
from helpers import check_llm_conversations_table, call_retriever_service, call_gemini_api
from retriever import get_db_connection, search_articles



# --------------------------
# Config
# --------------------------
ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://www.newsjuiceapp.com").split(",")
AUDIO_BUCKET = os.getenv("AUDIO_BUCKET")  # e.g., "ac215-audio-bucket"
GCS_PREFIX = os.getenv("GCS_PREFIX", "podcasts/").strip("/")
if GCS_PREFIX:
    GCS_PREFIX += "/"


# NEW - Works for both local and production - just reads from env
DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

GEMINI_SERVICE_ACCOUNT_PATH = os.environ.get(
    "GEMINI_SERVICE_ACCOUNT_PATH",
    "/secrets/gemini-service-account.json"  # Default for local
)
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

# Optional: tweak cache/headers for the uploaded object
CACHE_CONTROL = os.getenv("CACHE_CONTROL", "public, max-age=3600")

# --------------------------
# App / Clients
# --------------------------
logging.basicConfig(level=logging.INFO)

# Requires OPENAI_API_KEY via env/secret
client = OpenAI()

#NEW
# Configure Vertex AI with service account
try:
    if os.path.exists(GEMINI_SERVICE_ACCOUNT_PATH):
        # Set the credentials file path
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GEMINI_SERVICE_ACCOUNT_PATH
        
        # Initialize the model (using full model path for Vertex AI)
        # Try gemini-2.5-flash first as it's more readily available
        model = GenerativeModel(
            model_name=f'projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_REGION}/publishers/google/models/gemini-2.5-flash'
        )
        print("[gemini] Configured with Vertex AI service account authentication")
        print(f"[gemini] Using model: gemini-2.5-flash in {GOOGLE_CLOUD_REGION}")
    else:
        print(f"[gemini-warning] Service account file not found at {GEMINI_SERVICE_ACCOUNT_PATH}")
        model = None
except Exception as e:
    print(f"[gemini-error] Failed to configure service account: {e}")
    model = None

# Uses Workload Identity / ADC on Cloud Run
storage_client = storage.Client(project=GOOGLE_CLOUD_PROJECT)

async def chatter(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Accepts: {"text": "..."}
    Returns: {"signedUrl": "..."}  (here: a public URL since bucket is public)
    """

    # Test database connection
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), version();")
                db_name, db_version = cur.fetchone()
                print(f"[db] Connected successfully to '{db_name}'")
                print(f"[db] Server version: {db_version}")
    except Exception as e:
        print(f"[db-error] Failed to connect to database: {e}")
        sys.exit(1)

    if not AUDIO_BUCKET:
        raise HTTPException(status_code=500, detail="AUDIO_BUCKET env var not set.")

    text = (payload or {}).get("text", "")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=400, detail="Missing 'text'.")

    text = text.strip()
    if len(text) > 4000:
        text = text[:4000]

    
    # Step 1: Call retriever service to get relevant articles, based on the query text

    print("\n🔍 Step 1: Retrieving relevant news articles...")
    try:
        relevant_articles = call_retriever_service(text)
        if relevant_articles:
            print(f"✅ Found {len(relevant_articles)} relevant article chunks")
            for i, (_, chunk, score) in enumerate(relevant_articles):
                print(f"  📰 Chunk {i+1}: Relevance Score {score:.3f}")
                print(f"     Preview: {chunk[:100]}...")
        else:
            print("⚠️  No relevant articles found")
    except Exception as e:
        print(f"❌ Error calling retriever service: {e}")
        relevant_articles = []
    

    # Step 2: Call Gemini API with initial question as context to generate podcast text

    print(f"\n🎙️  Step 2: Generating podcast text response with Gemini API...")
    response, error = call_gemini_api(text, relevant_articles, model)
    
    if response:
        print(f"\n📝 PODCAST TEXT:")
        print("=" * 60)
        print(response)
        print("=" * 60)
    else:
        print(f"\n❌ Error generating podcast text: {error}")
        print("=" * 60)
    
    # Step 3:  TTS → MP3

    try:
        tts = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=response,
            response_format="mp3",
        )
        mp3_bytes = tts.content
        if not mp3_bytes:
            raise RuntimeError("Empty audio content from TTS.")
        logging.info("[tts] ok; bytes=%d", len(mp3_bytes))
    except Exception as e:
        logging.exception("TTS failed:")
        raise HTTPException(status_code=502, detail=f"TTS failed: {e}")

    # Step 4:  Upload MP3 to GCS
    ts = int(time.time())
    filename = f"{ts}-{uuid.uuid4().hex}.mp3"
    blob_name = f"{GCS_PREFIX}{filename}"
    try:
        bucket = storage_client.bucket(AUDIO_BUCKET)
        blob = bucket.blob(blob_name)
        # Optionally set headers before upload
        blob.cache_control = CACHE_CONTROL
        blob.content_type = "audio/mpeg"

        blob.upload_from_string(mp3_bytes, content_type="audio/mpeg")
        logging.info("[gcs] uploaded gs://%s/%s", AUDIO_BUCKET, blob_name)

        # Since bucket is public (UBLA + bucket IAM allUsers:objectViewer),
        # we can directly build the public URL:
        public_url = f"https://storage.googleapis.com/{AUDIO_BUCKET}/{blob_name}"
        logging.info("[public] %s", public_url)

    except Exception as e:
        logging.exception("GCS upload failed:")
        raise HTTPException(status_code=502, detail=f"GCS upload failed: {e}")

    # 4) Return public URL in the field your frontend expects
    return {"signedUrl": public_url}
