"""Google Cloud Text-to-Speech streaming client.

Converts text to audio using Google Cloud Text-to-Speech API and streams audio chunks in real-time.


FUNCTIONS CONTAINED:

async def text_to_audio_stream(text: str, websocket) -> Optional[str]:
    Stream audio chunks to WebSocket

def text_to_audio_bytes(text: str) -> Optional[bytes]:
    Convert text to audio bytes (non-streaming version for daily brief)

def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int =
2) -> bytes:
    Convert raw PCM audio data to WAV format.

"""

import struct
import re
from typing import Optional, List
from google.cloud import texttospeech


# text_to_audio_stream converts text to audio using Google Cloud TTS and streams audio chunks to WebSocket
async def text_to_audio_stream(text: str, websocket, voice_name: Optional[str] = None) -> Optional[str]:
    """
    Convert text to audio using Google Cloud Text-to-Speech API and stream audio chunks to WebSocket.

    Args:
        text: The podcast text to convert to audio (narrated EXACTLY as written)
        websocket: WebSocket connection to stream audio chunks to frontend
        voice_name: Optional voice name (e.g., "en-US-Studio-O"). Defaults to "en-US-Studio-O" if not provided.

    Returns:
        Success message or None if failed
    """
    try:
        print(f"[cloud-tts] Starting text-to-audio conversion, text length: {len(text)} chars")

        # Initialize Google Cloud Text-to-Speech client
        # Uses ADC (Application Default Credentials) - no API key needed
        client = texttospeech.TextToSpeechClient()

        # Configure the synthesis request
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Voice configuration - using a natural-sounding English voice
        # Default to en-US-Chirp3-HD-Aoede if no voice preference is provided
        default_voice = "en-US-Chirp3-HD-Aoede"
        selected_voice = voice_name if voice_name else default_voice
        print(f"[cloud-tts] Using voice: {selected_voice}")
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=selected_voice  # High-quality Studio voice (natural podcaster sound)
            # Note: Studio voices don't require ssml_gender parameter
        )

        # Audio configuration - LINEAR16 (PCM) format at 24kHz
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            speaking_rate=1.0,  # Normal speaking speed
            pitch=0.0  # Normal pitch
        )

        print("[cloud-tts] Sending text to Google Cloud Text-to-Speech API...")

        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        print(f"[cloud-tts] Received audio data: {len(response.audio_content)} bytes")

        # The response contains raw PCM audio data
        pcm_data = response.audio_content

        # Convert PCM to WAV format
        print("[cloud-tts] Converting PCM to WAV format...")
        wav_data = _pcm_to_wav(pcm_data, sample_rate=24000)

        print(f"[cloud-tts] Converted to WAV: {len(pcm_data)} bytes PCM -> {len(wav_data)} bytes WAV")

        # Stream WAV chunks to frontend via websocket
        chunk_size = 8192
        chunks_sent = 0
        for i in range(0, len(wav_data), chunk_size):
            chunk = wav_data[i : i + chunk_size]
            await websocket.send_bytes(chunk)
            chunks_sent += 1

        print(f"[cloud-tts] Streamed {chunks_sent} WAV audio chunks to frontend")
        return "success"

    except Exception as e:
        print(f"[cloud-tts-error] Failed to convert text to audio: {e}")
        import traceback

        traceback.print_exc()
        return None


def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """
    Convert raw PCM audio data to WAV format.

    Args:
        pcm_data: Raw PCM audio bytes (16-bit signed integers)
        sample_rate: Sample rate in Hz (default 24000 for LiveAPI)
        channels: Number of audio channels (1 = mono, 2 = stereo)
        sample_width: Bytes per sample (2 = 16-bit)

    Returns:
        WAV file as bytes
    """
    # WAV file header structure
    # RIFF header
    data_size = len(pcm_data)
    file_size = 36 + data_size

    wav_header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",  # ChunkID
        file_size,  # ChunkSize
        b"WAVE",  # Format
        b"fmt ",  # Subchunk1ID
        16,  # Subchunk1Size (PCM)
        1,  # AudioFormat (1 = PCM)
        channels,  # NumChannels
        sample_rate,  # SampleRate
        sample_rate * channels * sample_width,  # ByteRate
        channels * sample_width,  # BlockAlign
        sample_width * 8,  # BitsPerSample
        b"data",  # Subchunk2ID
        data_size,  # Subchunk2Size
    )

    return wav_header + pcm_data


def _split_text_into_chunks(text: str, max_bytes: int = 4000) -> List[str]:
    """
    Split text into chunks at sentence boundaries, ensuring each chunk is under max_bytes.
    
    Args:
        text: The text to split
        max_bytes: Maximum bytes per chunk (default 4000 to stay under 5000 limit)
    
    Returns:
        List of text chunks
    """
    # First, check if text is small enough
    text_bytes = len(text.encode('utf-8'))
    if text_bytes <= max_bytes:
        return [text]
    
    # Split by sentences (period, exclamation, question mark followed by space or end)
    sentences = re.split(r'([.!?]\s+)', text)
    
    # Recombine sentences with their punctuation
    chunks = []
    current_chunk = ""
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]  # Add punctuation back
        
        # Check if adding this sentence would exceed the limit
        test_chunk = current_chunk + sentence
        if len(test_chunk.encode('utf-8')) > max_bytes and current_chunk:
            # Save current chunk and start new one
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += sentence
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    print(f"[cloud-tts] Split text into {len(chunks)} chunks (original: {text_bytes} bytes)")
    return chunks


