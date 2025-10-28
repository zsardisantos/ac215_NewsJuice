import os
import csv
import json
import torch
from vertexai.generative_models import GenerativeModel
import psycopg
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
)

# Configuration
# Construct an absolute path to the secrets file to avoid relative path issues.
_script_dir = os.path.dirname(os.path.abspath(__file__))
GEMINI_SERVICE_ACCOUNT_PATH = os.path.join(_script_dir, "..", "..", "..", "secrets", "gemini-service-account.json")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = ( "us-central1")
QWEN_MODEL_PATH = ("Qwen/Qwen3-0.6B")
# Qwen pipeline expects numeric types for these parameters.
QWEN_MAX_NEW_TOKENS = (512)
QWEN_TEMPERATURE = (0.7)
PODCAST_LOG_CSV =("podcast_results.csv")

_qwen_pipeline = None

try:
    HF_TOKEN = os.environ.get("HF_TOKEN")
except:
    with open("../../../secrets/hf_token.txt", "r") as f:
        HF_TOKEN = f.readline().strip()

def connect_to_gc_db():
    #this is running locally, not in a docker container since it is not designed to be part of the production flow
    DB_URL = "postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb"
    conn = psycopg.connect(DB_URL, autocommit=True)
    return conn

def connect_to_gemini():
    try:
        if os.path.exists(GEMINI_SERVICE_ACCOUNT_PATH):
            # Set the credentials file path
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GEMINI_SERVICE_ACCOUNT_PATH
            
            # Initialize the model (using full model path for Vertex AI)
            # Try gemini-2.5-flash first as it's more readily available
            model = GenerativeModel(
                model_name=f'projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_REGION}/publishers/google/models/gemini-2.5-flash'
            )
            print("[gemini] Configured with Vertex AI service account authentication")
            print(f"[gemini] Using model: gemini-2.5-flash in {GOOGLE_CLOUD_REGION}")
        else:
            print(f"[gemini-warning] Service account file not found at {GEMINI_SERVICE_ACCOUNT_PATH}")
            model = None
    except Exception as e:
        print(f"[gemini-error] Failed to configure service account: {e}")
        model = None

    return model


def get_random_chunk(conn):
    """Extract a random chunk from the chunks_vector table."""
    try:
        with conn.cursor() as cur:
                # Get a random chunk with all relevant fields
                cur.execute("""
                    SELECT 
                        author, title, summary, content,
                        source_link, source_type, fetched_at, published_at,
                        chunk, chunk_index, article_id
                    FROM chunks_vector
                    ORDER BY RANDOM()
                    LIMIT 1;
                """)
                
                row = cur.fetchone()
                
                if row:
                    chunk_data = {
                        "author": row[0],
                        "title": row[1],
                        "summary": row[2],
                        "content": row[3],
                        "source_link": row[4],
                        "source_type": row[5],
                        "fetched_at": row[6],
                        "published_at": row[7],
                        "chunk": row[8],
                        "chunk_index": row[9],
                        "article_id": row[10]
                    }
                    return chunk_data, None
                else:
                    return None, "No chunks found in chunks_vector table"
                    
    except Exception as e:
        return None, f"Error fetching random chunk: {e}"


def create_prompt(context):
    prompt = f"""You are a news podcast host. Based on the following relevant news articles, create an engaging podcast-style script to the user's question. 
            Please limit the podcast generation to 300 words. You should only include the text of the script. Do not include any of your thoughts or any sound effects.    

article context: {context}

Please create a podcast-style response that:
1. Starts with a warm, engaging introduction
2. Directly addresses the user's question using information from the articles
3. Weaves together insights from the relevant news articles
4. Maintains a conversational, podcast-like tone
5. Ends with a thoughtful conclusion

If the articles don't contain enough information to fully answer the question, acknowledge this and provide what insights you can while being transparent about limitations.

Format your response as if you're speaking directly to the listener in a podcast episode."""
    return prompt

def call_gemini_api(prompt, model):
    """Call Google Gemini API with the question and context articles to generate a podcast-style response."""
    if not model:
        return None, "Gemini API not configured"
        
    response = model.generate_content(prompt)
    return response.text, None

