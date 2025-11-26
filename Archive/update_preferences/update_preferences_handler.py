'''
update_preferences_handler.py
=============================

contains the update_preferences() function, which does the following:

* connects to SQL DB newsbd
* receives input about preferences from the frontend (www.newsjuiceapp.com - update_preferences.html)
* updates preferences in the user database
* returns success message

'''

# Only load .env for local development
import os
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

#print(f"DEBUG: GEMINI_SERVICE_ACCOUNT_PATH from env = '{os.getenv('GEMINI_SERVICE_ACCOUNT_PATH')}'")
#print(f"DEBUG: Does ../secrets/gemini-service-account.json exist? {os.path.exists('../secrets/gemini-service-account.json')}")

import time
#import uuid
import logging
from typing import Dict, Any

#from google.cloud import storage
#from openai import OpenAI
#from fastapi import HTTPException

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
#from vertexai.generative_models import GenerativeModel


# NEW
#from helpers import check_llm_conversations_table, call_retriever_service, call_gemini_api
#from retriever import get_db_connection, search_articles



# --------------------------
# Config
# --------------------------
ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://www.newsjuiceapp.com").split(",")

# NEW - Works for both local and production - just reads from env
DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

# Optional: tweak cache/headers for the uploaded object
CACHE_CONTROL = os.getenv("CACHE_CONTROL", "public, max-age=3600")

# --------------------------
# App / Clients
# --------------------------
logging.basicConfig(level=logging.INFO)

# Uses Workload Identity / ADC on Cloud Run
storage_client = storage.Client(project=GOOGLE_CLOUD_PROJECT)

async def update_preferences(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Accepts: {"text": "..."}
    Returns: {"text": "..."}  (success message)
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
    


    # 4) Return public URL in the field your frontend expects
    return {"signedUrl": public_url}