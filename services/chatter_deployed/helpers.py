"""
HELPER FUNCTIONS (called by main.py in chatter_deployed)
THE HELPER FUNCTIONS USED CURRENTLY ARE

1. call_retriever_service(query: str) -> List[Tuple[int, str, str, float]]:
===================================================================
Call the retriever service to get relevant articles.
Input: query
Returns: List of tuples: (id, chunk, source_type, score) for each matching article


2. call_gemini_api(question: str, context_articles: List[Tuple[int, str, str, float]] = None) ->
tuple[Optional[str], Optional[str]]:
===================================================================================================
Call Google Gemini LLM API with the question and context articles to generate a podcast-style
response.
Input: question text + tuple of relevant chunks (with id, chunk text, source_type, and similarity score)
Output: tuple of response text + error message

THE HELPER FUNCTIONS NOT YET USED ARE
check_llm_conversations_table()
================================
Check if the llm_conversations table exists.
Inpùt: -
Output: TRUE if table exists, FALSE otherwise


log_conversation
================
NOT YET USED

"""

from typing import List, Tuple, Optional, Dict, Any
import psycopg
import json
import os
from datetime import datetime, timezone

# from vertexai.generative_models import GenerativeModel


# NEW should work for production and local
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")


def call_retriever_service(query: str, limit: int = 10) -> List[Tuple[int, str, str, float]]:
    """Call the retriever service to get relevant articles."""
    try:
        # Import the retriever function directly since we're in the same environment
        import sys

        sys.path.append("/app/retriever")
        from retriever import search_articles

        print(f"[retriever] Searching for: '{query[:50]}...'")
        articles = search_articles(query, limit=limit)
        print(f"[retriever] Found {len(articles)} relevant chunks")
        return articles
    except Exception as e:
        print(f"[retriever-error] Error calling retriever service: {e}")
        return []


