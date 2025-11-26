#!/usr/bin/env python3
"""
Chatter Service

A microservice that:
1. Prompts user for user ID and question
2. Sends question to Google Gemini API
3. Logs conversation in newsdb database
"""

import os
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

# Configuration
DB_URL = os.environ["DATABASE_URL"]
GEMINI_SERVICE_ACCOUNT_PATH = os.environ.get("GEMINI_SERVICE_ACCOUNT_PATH", "/run/secrets/gemini-service-account.json")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

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


def check_llm_conversations_table():
    """Check if the llm_conversations table exists."""
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'llm_conversations'
                    );
                """)
                exists = cur.fetchone()[0]
                if exists:
                    print("[db] llm_conversations table found")
                else:
                    print("[db-warning] llm_conversations table not found")
                return exists
    except Exception as e:
        print(f"[db-error] Failed to check table: {e}")
        raise


def get_user_input() -> tuple[str, str]:
    """Get user ID and question from terminal input."""
    try:
        user_id = input("Enter your user ID: ").strip()
        if not user_id:
            print("Error: User ID cannot be empty")
            return get_user_input()
        
        question = input("Enter your question: ").strip()
        if not question:
            print("Error: Question cannot be empty")
            return get_user_input()
        
        return user_id, question
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except EOFError:
        print("\nNo more input available. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error getting input: {e}")
        return get_user_input()


def call_retriever_service(query: str) -> List[Tuple[int, str, float]]:
    """Call the retriever service to get relevant articles."""
    try:
        # Import the retriever function directly since we're in the same environment
        import sys
        sys.path.append('/app/retriever')
        from retriever import search_articles
        
        print(f"[retriever] Searching for: '{query[:50]}...'")
        articles = search_articles(query, limit=2)
        print(f"[retriever] Found {len(articles)} relevant chunks")
        return articles
    except Exception as e:
        print(f"[retriever-error] Error calling retriever service: {e}")
        return []

def call_tts_service(text: str) -> Optional[str]:
    """Call the TTS service to generate audio from text."""
    try:
        # Import the TTS function directly since we're in the same environment
        import sys
        sys.path.append('/app/tts')
        from tts import generate_podcast_audio
        
        print(f"[tts] Generating audio for podcast...")
        audio_path = generate_podcast_audio(text)
        if audio_path:
            print(f"[tts] Audio generated successfully")
        return audio_path
    except Exception as e:
        print(f"[tts-error] Error calling TTS service: {e}")
        return None

def play_audio(audio_path: str) -> bool:
    """Play audio file to user."""
    try:
        if not audio_path or not os.path.exists(audio_path):
            print("[audio-error] Audio file not found")
            return False
        
        print(f"🎧 Playing podcast audio...")
        print(f"📁 Audio file: {audio_path}")
        
        # Try to play audio using available players
        players = ['mpv', 'mplayer', 'play', 'aplay']
        for player in players:
            try:
                subprocess.run([player, audio_path], check=True, capture_output=True)
                print(f"[audio] Played using {player}")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        # If no player found, try to play with system default
        try:
            subprocess.run(['open', audio_path], check=True)
            print(f"[audio] Opened with system default player")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        print("[audio-warning] No audio player found. Audio file saved but not played.")
        print(f"[audio-info] You can manually play: {audio_path}")
        
        # Show local file path if it's in the mounted volume
        if "/tmp/audio_output" in audio_path:
            local_path = audio_path.replace("/tmp/audio_output", "./audio_output")
            print(f"[audio-info] Local file path: {local_path}")
            print(f"[audio-info] Run: mpv {local_path}")
        
        return False
        
    except Exception as e:
        print(f"[audio-error] Failed to play audio: {e}")
        return False

def cleanup_audio(audio_path: str) -> None:
    """Clean up temporary audio file."""
    try:
        # Don't delete files in audio_output directory - keep them for user access
        if audio_path and os.path.exists(audio_path) and "/tmp/audio_output" not in audio_path:
            os.remove(audio_path)
            print(f"[audio] Cleaned up temporary audio file: {audio_path}")
        elif "/tmp/audio_output" in audio_path:
            print(f"[audio] Audio file saved for user access: {audio_path}")
    except Exception as e:
        print(f"[audio-warning] Failed to cleanup audio file: {e}")

def call_gemini_api(question: str, context_articles: List[Tuple[int, str, float]] = None) -> tuple[Optional[str], Optional[str]]:
    """Call Google Gemini API with the question and context articles to generate a podcast-style response."""
    if not model:
        return None, "Gemini API not configured"
    
    try:
        # Build the prompt with context if articles are provided
        if context_articles:
            context_text = "\n\n".join([
                f"News Article {i+1} (Relevance Score: {score:.3f}):\n{chunk}"
                for i, (_, chunk, score) in enumerate(context_articles)
            ])
            
            prompt = f"""You are a news podcast host. Based on the following relevant news articles, create an engaging podcast-style response to the user's question. 
            Please limit the podcast generation to one minute at maximum.  