def call_local_qwen(prompt):
    """Generate podcast text using locally hosted Qwen model."""
    try:
        generator = ensure_qwen_pipeline()
        outputs = generator(
            prompt,
            max_new_tokens=QWEN_MAX_NEW_TOKENS,
            temperature=QWEN_TEMPERATURE,
            do_sample=QWEN_TEMPERATURE > 0,
            return_full_text=True,
        )
        generated = outputs[0]["generated_text"]
        if generated.startswith(prompt):
            generated = generated[len(prompt):].strip()
        return generated.strip(), None
    except Exception as exc:
        return None, f"Error generating with Qwen: {exc}"

def ensure_qwen_pipeline():
    global _qwen_pipeline
    if _qwen_pipeline is None:
        tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL_PATH, token=HF_TOKEN, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            QWEN_MODEL_PATH,
            device_map="auto" if torch.cuda.is_available() else None,
            torch_dtype="auto",
            trust_remote_code=True,
        )
        _qwen_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )
    return _qwen_pipeline

def append_podcast_result(chunk_text, gemini_text, qwen_text, csv_path=PODCAST_LOG_CSV):
    fieldnames = [
        "chunk_text",
        "gemini_podcast_text",
        "qwen_podcast_text",
        "gemini_length",
        "qwen_length",
    ]
    file_exists = os.path.exists(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "chunk_text": chunk_text,
                "gemini_podcast_text": gemini_text or "",
                "qwen_podcast_text": qwen_text or "",
                "gemini_length": len(gemini_text) if gemini_text else 0,
                "qwen_length": len(qwen_text) if qwen_text else 0,
            }
        )

def get_and_save_chunks(conn, training_samples, filename="chunks_for_processing.json"):
    """Fetch random chunks from the database and save them to a file."""
    chunks = []
    print(f"Fetching {training_samples} random chunks...")
    for _ in range(training_samples):
        chunk, error = get_random_chunk(conn)
        if error:
            print(f"[error] {error}")
        else:
            # Ensure datetime objects are converted to strings for JSON serialization
            if chunk.get('fetched_at'):
                chunk['fetched_at'] = chunk['fetched_at'].isoformat()
            if chunk.get('published_at'):
                chunk['published_at'] = chunk['published_at'].isoformat()
            chunks.append(chunk)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=4)
    print(f"Saved {len(chunks)} chunks to {filename}")
    return chunks

def generate_training_data(training_samples, get_chunks=True, get_generation=False):
    
    

    # 1. Get and save all chunks first
    if get_chunks:
        conn = connect_to_gc_db()
        chunks = get_and_save_chunks(conn, training_samples)
        conn.close() 

    gemini_results = []
    qwen_results = []

    if get_generation:
        # Always load chunks from the file for the generation step.
        try:
            with open("chunks_for_processing.json", 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            print(f"Loaded {len(chunks)} chunks from chunks_for_processing.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading chunks from file: {e}. Please run with get_chunks=True first.")
            return

        model = connect_to_gemini()
        # 2. Run all calls to the Gemini API
        print("\n--- Calling Gemini API for all chunks ---")
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} for Gemini...")
            prompt = create_prompt(chunk['chunk'])
            gemini_podcast_text, gemini_error = call_gemini_api(prompt, model)
            if gemini_error:
                print(f"[gemini-error] {gemini_error}")
            gemini_results.append(gemini_podcast_text)

        # 3. Run all calls to the local Qwen model
        print("\n--- Calling local Qwen model for all chunks ---")
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} for Qwen...")
            prompt = create_prompt(chunk['chunk'])
            qwen_podcast_text, qwen_error = call_local_qwen(prompt)
            if qwen_error:
                print(f"[qwen-error] {qwen_error}")
            qwen_results.append(qwen_podcast_text)

        # 4. Append all results to the CSV file
        print("\n--- Appending all results to CSV ---")
        for i, chunk in enumerate(chunks):
            append_podcast_result(
                chunk['chunk'],
                gemini_results[i],
                qwen_results[i],
            )
        print(f"[info] {len(chunks)} podcast texts appended to podcast_results.csv")

if __name__=="__main__":
    generate_training_data(training_samples=2000, get_chunks=True, get_generation=False)