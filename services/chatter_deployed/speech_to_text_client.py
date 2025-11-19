"""Speech-to-Text client for converting audio bytes to text.

FUNCTIONS CONTAINED:

async def audio_to_text(audio_bytes: bytes) -> Optional[str]:
(Convert audio bytes (PCM 16kHz mono) to text using Speech-to-Text API.)

async def _transcribe_with_google_speech(audio_bytes: bytes) -> Optional[str]:
(Transcribe the audio from frontend using the Google Speech to Text API.)
"""

import os
from typing import Optional

# Try google cloud speech to text in order to transcribe audio
try:
    from google.cloud import speech
    GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    GOOGLE_SPEECH_AVAILABLE = False
    print("[speech-to-text] google-cloud-speech not available")


async def audio_to_text(audio_bytes: bytes) -> Optional[str]:
    """
    Convert audio bytes (PCM 16kHz mono) to text using Speech-to-Text API.
    
    Args:
        audio_bytes: Raw audio data in PCM 16kHz mono format that come FROM THE FRONTEND
        
    Returns:
        Transcribed text string, or None if transcription fails
    """
    try:
        print(f"[speech-to-text] Starting transcription, audio size: {len(audio_bytes)} bytes")
        
        
        if GOOGLE_SPEECH_AVAILABLE:
            #transcribe_with_google_speech is defined below
            return await _transcribe_with_google_speech(audio_bytes)
    
        
        else:
            print("[speech-to-text-error] No speech-to-text library available")
            return None
            
    except Exception as e:
        print(f"[speech-to-text-error] Failed to transcribe audio: {e}")
        import traceback
        traceback.print_exc()
        return None


async def _transcribe_with_google_speech(audio_bytes: bytes) -> Optional[str]:
    """Transcribe the audio from frontend using the Google Speech to Text API."""
    try:
        # [Z]
        #initialize the client, which uses GOOGLE_APPLICATION_CREDENTIALS from env
        client = speech.SpeechClient()
        
        # create the audio object. This wraps raw audio bytes into a RecognitionAudio object for the Google
        # Cloud Speech-to-Text. Tells the API the audio data to transcribe.
        audio = speech.RecognitionAudio(content=audio_bytes)
        #[Z]
        # have to try multiple sample rates in case there is something funky from the frontend
        #but usually audio streamed from a browser is 44100 Hz
        #sample rate is how many audio samples per second, so higher = better quality, larger files. It's like frames per second.
        sample_rates_to_try = [44100, 48000, 16000, 22050, 32000]
        
        print("[speech-to-text] Trying multiple sample rates...")
        
        for sample_rate in sample_rates_to_try:
            # Configure recognition
            #configure recognition tries to recognize the sample rate of the audio
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=False,
                audio_channel_count=1,  # Mono
            )
            
            print(f"[speech-to-text] Trying sample rate: {sample_rate} Hz...")
            
            try:
                #[Z]
                # Perform transcription
                #recognize is what the Google Cloud Speech  to Text API uses to understand audio, in order for transcription
                response = client.recognize(config=config, audio=audio)
                #response is essentially one giant dictionary that contaisn the 
                #speech to text transcription version : degree of confidence model has that that is the ground truth transcription
        
                # Debug: Print full response
                print(f"[speech-to-text] Response received: {len(response.results)} results")
                #[Z]
                # Here we actually transcript the text in the event the response is recognized.
                #processes phrase/sentence segments (response.results is multiple transcription segments)
                #alternatives[0] = best interpretation of that segment. alternatives is a list of potential phrases
                #the given audio segment could be. confidence reflects confidence for entire segment.
                transcript_parts = []
                for i, result in enumerate(response.results):
                    if result.alternatives: #result is a specific SEGMENT of the transcription. results[0] is the first phrase of audio --> "Hello Newsjuice"
                        transcript_text = result.alternatives[0].transcript #Result alternatives are different interpretations of the same segment
                        confidence = result.alternatives[0].confidence if hasattr(result.alternatives[0], 'confidence') else None
                        print(f"[speech-to-text] Result {i}: '{transcript_text}' (confidence: {confidence})")
                        if transcript_text.strip():  # Only add non-empty transcripts
                            transcript_parts.append(transcript_text)  #we only add the greatest confidence segment to our transcription
                
                transcript = " ".join(transcript_parts)
                
                if transcript.strip():
                    print(f"[speech-to-text] Transcription successful at {sample_rate}Hz: {transcript[:100]}...")
                    return transcript.strip()
                else:
                    print(f"[speech-to-text] No transcript at {sample_rate}Hz, trying next...")
                    continue  # Try next sample rate
                    
            except Exception as e:
                print(f"[speech-to-text] Error at {sample_rate}Hz: {e}, trying next...")
                continue  # Try next sample rate
        
        # If we get here, none of the sample rates worked
        print("[speech-to-text] No transcript returned from any sample rate")
        return None
            
    except Exception as e:
        print(f"[speech-to-text-error] Google Speech-to-Text error: {e}")
        raise