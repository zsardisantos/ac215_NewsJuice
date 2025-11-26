#!/usr/bin/env python3
"""
Text-to-Speech Service

Converts podcast text to audio using Google Cloud Text-to-Speech API.
Supports multiple voice options and audio formats.
"""

import os
import tempfile
import uuid
from typing import Optional
from google.cloud import texttospeech
from google.oauth2 import service_account

# Configuration
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
TTS_SERVICE_ACCOUNT_PATH = os.environ.get("TTS_SERVICE_ACCOUNT_PATH", "/run/secrets/gcp.json")

# Initialize TTS client
try:
    if os.path.exists(TTS_SERVICE_ACCOUNT_PATH):
        credentials = service_account.Credentials.from_service_account_file(TTS_SERVICE_ACCOUNT_PATH)
        tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
        print("[tts] Configured with Google Cloud TTS service account authentication")
    else:
        print(f"[tts-warning] Service account file not found at {TTS_SERVICE_ACCOUNT_PATH}")
        tts_client = None
except Exception as e:
    print(f"[tts-error] Failed to configure TTS service account: {e}")
    tts_client = None

def generate_podcast_audio(text: str, voice_name: str = "en-US-Neural2-J") -> Optional[str]:
    """
    Generate audio from podcast text using Google Cloud TTS.
    
    Args:
        text: The podcast text to convert to speech
        voice_name: Voice to use (default: en-US-Neural2-J for male podcast voice)
    
    Returns:
        Path to generated audio file, or None if error
    """
    if not tts_client:
        print("[tts-error] TTS client not configured")
        return None
    
    try:
        # Configure synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Configure voice parameters
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.MALE  # Podcast-style male voice
        )
        
        # Configure audio output
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.9,  # Slightly slower for podcast clarity
            pitch=0.0,  # Neutral pitch
            volume_gain_db=0.0  # Normal volume
        )
        
        # Generate speech
        print(f"[tts] Generating audio with voice: {voice_name}")
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Save audio to mounted volume for easy access
        audio_filename = f"podcast_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = os.path.join("/tmp/audio_output", audio_filename)
        
        # Ensure directory exists
        os.makedirs("/tmp/audio_output", exist_ok=True)
        
        with open(audio_path, "wb") as out:
            out.write(response.audio_content)
        
        print(f"[tts] Audio saved to: {audio_path}")
        return audio_path
        
    except Exception as e:
        print(f"[tts-error] Failed to generate audio: {e}")
        return None

def get_available_voices() -> list:
    """Get list of available voices for podcast generation."""
    if not tts_client:
        return []
    
    try:
        voices = tts_client.list_voices()
        podcast_voices = []
        
        for voice in voices.voices:
            if voice.language_codes[0].startswith("en-US"):
                podcast_voices.append({
                    "name": voice.name,
                    "gender": voice.ssml_gender.name,
                    "language": voice.language_codes[0]
                })
        
        return podcast_voices
    except Exception as e:
        print(f"[tts-error] Failed to get voices: {e}")
        return []

def cleanup_audio(audio_path: str) -> None:
    """Clean up temporary audio file."""
    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"[tts] Cleaned up audio file: {audio_path}")
    except Exception as e:
        print(f"[tts-warning] Failed to cleanup audio file: {e}")

def main():
    """Test the TTS service."""
    print("=== NewsJuice TTS Service ===")
    print("Testing Google Cloud Text-to-Speech...")
    
    if not tts_client:
        print("❌ TTS client not configured")
        return
    
    # Test with sample text
    test_text = "Welcome to NewsJuice Podcast! This is a test of our text-to-speech system."
    
    print(f"Generating audio for: '{test_text[:50]}...'")
    audio_path = generate_podcast_audio(test_text)
    
    if audio_path:
        print(f"✅ Audio generated successfully: {audio_path}")
        print("🎧 You can play this file to test the audio quality")
    else:
        print("❌ Failed to generate audio")

if __name__ == "__main__":
    main()
