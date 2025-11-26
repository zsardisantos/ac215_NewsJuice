#############################################################################
###### This script is designed to run on colab. It was not tested elsewhere
#############################################################################
###### Dont forget to have the env variables setup in colab
#############################################################################

print("Starting Script")
import os
import csv
import json
from vertexai.generative_models import GenerativeModel
from tqdm import tqdm

print("Loaded Dependancies")
# Configuration

GEMINI_SERVICE_ACCOUNT_PATH =  "../secrets/gemini-service-account.json"    #For running on colab. make sure that the secrets file is placed in the contents folder
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = ( "us-central1")

input_file_path = "Output/01_get_chuncks_from_db.csv"
output_file_path = "Output/02_get_gemini_training_data.csv"

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
    return response, None

def append_podcast_result(chunk_text, gemini_text, csv_path=output_file_path):
    fieldnames = [
        "chunk_text",
        "gemini_podcast_text",
        "gemini_length",
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
                "gemini_length": word_count(gemini_text),
            }
        )

def generate_training_data(training_samples):

  processed_count = 0
  if os.path.exists(output_file_path):
      print(f"Found existing output file. Counting processed rows...")
      try:
          with open(output_file_path, 'r', encoding='utf-8') as f:
              reader = csv.reader(f) 
              processed_count = sum(1 for row in reader) - 1 
              if processed_count < 0:
                   processed_count = 0
          print(f"Found {processed_count} already processed data rows. Will skip.")
      except Exception as e:
          print(f"Warning: Could not read output file {output_file_path}. Starting from scratch. Error: {e}")
          processed_count = 0
  
  chunks_to_process = [] 
  try:
    with open(input_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        print("Found input CSV and loading chunks...")
        
        for i, row in enumerate(reader):
            
            if i >= training_samples:
                print(f"Reached training sample limit of {training_samples}.")
                break 
            
            if i < processed_count:
                continue
            
            chunks_to_process.append(row['content'])
            
  except FileNotFoundError:
      print(f"ERROR: Input file not found at {input_file_path}")
      return
  except Exception as e:
      print(f"ERROR: Failed to read input file. {e}")
      return

  print(f"Total chunks requested: {training_samples}")
  print(f"Already processed: {processed_count}")
  print(f"New chunks to process: {len(chunks_to_process)}")
  
  if not chunks_to_process:
      print("No new chunks to process. Exiting.")
      return

  model = connect_to_gemini()
  if not model:
      print("Failed to connect to Gemini. Aborting.")
      return

  print(f"\n--- Running Gemini generation for {len(chunks_to_process)} new chunks ---")
  
  prompts = [create_prompt(chunk) for chunk in chunks_to_process]

  for idx, prompt in enumerate(tqdm(prompts, desc="Gemini generations", unit="chunk")):
      
      current_chunk_text = chunks_to_process[idx]

      try:
          gemini_response, gemini_error = call_gemini_api(prompt, model)
          
          final_gemini_text = None 
          if gemini_error:
              print(f"\n[gemini-error] API call failed for row {processed_count + idx + 1}: {gemini_error}")
          elif gemini_response:
              try:
                  final_gemini_text = gemini_response.text
              except Exception as e:
                  print(f"\n[gemini-error] Failed to get text for row {processed_count + idx + 1}: {e}")
                  print(f"Full response details: {gemini_response}")
          
          append_podcast_result(
              current_chunk_text,
              final_gemini_text, 
          )
          
      except Exception as e:
          print(f"\n[critical-error] Unhandled exception during processing row {processed_count + idx + 1}: {e}")
          append_podcast_result(
              current_chunk_text,
              f"CRITICAL SCRIPT ERROR: {e}",
          )
  
  print(f"[info] Script finished. Processed {len(chunks_to_process)} new chunks.")


if __name__=="__main__":
    generate_training_data(training_samples=2000)