RELEVANT NEWS ARTICLES:
{context_text}

USER QUESTION: {question}

Please create a podcast-style response that:
1. Starts with a warm, engaging introduction
2. Directly addresses the user's question using information from the articles
3. Weaves together insights from the relevant news articles
4. Maintains a conversational, podcast-like tone
5. Ends with a thoughtful conclusion

If the articles don't contain enough information to fully answer the question, acknowledge this and provide what insights you can while being transparent about limitations.

Format your response as if you're speaking directly to the listener in a podcast episode."""
        else:
            prompt = f"""You are a news podcast host. The user has asked: "{question}"

However, no relevant news articles were found to provide context. Please provide a thoughtful response acknowledging this limitation and suggest how the user might find more information about their question."""
        
        response = model.generate_content(prompt)
        return response.text, None
    except Exception as e:
        return None, str(e)


def log_conversation(user_id: str, question: str, response: Optional[str], error_message: Optional[str]):
    """Log the conversation to the database."""
    try:
        # Prepare conversation data as JSON
        conversation_data = {
            "question": question,
            "response": response,
            "error": error_message
        }
        
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO llm_conversations (user_id, model_name, conversation_data)
                    VALUES (%s, %s, %s);
                """, (user_id, 'gemini-2.5-flash', json.dumps(conversation_data)))
                
                print("[db] Conversation logged successfully")
    except Exception as e:
        print(f"[db-error] Failed to log conversation: {e}")


def main():
    """Main function implementing the complete workflow:
    1. User provides user_id and query
    2. Chatter calls retriever service
    3. Retriever embeds query and searches chunks_vector_test for top 2 chunks
    4. Retriever returns chunks to chatter
    5. Chatter calls Gemini API with query and chunks as context
    6. Gemini generates podcast-style response
    """
    print("=== NewsJuice Podcast Generator ===")
    print("🎙️  Welcome to the NewsJuice Podcast Service!")
    print("📰 This service will help you create personalized news podcasts")
    print("🔗 Connecting to database...")
    
    # Test database connection and create table
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
    
    # Check if the llm_conversations table exists
    check_llm_conversations_table()
    
    print("\nGemini API Status:", "✓ Configured" if model else "✗ Not configured")
    print("=" * 40)
    
    # Main interaction loop
    while True:
        try:
            # Get user input
            user_id, question = get_user_input()
            
            print(f"\nProcessing question for user: {user_id}")
            print(f"Question: {question}")
            
            # Step 1: Call retriever service to get relevant articles
            print("\n🔍 Step 1: Retrieving relevant news articles...")
            try:
                relevant_articles = call_retriever_service(question)
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
            
            # Step 2: Call Gemini API with context to generate podcast
            print(f"\n🎙️  Step 2: Generating podcast response with Gemini API...")
            response, error = call_gemini_api(question, relevant_articles)
            
            if response:
                print(f"\n📝 PODCAST TEXT:")
                print("=" * 60)
                print(response)
                print("=" * 60)
                
                # Step 3: Generate audio from podcast text
                print(f"\n🎵 Step 3: Converting podcast to audio...")
                audio_path = call_tts_service(response)
                
                if audio_path:
                    # Step 4: Play audio to user
                    print(f"\n🎧 Step 4: Playing podcast audio...")
                    play_success = play_audio(audio_path)
                    
                    if play_success:
                        print(f"\n✅ Podcast audio played successfully!")
                    else:
                        print(f"\n⚠️  Audio generated but couldn't play automatically")
                        print(f"📁 Audio file saved at: {audio_path}")
                    
                    # Cleanup audio file
                    cleanup_audio(audio_path)
                else:
                    print(f"\n❌ Failed to generate audio")
            else:
                print(f"\n❌ Error generating podcast: {error}")
            
            # Log conversation
            log_conversation(user_id, question, response, error)
            
            print("\n" + "=" * 40)
            
            # Ask if user wants to continue
            continue_choice = input("Do you want to ask another question? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes']:
                break
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            continue
    
    print("🎧 Thank you for using NewsJuice Podcast Generator!")
    print("📰 Keep up with the latest news in podcast format!")


if __name__ == "__main__":
    main()
