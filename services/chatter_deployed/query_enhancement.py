"""
Query Enhancement Module

Handles the conversation loop with Gemini LLM to refine user queries before retrieval.
Uses the system prompt from query_enhancement.txt to guide the enhancement process.
"""

import os
import json
import re
from typing import Optional, Tuple, Dict, Any
from vertexai.generative_models import GenerativeModel


def load_system_prompt() -> str:
    """Load the system prompt from query_enhancement.txt"""
    try:
        # Try to find the file relative to this module
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "query_enhancement.txt")
        
        if not os.path.exists(prompt_path):
            # Fallback: try parent directory
            prompt_path = os.path.join(os.path.dirname(current_dir), "chatter_deployed", "query_enhancement.txt")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract the system prompt section (everything after "## 🧠 **System Prompt: News Query Enhancement LLM**")
        # We'll use the entire file content as the system prompt
        return content
    except Exception as e:
        print(f"[query-enhancement-error] Failed to load system prompt: {e}")
        # Return a minimal fallback prompt
        return """You are a news query enhancement assistant. Your job is to take a human user's question about the news and make it clearer, more focused, and more useful for retrieving relevant information.

Every response must strictly follow this JSON schema:
{
  "original_query": "<the user's original query>",
  "enhanced_query": "<the LLM's improved and more specific version, possibly containing multiple explicit questions>",
  "clarification_question": "<a short, self-contained, natural spoken question that summarizes your understanding using reflective phrasing and ends with a gentle confirmation>"
}

The clarification_question is the only part the user hears, so it must be fully self-contained and end with a confirmation phrase like 'does that sound right?'"""


def parse_gemini_response(response_text: str) -> Optional[Dict[str, str]]:
    """Parse Gemini's response to extract JSON, handling markdown code blocks if present."""
    try:
        # Try to find JSON in the response (might be wrapped in ```json or ```)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text
        
        # Parse the JSON
        result = json.loads(json_str)
        
        # Validate required fields
        if all(key in result for key in ["original_query", "enhanced_query", "clarification_question"]):
            return result
        else:
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
    user_query: str,
    model: GenerativeModel,
    conversation_history: Optional[list] = None
) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """
    Call Gemini to enhance a user query.
    
    Args:
        user_query: The user's original or follow-up query
        model: The Gemini model instance
        conversation_history: Optional list of previous messages for context
        
    Returns:
        Tuple of (parsed_response_dict, error_message)
    """
    if not model:
        return None, "Gemini model not configured"
    
    try:
        system_prompt = load_system_prompt()
        
        # Build the prompt
        if conversation_history:
            # Include conversation history for context
            history_text = "\n".join([
                f"User: {msg.get('user', '')}\nAssistant: {msg.get('assistant', '')}"
                for msg in conversation_history
            ])
            prompt = f"""{system_prompt}

CONVERSATION HISTORY:
{history_text}

CURRENT USER QUERY: {user_query}

Please provide your response in the required JSON format."""
        else:
            # First interaction
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


def is_confirmation(user_response: str) -> bool:
    """
    Check if the user's response indicates confirmation.
    
    Returns True if the user confirms (e.g., "yes", "that's right", "correct", etc.)
    """
    confirmation_keywords = [
        "yes", "yeah", "yep", "yup", "correct", "right", "that's right", 
        "exactly", "that's it", "sounds good", "perfect", "that works",
        "sure", "okay", "ok", "alright", "go ahead", "proceed", "continue"
    ]
    
    user_lower = user_response.lower().strip()
    
    # Check for confirmation phrases
    for keyword in confirmation_keywords:
        if keyword in user_lower:
            return True
    
    # Check for negation (not a confirmation)
    negation_keywords = ["no", "nope", "not", "wrong", "incorrect", "that's not", "that isn't"]
    for keyword in negation_keywords:
        if keyword in user_lower:
            return False
    
    # If response is very short and doesn't contain negation, assume confirmation
    if len(user_lower.split()) <= 3:
        return True
    
    return False