def call_gemini_api(
    question: str, context_articles: List[Tuple[int, str, str, float]] = None, model=None
) -> tuple[Optional[str], Optional[str]]:
    """Call Google Gemini API with the question and context articles to generate a podcast-style
    response."""
    if not model:
        return None, "Gemini API not configured"

    try:
        # Debug logging to track the bug
        print(f"[gemini-debug] Received context_articles: {context_articles is not None}")
        if context_articles is not None:
            print(f"[gemini-debug] Type: {type(context_articles)}")
            print(f"[gemini-debug] Length: {len(context_articles)}")
            if len(context_articles) > 0:
                print(f"[gemini-debug] First chunk structure: {context_articles[0]}")
                print(f"[gemini-debug] First chunk types: {[type(x) for x in context_articles[0]]}")
        else:
            print(f"[gemini-debug] context_articles is None!")

        # Build the prompt with context if articles are provided
        if context_articles:
            print(f"[gemini-debug] Using WITH-CONTEXT prompt (if block)")
            context_text = "\n\n".join(
                [
                    f"Article Title: {source_type}\n{chunk}"
                    for _, chunk, source_type, score in context_articles
                ]
            )

            print(f"[gemini-debug] Built context_text with {len(context_text)} characters")
            print(f"[gemini-debug] First 200 chars of context: {context_text[:200]}")

            # FAILSAFE: Check if context_text is actually empty despite having articles
            if not context_text.strip():
                print(f"[gemini-error] context_text is empty despite having {len(context_articles)} articles!")
                print(f"[gemini-error] Sample chunks: {context_articles[:3]}")
                # Fall through to no-context prompt
                prompt = f"""You are NewsJuice, the AI host of a news podcast about Harvard University.

LISTENER'S QUESTION: {question}

SITUATION: No relevant Harvard news articles were found in the database for this topic.

YOUR TASK:
Deliver a brief, authoritative response stating that this topic is not currently covered in the Harvard news database. Do NOT ask the listener for more information or engage in collaborative conversation.

RESPONSE STRUCTURE:
1. Acknowledge the question directly
2. State clearly that recent Harvard news on this topic is not available in your database
3. Provide 1-2 sentences on what types of Harvard news you DO cover
4. End with a brief closing statement (NO invitation for follow-up)

DELIVERY STYLE:
- Professional and authoritative
- NO collaborative phrases like "Could you clarify?", "What aspect are you interested in?", or "Let me know if..."
- NO questions to the listener
- Keep it brief: 50-75 words maximum

EXAMPLE RESPONSE:
"I don't currently have recent Harvard news covering that specific topic in my database. My coverage focuses on Harvard's academic programs, administrative developments, research initiatives, campus news, and university policy changes. For information on this topic, you may want to check the Harvard Gazette or Crimson directly."

Now generate your response:"""
            else:
                prompt = f"""You are NewsJuice, the AI host of a news podcast about Harvard University. Your role is to deliver factual, informative summaries based on news article chunks.

LISTENER'S QUESTION: {question}

NEWS ARTICLES TO REFERENCE:
{context_text}

YOUR TASK:
1. Synthesize the information from the news article chunks above into a clear, factual podcast segment
2. Directly answer the listener's question using specific details, numbers, and quotes from the article chunks
3. Present information authoritatively - you are delivering news, not seeking clarification
4. Structure your response with these elements:
   - OPENING: Directly state the answer to the question
   - KEY FACTS: Present the most important details with specific numbers, names, and dates. BE SURE TO MENTION THE ARTICLE SOURCE (NEWS TITLE) THE KEY FACT DERIVES FROM WHEN STATING THE KEY FACT.
   - CONTEXT: Provide background information and explain implications
   - CLOSING: Brief summary statement (NO invitation for follow-up questions)
5. Target 50 words for a comprehensive answer
6. IMPORTANT: You may make reasonable inferences and draw connections from related information in the articles. If the articles contain relevant context, related topics, or similar subject matter, use that information to provide a helpful answer. Be flexible in interpreting what counts as "relevant" - synonyms, related concepts, and contextual information all count.
7. ONLY state "The latest Harvard news I have doesn't cover that topic in detail" if the articles are completely unrelated or irrelevant to the question (e.g., asking about sports when only economics articles are provided).

DELIVERY STYLE:
- Professional but conversational tone
- Use specific numbers, names, dates, and quotes from the articles
- NO collaborative phrases like "Great question!", "What do you think?", or "Let me know if you want more details"
- ABSOLUTELY NO COLLABORATIVE PHRASES LIKE "That's a great summary you provided!", or "Thank you for the information"
- NO requests for more information from the listener
- You are INFORMING, not CONVERSING
- DO NOT use markdown formatting like **bold**, *italics*, or ### headers
- Write in plain text only - this will be converted to speech
- When referencing information, naturally mention the article title in your narration
- Example: "According to the Harvard Gazette article 'Budget Cuts Impact Research,' the university..."

EXAMPLE STRUCTURE:
"Harvard is facing significant budget challenges this year. According to recent reports, the university posted a $113 million operating deficit in fiscal year 2025 - its first since 2020. This deficit stems from multiple factors, including the Trump administration's temporary termination of nearly all federal research grants in spring 2025, which removed approximately $116 million in sponsored funds overnight. To address these shortfalls, Harvard has implemented several cost-cutting measures: freezing salaries for non-union staff, leaving positions unfilled, and conducting targeted workforce reductions including 38 IT workers in November. The situation is compounded by a scheduled 400 percent increase in the federal endowment tax taking effect in 2027. Despite these challenges, Harvard's endowment grew 11.9 percent to $56.9 billion in fiscal 2025, which financial officers credit as central to navigating this uncertain period."

Now generate your podcast segment answering the listener's question:"""
        else:
            print(f"[gemini-debug] Using NO-CONTEXT prompt (else block)")
            prompt = f"""You are NewsJuice, the AI host of a news podcast about Harvard University.

LISTENER'S QUESTION: {question}

SITUATION: No relevant Harvard news articles were found in the database for this topic.

YOUR TASK:
Deliver a brief, authoritative response stating that this topic is not currently covered in the Harvard news database. Do NOT ask the listener for more information or engage in collaborative conversation.

RESPONSE STRUCTURE:
1. Acknowledge the question directly
2. State clearly that recent Harvard news on this topic is not available in your database
3. Provide 1-2 sentences on what types of Harvard news you DO cover
4. End with a brief closing statement (NO invitation for follow-up)

DELIVERY STYLE:
- Professional and authoritative
- NO collaborative phrases like "Could you clarify?", "What aspect are you interested in?", or "Let me know if..."
- NO questions to the listener
- Keep it brief: 50-75 words maximum

EXAMPLE RESPONSE:
"I don't currently have recent Harvard news covering that specific topic in my database. My coverage focuses on Harvard's academic programs, administrative developments, research initiatives, campus news, and university policy changes. For information on this topic, you may want to check the Harvard Gazette or Crimson directly."

Now generate your response:"""

        response = model.generate_content(prompt)
        return response.text, None
    except Exception as e:
        return None, str(e)



def check_llm_conversations_table():  # [Z] check_llm_convos is not used by our current workflow.
    # its use case is to first check if there is previous context already present to pull from for
    # our podcast generation.

    """Check if the llm_conversations table exists."""
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'llm_conversations'
                    );
                """
                )
                exists = cur.fetchone()[0]
                if exists:
                    print("[db] llm_conversations table found")
                else:
                    print("[db-warning] llm_conversations table not found")
                return exists
    except Exception as e:
        print(f"[db-error] Failed to check table: {e}")
        raise


# [Z] log conversations is here in case we plan to insert conversations into db for context
def log_conversation(
    user_id: str,
    question: str,
    response: Optional[str],
    error_message: Optional[str],
):
    """Log the conversation to the database."""
    try:
        # Prepare conversation data as JSON
        conversation_data = {
            "question": question,
            "response": response,
            "error": error_message,
        }

        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO llm_conversations (user_id, model_name, conversation_data)
                    VALUES (%s, %s, %s);
                """,
                    (user_id, "gemini-2.5-flash", json.dumps(conversation_data)),
                )

                print("[db] Conversation logged successfully")
    except Exception as e:
        print(f"[db-error] Failed to log conversation: {e}")


