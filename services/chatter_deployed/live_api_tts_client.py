"""LiveAPI Text-to-Audio streaming client.

Converts text to audio using Google's LiveAPI and streams audio chunks in real-time.


FUNCTION CONTAINED:

async def text_to_audio_stream(text: str, websocket) -> Optional[str]:

def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int =
2) -> bytes:
(Convert raw PCM audio data to WAV format.)

"""

import asyncio
import os
import struct
from typing import Optional
from google import genai

# from google.genai import types


# text_to_audio_stream converts text to audio using LiveAPI and streams audio chunks to WebSocket
# text_to_audio_stream(text: str, websocket)
async def text_to_audio_stream(text: str, websocket) -> Optional[str]:
    """
    Convert text to audio using LiveAPI and stream audio chunks to WebSocket.

    Args:
        text: The podcast text to convert to audio
        websocket: WebSocket connection to stream audio chunks to frontend

    Returns:
        Success message or None if failed
    """
    try:
        print(f"[live-api-tts] Starting text-to-audio conversion, text length: {len(text)} chars")

        # get API key for Google
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("[live-api-tts-error] GOOGLE_API_KEY not set")
            return None

        # initialize liveAPI client, client = genai.Client(api_key=api_key)
        client = genai.Client(api_key=api_key)
        # half-cascade model, this model is used for production
        model = "gemini-live-2.5-flash-preview"

        # response_modalities has to equal audio because we are outputting audio
        config = {"response_modalities": ["AUDIO"]}  # Request audio output

        print(f"[live-api-tts] Connecting to Live API with model: {model}")

        async with client.aio.live.connect(model=model, config=config) as session:
            print("[live-api-tts] Connected, sending text...")

            # send text to LIVEAPI via session.send_realtime_input(text=text)
            # LiveAPI expects text input, not text_stream_end
            await session.send_realtime_input(text=text)

            print("[live-api-tts] Text sent, receiving audio stream...")

            # initialize the audio chunk buffers to 0
            audio_chunk_count = 0
            total_audio_bytes = 0
            all_audio_chunks = []  # Accumulate all chunks to convert to WAV

            # here we collect the audio chunks in the respective buffers as they are created by
            # LiveAPI
            try:

                async def collect_audio():
                    nonlocal audio_chunk_count, total_audio_bytes
                    async for response in session.receive():
                        # Check multiple possible audio response formats
                        audio_data = None

                        # Try response.audio.data
                        if hasattr(response, "audio") and response.audio:
                            if hasattr(response.audio, "data"):
                                audio_data = response.audio.data
                            elif hasattr(response.audio, "content"):
                                audio_data = response.audio.content

                        # Try response.data if audio not found
                        if not audio_data and hasattr(response, "data"):
                            audio_data = response.data

                        # Try response.content
                        if not audio_data and hasattr(response, "content"):
                            audio_data = response.content

                        if audio_data:
                            audio_chunk_count += 1
                            total_audio_bytes += len(audio_data)
                            all_audio_chunks.append(audio_data)

                            print(
                                f"""[live-api-tts] Received audio chunk {audio_chunk_count}
                                 ({len(audio_data)} bytes)"""
                            )

                        # check if the stream is complete
                        if hasattr(response, "server_content") and response.server_content:
                            if (
                                hasattr(response.server_content, "generation_complete")
                                and response.server_content.generation_complete
                            ):
                                print("[live-api-tts] Generation complete")
                                break
                            if (
                                hasattr(response.server_content, "turn_complete")
                                and response.server_content.turn_complete
                            ):
                                print("[live-api-tts] Turn complete")
                                break

                # Wait for audio with timeout
                await asyncio.wait_for(collect_audio(), timeout=60.0)

            except asyncio.TimeoutError:
                print(
                    f"""[live-api-tts] Timeout waiting for audio (60s),
                received {audio_chunk_count} chunks"""
                )

            print(
                f"""[live-api-tts] Audio stream complete: {audio_chunk_count} chunks,
             {total_audio_bytes} total bytes"""
            )

            # convert PCM (analog) to WAV because that is the audio input the frontend takes
            if all_audio_chunks:
                print(
                    f"""[live-api-tts] Converting {len(all_audio_chunks)}
                 PCM chunks to WAV format..."""
                )
                pcm_data = b"".join(all_audio_chunks)
                wav_data = _pcm_to_wav(pcm_data, sample_rate=24000)  # LiveAPI uses 24kHz

                print(
                    f"""[live-api-tts] Converted to WAV: {len(pcm_data)}
                bytes PCM -> {len(wav_data)} bytes WAV"""
                )

                # stream WAV chunks to frontend via websocket.send_bytes(chunk)
                chunk_size = 8192
                for i in range(0, len(wav_data), chunk_size):
                    chunk = wav_data[i : i + chunk_size]
                    await websocket.send_bytes(chunk)

                print("[live-api-tts] Streamed WAV audio to frontend")
            else:
                print("[live-api-tts] No audio chunks to convert")

            return "success"

    except Exception as e:
        print(f"[live-api-tts-error] Failed to convert text to audio: {e}")
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
