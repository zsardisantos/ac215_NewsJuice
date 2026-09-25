#!/usr/bin/env python3
"""
Measure voice Q&A latency against the RUNNING backend, the way the browser uses it.

1. Speaks a question with Google TTS and converts it to raw 16-bit PCM, the same
   format Podcast.jsx sends from the microphone.
2. Streams it to ws://localhost:8080/ws/chat, then sends {"type": "complete"}.
3. The clock starts at "complete" -- the moment the user stops talking -- and
   every status message and the first audio byte are timestamped from there.

    cd services/chatter_deployed
    uv run --env-file .env python ../../demo-local/measure_qa.py "How is Harvard doing financially?"

The headline number is TIME TO FIRST AUDIO: stop talking -> first sound.
Runs unauthenticated, so the follow-up classifier step is skipped (it needs a
logged-in user with a daily brief).
"""

import argparse
import asyncio
import json
import time

import websockets
from google.cloud import texttospeech


def speak_to_pcm(text: str, rate: int) -> bytes:
    client = texttospeech.TextToSpeechClient()
    resp = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Neural2-D"),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16, sample_rate_hertz=rate
        ),
    )
    return resp.audio_content[44:]  # drop the WAV header -> raw PCM, like the browser sends


async def run(question: str, rate: int, url: str) -> None:
    pcm = speak_to_pcm(question, rate)
    print(f"question: {question!r}  ({len(pcm) / (rate * 2):.1f}s of speech at {rate} Hz)\n")

    events = []
    async with websockets.connect(url, max_size=None) as ws:
        for i in range(0, len(pcm), 8192):
            await ws.send(pcm[i : i + 8192])
        # drain the per-chunk acknowledgements so they don't pollute timings
        try:
            while True:
                await asyncio.wait_for(ws.recv(), timeout=0.5)
        except asyncio.TimeoutError:
            pass

        t0 = time.perf_counter()
        await ws.send(json.dumps({"type": "complete"}))
        first_audio = None
        audio_bytes = 0
        transcript = None

        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=120)
            t = time.perf_counter() - t0
            if isinstance(msg, bytes):
                audio_bytes += len(msg)
                if first_audio is None:
                    first_audio = t
                    events.append((t, ">>> FIRST AUDIO"))
                continue
            data = json.loads(msg)
            if data.get("status") == "transcribed":
                transcript = data.get("text")
            label = data.get("status") or ("ERROR: " + str(data.get("error"))) or str(data)
            if label not in ("chunk_received", "audio_segment_done"):
                events.append((t, label))
            if data.get("status") == "complete" or "error" in data:
                break

    prev = 0.0
    for t, label in events:
        print(f"  {t:6.2f}s  (+{t - prev:5.2f})  {label}")
        prev = t
    print(f"\n  transcript heard : {transcript!r}")
    print(f"  TIME TO FIRST AUDIO: {first_audio:.2f}s" if first_audio else "  no audio received")
    print(f"  total until complete: {events[-1][0]:.2f}s, {audio_bytes / 48000:.0f}s of answer audio")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?", default="How is Harvard doing financially?")
    ap.add_argument("--rate", type=int, default=48000, help="mic sample rate to simulate (Mac Chrome: 48000)")
    ap.add_argument("--url", default="ws://localhost:8080/ws/chat")
    a = ap.parse_args()
    asyncio.run(run(a.question, a.rate, a.url))
