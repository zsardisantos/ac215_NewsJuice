
'''
HELPER FUNCTIONS (called by chatter_handler)

call_retriever_service(query: str) -> List[Tuple[int, str, float]]:
===================================================================
Call the retriever service to get relevant articles.
Input: query  
Returns: List of tuples: (id, chunk, score) for each matching article


call_gemini_api(question: str, context_articles: List[Tuple[int, str, float]] = None) -> tuple[Optional[str], Optional[str]]:
=============================================================================================================================
Call Google Gemini LLM API with the question and context articles to generate a podcast-style response.
Input: question text + tuple of relevant chunks (with id, chunk text and similarity score)
Output: tuple of response text + error message


check_llm_conversations_table() - NOT YET USED
================================
Check if the llm_conversations table exists.
Inpùt: - 
Output: TRUE if table exists, FALSE otherwise


log_conversation
================
NOT YET USED

'''

from typing import List, Tuple, Dict, Optional
import psycopg
import json
import os
from vertexai.generative_models import GenerativeModel


# NEW should work for production and local
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")


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

def call_gemini_api(question: str, context_articles: List[Tuple[int, str, float]] = None, model=None) -> tuple[Optional[str], Optional[str]]:
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
