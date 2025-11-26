"""
Query Enhancement Module

Handles query enhancement with Gemini LLM to improve user queries before retrieval.
Uses the system prompt from query_enhancement.txt to guide the enhancement process.
Enhances the query once and returns the improved version for immediate use.
"""

import os
import json
import re
from typing import Optional, Tuple, Dict
from vertexai.generative_models import GenerativeModel


def load_system_prompt() -> str:
    """Load the system prompt from query_enhancement.txt"""
    try:
        # Try to find the file relative to this module
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "query_enhancement.txt")

        if not os.path.exists(prompt_path):
            # Fallback: try parent directory
            prompt_path = os.path.join(
                os.path.dirname(current_dir),
                "chatter_deployed",
                "query_enhancement.txt",
            )

        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract the system prompt section (everything after "## 🧠 **System Prompt:
        # News Query Enhancement LLM**")
        # We'll use the entire file content as the system prompt
        return content
    except Exception as e:
        print(f"[query-enhancement-error] Failed to load system prompt: {e}")
        # Return a minimal fallback prompt
        return """You are a news query enhancement assistant. Your job is to take a human user's
         question about the news and make it clearer, more focused, and more useful for retrieving
         relevant information.

Every response must strictly follow this JSON schema:
{
  "original_query": "<the user's original query>",
  "enhanced_query": "<the LLM's improved and more specific version, possibly containing multiple
  explicit questions>"
}

The enhanced query will be used directly for retrieving relevant news articles. Produce the best
possible enhanced query on the first attempt."""


def parse_gemini_response(response_text: str) -> Optional[Dict[str, str]]:
    """Parse Gemini's response to extract JSON, handling markdown code blocks if present."""
    try:
        # Try to find JSON in the response (might be wrapped in ```json or ```)
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text

        # Parse the JSON
        result = json.loads(json_str)

        # Validate required fields: must have original_query and at least one enhanced_query_N
        if "original_query" in result:
            # Check if there's at least one enhanced_query_N key
            has_enhanced_query = any(k.startswith("enhanced_query_") for k in result.keys())
            if has_enhanced_query:
                return result

        print(f"[query-enhancement-error] Missing required fields in response: {result}")
        return None
    except json.JSONDecodeError as e:
        print(f"[query-enhancement-error] Failed to parse JSON from response: {e}")
        print(f"[query-enhancement-error] Response text: {response_text[:200]}...")
        return None
    except Exception as e:
        print(f"[query-enhancement-error] Unexpected error parsing response: {e}")
        return None


def enhance_query_with_gemini(
    user_query: str, model: GenerativeModel
) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """
    Call Gemini to enhance a user query.

    Args:
        user_query: The user's original query
        model: The Gemini model instance

    Returns:
        Tuple of (parsed_response_dict, error_message)
    """
    if not model:
        return None, "Gemini model not configured"

    try:
        system_prompt = load_system_prompt()

        # Build the prompt
        prompt = f"""{system_prompt}

USER QUERY: {user_query}

Please provide your response in the required JSON format."""

        # Call Gemini
        response = model.generate_content(prompt)
        response_text = response.text

        # Parse the response
        parsed = parse_gemini_response(response_text)

        if parsed:
            return parsed, None
        else:
            return None, "Failed to parse Gemini response"

    except Exception as e:
        print(f"[query-enhancement-error] Error calling Gemini: {e}")
        return None, str(e)