def _generate_silence(duration_seconds: float = 0.5, sample_rate: int = 24000) -> bytes:
    """
    Generate silence (PCM audio bytes with zero values) for a specified duration.
    
    Args:
        duration_seconds: Duration of silence in seconds (default 0.8 seconds)
        sample_rate: Sample rate in Hz (default 24000)
    
    Returns:
        PCM audio bytes representing silence
    """
    # For 16-bit PCM: each sample is 2 bytes
    num_samples = int(sample_rate * duration_seconds)
    # Generate zeros (silence) - 16-bit signed integers, so 0x0000 for each sample
    silence = b'\x00\x00' * num_samples
    return silence


def _synthesize_chunk(client: texttospeech.TextToSpeechClient, text: str, voice: texttospeech.VoiceSelectionParams, audio_config: texttospeech.AudioConfig) -> Optional[bytes]:
    """
    Synthesize a single chunk of text to PCM audio bytes.
    
    Args:
        client: TTS client
        text: Text chunk to synthesize
        voice: Voice configuration
        audio_config: Audio configuration
    
    Returns:
        PCM audio bytes or None if failed
    """
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        print(f"[cloud-tts-error] Failed to synthesize chunk: {e}")
        return None


def text_to_audio_bytes(text: str, voice_name: Optional[str] = None) -> Optional[bytes]:
    """
    Convert text to audio bytes (non-streaming version for daily brief).
    Handles long text by splitting into chunks and concatenating the audio.
    
    Args:
        text: The podcast text to convert to audio
        voice_name: Optional voice name (e.g., "en-US-Studio-O"). Defaults to "en-US-Studio-O" if not provided.
    
    Returns:
        WAV audio file as bytes, or None if conversion fails
    """
    try:
        text_bytes = len(text.encode('utf-8'))
        print(f"[cloud-tts] Starting text-to-audio conversion, text length: {len(text)} chars ({text_bytes} bytes)")
        
        # Initialize Google Cloud Text-to-Speech client
        # Uses ADC (Application Default Credentials) - no API key needed
        client = texttospeech.TextToSpeechClient()
        
        # Voice configuration - using a natural-sounding English voice
        # Default to en-US-Chirp3-HD-Aoede if no voice preference is provided
        default_voice = "en-US-Chirp3-HD-Aoede"
        selected_voice = voice_name if voice_name else default_voice
        print(f"[cloud-tts] Using voice: {selected_voice}")
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=selected_voice  # High-quality Studio voice (natural podcaster sound)
            # Note: Studio voices don't require ssml_gender parameter
        )
        
        # Audio configuration - LINEAR16 (PCM) format at 24kHz
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            speaking_rate=1.0,  # Normal speaking speed
            pitch=0.0  # Normal pitch
        )
        
        # Check if text needs to be chunked (5000 byte limit, use 4000 to be safe)
        chunks = _split_text_into_chunks(text, max_bytes=4000)
        
        if len(chunks) == 1:
            # Single chunk - use simple path
            print("[cloud-tts] Sending text to Google Cloud Text-to-Speech API...")
            synthesis_input = texttospeech.SynthesisInput(text=text)
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            pcm_data = response.audio_content
            print(f"[cloud-tts] Received audio data: {len(pcm_data)} bytes")
        else:
            # Multiple chunks - synthesize each and concatenate with pauses
            print(f"[cloud-tts] Synthesizing {len(chunks)} chunks...")
            pcm_chunks = []
            pause_duration = 0.8  # Pause duration in seconds between chunks
            
            for i, chunk in enumerate(chunks, 1):
                print(f"[cloud-tts] Synthesizing chunk {i}/{len(chunks)} ({len(chunk.encode('utf-8'))} bytes)...")
                chunk_pcm = _synthesize_chunk(client, chunk, voice, audio_config)
                
                if not chunk_pcm:
                    print(f"[cloud-tts-error] Failed to synthesize chunk {i}")
                    return None
                
                pcm_chunks.append(chunk_pcm)
                print(f"[cloud-tts] Chunk {i} synthesized: {len(chunk_pcm)} bytes")
                
                # Add pause after each chunk (except the last one)
                if i < len(chunks):
                    silence = _generate_silence(duration_seconds=pause_duration, sample_rate=24000)
                    pcm_chunks.append(silence)
                    print(f"[cloud-tts] Added {pause_duration}s pause after chunk {i}")
            
            # Concatenate all PCM chunks (including pauses)
            pcm_data = b''.join(pcm_chunks)
            print(f"[cloud-tts] Concatenated {len(chunks)} chunks with pauses: {len(pcm_data)} total bytes")
        
        # Convert PCM to WAV format
        print("[cloud-tts] Converting PCM to WAV format...")
        wav_data = _pcm_to_wav(pcm_data, sample_rate=24000)
        
        print(f"[cloud-tts] Converted to WAV: {len(pcm_data)} bytes PCM -> {len(wav_data)} bytes WAV")
        return wav_data
        
    except Exception as e:
        print(f"[cloud-tts-error] Failed to convert text to audio: {e}")
        import traceback
        traceback.print_exc()
        return None