# [NEW] Context-Aware Q&A Helper Functions

def get_daily_brief_context(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch today's daily brief context (transcript + chunks) for context-aware Q&A.

    Args:
        user_id: The user's ID

    Returns:
        Dictionary with:
        {
            "id": 123,
            "transcript": "Good morning, this is your...",
            "chunks": [
                {"chunk_id": 1, "chunk_text": "...", "source_type": "...", "score": 0.85},
                ...
            ]
        }
        Returns None if no daily brief found for today
    """
    try:
        from user_db import get_audio_history

        # Get recent history
        history = get_audio_history(user_id, limit=10)

        # Find today's daily brief
        today = datetime.now(timezone.utc).date()
        for entry in history:
            if entry.get("question_text") == "Daily Brief":
                created_at = entry.get("created_at")
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                if created_at.date() == today:
                    # Found today's brief
                    source_chunks = entry.get("source_chunks")
                    # Handle both dict (JSONB from DB) and string (JSON string) formats
                    if isinstance(source_chunks, dict):
                        chunks_data = source_chunks
                    elif isinstance(source_chunks, str):
                        chunks_data = json.loads(source_chunks)
                    else:
                        chunks_data = {"chunks": []}

                    # Debug logging for chunk format verification
                    print(f"[brief-debug] chunks_data type: {type(chunks_data)}")
                    print(f"[brief-debug] chunks_data keys: {chunks_data.keys() if isinstance(chunks_data, dict) else 'not a dict'}")
                    if chunks_data.get("chunks"):
                        print(f"[brief-debug] Number of chunks in chunks_data: {len(chunks_data['chunks'])}")
                        print(f"[brief-debug] First chunk from DB: {chunks_data['chunks'][0]}")

                    return {
                        "id": entry.get("id"),
                        "transcript": entry.get("podcast_text", ""),
                        "chunks": chunks_data.get("chunks", [])
                    }

        return None
    except Exception as e:
        print(f"[brief-context-error] {e}")
        import traceback
        traceback.print_exc()
        return None


def classify_question_context(question: str, brief_transcript: str, model) -> str:
    """
    Classify if a question is about the daily brief content or a general question.

    Args:
        question: User's question
        brief_transcript: The daily brief podcast text
        model: Gemini model instance

    Returns:
        "CONTEXTUAL" - question is about the daily brief
        "GENERAL" - question is unrelated to daily brief
    """
    try:
        # Use more of the transcript for better matching (up to 2000 chars)
        brief_summary = brief_transcript[:2000] if len(brief_transcript) > 2000 else brief_transcript
        #perhaps pass the entire brief or the chunks themselves instead of brief 

        # Create classification prompt with emphasis on name/entity matching
        prompt = f"""You are analyzing a user's question to determine if it relates to a daily news briefing they just heard.

DAILY BRIEF CONTENT:
{brief_summary}

USER'S QUESTION:
{question}

TASK:
Determine if the user's question is asking about ANY content mentioned in the daily brief above.

IMPORTANT INSTRUCTIONS:
1. Check if ANY person names, places, topics, or events in the question appear in the brief
2. Look for partial matches - if the question mentions "Amanda Claybaugh" and the brief mentions that name, it's CONTEXTUAL
3. If the question asks for more details about ANYTHING mentioned in the brief, it's CONTEXTUAL
4. Questions with pronouns like "what did you say about..." or "tell me more about..." are usually CONTEXTUAL
5. Only classify as GENERAL if the topic is completely absent from the brief

Examples of CONTEXTUAL questions:
- "How much were those budget cuts?" (if brief mentioned budget cuts)
- "Tell me more about that research" (if brief mentioned research)
- "What did Amanda Claybaugh say?" (if brief mentioned Amanda Claybaugh)
- "Can you expand on the grading report?" (if brief mentioned a grading report)
- "What did the dean say?" (if brief mentioned a dean)

Examples of GENERAL questions (NOT contextual):
- "What's Harvard's endowment size?" (if brief didn't mention endowment at all)
- "Tell me about sports news" (if brief was only about academics and never mentioned sports)
- "How's the weather?" (unrelated topic never mentioned)

Respond with ONLY ONE word - either "CONTEXTUAL" or "GENERAL":"""

        response = model.generate_content(prompt)
        classification = response.text.strip().upper()

        # Validate response
        if "CONTEXTUAL" in classification:
            print(f"[classification] ✓ Question is CONTEXTUAL to daily brief")
            return "CONTEXTUAL"
        elif "GENERAL" in classification:
            print(f"[classification] ✗ Question is GENERAL (not related to brief)")
            return "GENERAL"
        else:
            # Default to general if unclear
            print(f"[classification-warning] Unclear response: '{classification}', defaulting to GENERAL")
            return "GENERAL"

    except Exception as e:
        print(f"[classification-error] {e}, defaulting to GENERAL")
        import traceback
        traceback.print_exc()
        return "GENERAL"
