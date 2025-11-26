# NOT USED CURRENTLY

import json
import os

from tqdm import tqdm
from vertexai.generative_models import GenerativeModel

from db_manager import PostgresDBManager

GEMINI_SERVICE_ACCOUNT_PATH = os.environ.get(
    "GEMINI_SERVICE_ACCOUNT_PATH", "../../../secrets/gemini-service-account.json"
)
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

# Configure Vertex AI with service account
try:
    if os.path.exists(GEMINI_SERVICE_ACCOUNT_PATH):
        # Set the credentials file path
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GEMINI_SERVICE_ACCOUNT_PATH

        # Initialize the model (using full model path for Vertex AI)
        # Try gemini-2.5-flash first as it's more readily available
        model = GenerativeModel(
            model_name=f"""projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_REGION}
            /publishers/google/models/gemini-2.5-flash"""
        )
        print("[gemini] Configured with Vertex AI service account authentication")
        print(f"[gemini] Using model: gemini-2.5-flash in {GOOGLE_CLOUD_REGION}")
    else:
        print(f"[gemini-warning] Service account file not found at {GEMINI_SERVICE_ACCOUNT_PATH}")
        model = None
except Exception as e:
    print(f"[gemini-error] Failed to configure service account: {e}")
    model = None


def call_gemini_api(article):
    """Call Google Gemini API to generate tags JSON for a single article."""
    if not model:
        return None, "Gemini API not configured"

    try:
        article_text = (article or "").strip()
        if not article_text:
            return None, "No article content provided"

        prompt = f"""
            You are an expert news-tagging system. Your task is to analyze the provided news article
            and generate a structured JSON object containing a broad category,
            a specific sub-topic, and a list of key entities.

            ### INSTRUCTIONS ###
            1.  **Broad Category:** Identify ONE main, high-level category for the article
            (e.g., "Technology," "Politics," "Business," "Sports," "Science").
            2.  **Specific Sub-Topic:** Provide ONE mid-level, descriptive topic that narrows down
            the category (e.g., "Generative AI," "US-China Relations," "Semiconductor Market,"
            "Climate Tech").
            3.  **Key Tags:** Generate a list of 3-5 specific keywords, people, organizations,
            or locations central to the article (e.g., "OpenAI," "GPT-4o," "Sam Altman,"
            "Senate Hearing").
            4.  **Format:** Return your response *only* as a single, valid JSON object following the
             specified structure. Do not include any other text or explanations.

            ### JSON OUTPUT STRUCTURE ###
            {{
            "category": "string",
            "sub_topic": "string",
            "key_tags": ["string", "string", "string"]
            }}

            ### ARTICLE ###
            {article}

            ### YOUR RESPONSE (JSON only) ###

            """

        response = model.generate_content(prompt)
        payload_text = response.text.strip() if response and response.text else ""
        tags_json, parse_error = _extract_json_payload(payload_text)
        if parse_error:
            return None, parse_error
        return tags_json, None
    except Exception as e:
        return None, str(e)


def _extract_json_payload(raw_text):
    """Attempt to parse the model response as JSON and validate required keys."""
    if not raw_text:
        return None, "Empty response from Gemini"

    candidate = raw_text
    if "{" in raw_text and "}" in raw_text:
        try:
            start = raw_text.index("{")
            end = raw_text.rindex("}") + 1
            candidate = raw_text[start:end]
        except ValueError:
            pass

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, f"Failed to parse JSON payload: {exc}"

    required_keys = {"category", "sub_topic", "key_tags"}
    missing = required_keys - set(parsed.keys())
    if missing:
        return None, f"JSON payload missing keys: {', '.join(sorted(missing))}"

    if not isinstance(parsed.get("key_tags"), list):
        return None, "'key_tags' must be a list"

    return parsed, None


def process_articles(limit=1000):
    """Fetch blank-summary articles, generate tags, and persist them."""
    db_manager = PostgresDBManager(url_column="source_link")
    articles = db_manager.fetch_articles_without_summary(limit=limit)

    if not articles:
        print("[tags] No articles with blank summaries found.")
        return

    for article in tqdm(articles, desc="[tags] processing", unit="article"):
        article_id = article.get("article_id")
        content = article.get("content") or ""
        title = article.get("title") or ""

        if not content.strip() and not title.strip():
            print(f"[tags-warning] Skipping article {article_id}: no content or title available.")
            continue

        tags_payload, error = call_gemini_api(content)
        if error:
            print(f"[tags-error] Gemini failed for article {article_id}: {error}")
            continue

        serialized = json.dumps(tags_payload, ensure_ascii=False)
        updated = db_manager.update_article_summary(article_id, serialized)
        if updated:
            print(f"[tags] Updated article {article_id} with tags: {serialized}")
        else:
            print(f"[tags-warning] No DB rows updated for article {article_id}.")


if __name__ == "__main__":
    process_articles()
