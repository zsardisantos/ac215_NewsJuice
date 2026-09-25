#!/usr/bin/env python3
"""
Terminal demo of the NewsJuice RAG pipeline -- no microphone, no browser,
no WebSocket, no Firebase, no audio.

It runs YOUR real modules (query_enhancement, retriever, helpers) so what it
shows is the actual production pipeline, minus speech in and speech out.

This exists as the low-risk demo: it needs only the database + Vertex AI, so it
works even if the browser audio loop is misbehaving. It also SHOWS MORE than the
voice demo does -- the interviewers get to see the retrieved chunks and their
similarity scores, which is the part engineers actually find interesting.

    python demo-local/demo_cli.py "What is happening with Harvard's budget?"
"""

import asyncio
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "services", "chatter_deployed"))

import vertexai
from vertexai.generative_models import GenerativeModel

from query_enhancement import enhance_query_with_gemini
from helpers import call_retriever_service, call_gemini_api_stream


def rule(title: str) -> None:
    print(f"\n\033[1m{'=' * 74}\n{title}\n{'=' * 74}\033[0m")


async def run(question: str) -> int:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    region = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
    if not project:
        print("ERROR: GOOGLE_CLOUD_PROJECT is not set")
        return 1

    vertexai.init(project=project, location=region)
    model = GenerativeModel(model_name="gemini-2.5-flash")

    rule("STEP 1  The listener's question")
    print(f"  {question}")

    # ---- Query expansion -------------------------------------------------
    rule("STEP 2  Gemini expands it into focused sub-queries")
    result, err = enhance_query_with_gemini(question, model)
    if err or not result:
        print(f"  (enhancement failed: {err} -- falling back to the raw question)")
        sub_queries = {"enhanced_query_1": question}
    else:
        sub_queries = {k: v for k, v in result.items() if k.startswith("enhanced_query_")}
    for k in sorted(sub_queries):
        print(f"  [{k}] {sub_queries[k]}")

    # ---- Retrieval -------------------------------------------------------
    rule("STEP 3  Vector search over pgvector (cosine distance, lower = closer)")
    all_chunks = []
    for k in sorted(sub_queries):
        hits = call_retriever_service(sub_queries[k], limit=5)
        print(f"\n  {k} -> {len(hits)} hits")
        for cid, text, source, score in hits:
            print(f"    id={cid:<6} score={score:.4f}  [{source}]")
            print(f"      {textwrap.shorten(text, 96)}")
        all_chunks.extend(hits)

    seen, unique = set(), []
    for c in all_chunks:
        if c[0] not in seen:
            seen.add(c[0])
            unique.append(c)

    print(f"\n  {len(all_chunks)} retrieved -> {len(unique)} unique after dedup by chunk id")

    if not unique:
        print("\n  NO CHUNKS FOUND -- the database is empty, or this topic isn't in the corpus.")
        return 1

    # ---- Generation ------------------------------------------------------
    rule("STEP 4  Gemini 2.5 Flash writes the podcast script (streaming)")
    combined = "\n".join(sub_queries[k] for k in sorted(sub_queries))
    print()
    async for token in call_gemini_api_stream(combined, unique, model):
        print(token, end="", flush=True)
    print("\n")

    rule("In the real app this script streams into Google TTS sentence by sentence")
    return 0


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What is happening at Harvard right now?"
    sys.exit(asyncio.run(run(q)))
