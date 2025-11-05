#############################################################################
###### This script is designed to run on colab. It was not tested elsewhere
#############################################################################
###### Dont forget to have the env variables setup in colab
#############################################################################

import os
import csv
import json
import torch
from vertexai.generative_models import GenerativeModel
#!pip import psycopg
import psycopg
from tqdm import tqdm
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
)

# Configuration

#GEMINI_SERVICE_ACCOUNT_PATH =  "gemini-service-account.json"    #For running on colab. make sure that the secrets file is placed in the contents folder
#GEMINI_SERVICE_ACCOUNT_PATH =  "../../../secrets/gemini-service-account.json"     ## For testing Locally
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = ( "us-central1")
QWEN_MODEL_PATH = ("Qwen/Qwen3-0.6B")
# Qwen pipeline expects numeric types for these parameters.
QWEN_MAX_NEW_TOKENS = int(WORD_LIMIT * 1.5)
QWEN_TEMPERATURE = (0.7)
QWEN_BATCH_SIZE = 4    #Running Qwen in batches of 4 for quicker generation
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
            The script must be no longer than 300 words under any circumstance. Make sure you dont go over the spesified word limit You should only include the text of the script. Do not include any of your thoughts or any sound effects.    

article context: {context}

Please create a podcast-style response that:
1. Starts with a warm, engaging introduction
2. Directly addresses the user's question using information from the articles
3. Weaves together insights from the relevant news articles
4. Maintains a conversational, podcast-like tone
5. Ends with a thoughtful conclusion that stays within the 300-word limit

If the articles don't contain enough information to fully answer the question, acknowledge this and provide what insights you can while being transparent about limitations.

Format your response as if you're speaking directly to the listener in a podcast episode."""
    return prompt


def enforce_word_limit(text, limit=WORD_LIMIT):
    """Ensure the generated text does not exceed the desired word limit."""
    if not text:
        return text

    words = text.strip().split()
    if len(words) <= limit:
        return text.strip()

    trimmed = " ".join(words[:limit])
    return trimmed.strip()


def word_count(text):
    """Return the number of words in the provided text."""
    if not text:
        return 0
    return len(text.strip().split())

def call_gemini_api(prompt, model):
    """Call Google Gemini API with the question and context articles to generate a podcast-style response."""
    if not model:
        return None, "Gemini API not configured"

    response = model.generate_content(prompt)
    limited_text = enforce_word_limit(response.text, WORD_LIMIT)
    return limited_text, None

def call_local_qwen(prompt):
    outputs, errors = call_local_qwen_batch([prompt])
    return outputs[0], errors[0]


def call_local_qwen_batch(prompts):
    """Generate podcast text using locally hosted Qwen model for a batch of prompts."""
    try:
        generator = ensure_qwen_pipeline()
        results = generator(
            prompts,
            max_new_tokens=QWEN_MAX_NEW_TOKENS,
            temperature=QWEN_TEMPERATURE,
            do_sample=QWEN_TEMPERATURE > 0,
            return_full_text=True,
        )

        texts = []
        errors = [None] * len(prompts)

        # The pipeline returns a nested list when multiple prompts are provided.
        for idx, output in enumerate(results):
            sequences = output if isinstance(output, list) else [output]
            generated = sequences[0]["generated_text"]
            prompt = prompts[idx]
            if generated.startswith(prompt):
                generated = generated[len(prompt):].strip()
            texts.append(enforce_word_limit(generated, WORD_LIMIT))

        return texts, errors

    except Exception as exc:
        error_message = f"Error generating with Qwen: {exc}"
        return [None] * len(prompts), [error_message] * len(prompts)

def ensure_qwen_pipeline():
    global _qwen_pipeline
    if _qwen_pipeline is None:
        tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL_PATH, token=HF_TOKEN, trust_remote_code=True)
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            QWEN_MODEL_PATH,
            device_map="auto" if torch.cuda.is_available() else None,
            torch_dtype=torch_dtype,
            trust_remote_code=True,
        )
        _qwen_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            model_kwargs={"torch_dtype": torch_dtype},
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
                "gemini_length": word_count(gemini_text),
                "qwen_length": word_count(qwen_text),
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

    if get_generation:
        # Always load chunks from the file for the generation step.
        try:
            with open("chunks_for_processing.json", 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            print(f"Loaded {len(chunks)} chunks from chunks_for_processing.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading chunks from file: {e}. Please run with get_chunks=True first.")
            return

        prompts = [create_prompt(chunk['chunk']) for chunk in chunks]

        # 2. Run Qwen first (batched) so results are ready when Gemini finishes each chunk
        print("\n--- Running Qwen generation in batches ---")
        qwen_outputs = [None] * len(prompts)
        qwen_errors_all = [None] * len(prompts)
        for batch_start in tqdm(range(0, len(prompts), QWEN_BATCH_SIZE), desc="Qwen batches", unit="batch"):
            batch_end = batch_start + QWEN_BATCH_SIZE
            batch_prompts = prompts[batch_start:batch_end]
            qwen_texts, qwen_errors = call_local_qwen_batch(batch_prompts)

            for offset, chunk_idx in enumerate(range(batch_start, batch_end)):
                if chunk_idx >= len(chunks):
                    break

                qwen_outputs[chunk_idx] = qwen_texts[offset]
                qwen_errors_all[chunk_idx] = qwen_errors[offset]
                if qwen_errors[offset]:
                    print(f"[qwen-error] {qwen_errors[offset]}")

        # 3. Run Gemini calls and append results immediately using stored Qwen outputs
        model = connect_to_gemini()
        print("\n--- Running Gemini generation for all chunks ---")
        for idx, prompt in enumerate(tqdm(prompts, desc="Gemini generations", unit="chunk"), start=1):
            gemini_text, gemini_error = call_gemini_api(prompt, model)
            if gemini_error:
                print(f"[gemini-error] {gemini_error}")
                gemini_text = None

            append_podcast_result(
                chunks[idx - 1]['chunk'],
                gemini_text,
                qwen_outputs[idx - 1],
            )
            print(f"[info] Podcast texts appended for chunk {idx}/{len(chunks)}")

if __name__=="__main__":
    generate_training_data(training_samples=2000, get_chunks=False, get_generation=True)