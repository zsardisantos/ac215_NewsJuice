#############################################################################
###### This script is designed to run on colab. It was not tested elsewhere
#############################################################################
###### Dont forget to have the env variables setup in colab
#############################################################################
print("Starting Qwen Generation Without finetuning")

import os
import csv
import json
import torch
from vertexai.generative_models import GenerativeModel
from tqdm import tqdm
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
)

print("Loaded Dependancies")

# Configuration

QWEN_MODEL_PATH = ("Qwen/Qwen3-0.6B")
QWEN_MAX_NEW_TOKENS = int(300 * 1.5)
QWEN_TEMPERATURE = (0.7)
QWEN_BATCH_SIZE = 4    #Running Qwen in batches of 4 for quicker generation

INPUT_FILE_PATH = "Output/02_get_gemini_training_data.csv"
OUTPUT_FILE_PATH = "Output/03_get_Qwen_initial_response.csv"

_qwen_pipeline = None

with open("../secrets/hf_token.txt", "r") as f:
    HF_TOKEN = f.readline().strip()

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
              texts.append(generated[len(prompt):].strip())

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

def append_podcast_result(chunk_text, gemini_text, qwen_text, csv_path=OUTPUT_FILE_PATH):
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


def generate_qwen_initial_response(training_samples):
  
  # This list will hold the full rows from the input CSV
  input_data = [] 
  with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
      reader = csv.DictReader(f)
      print("Found CSV and Loading it")
      for i, row in enumerate(reader):
          if i >= training_samples:
              break 
          
          # Save the whole row so we have 'content' AND 'gemini_podcast_text'
          input_data.append(row)

  prompts = [create_prompt(row['chunk_text']) for row in input_data]

  print("\n--- Running Qwen generation in batches ---")
  
  # Loop over the prompts in batches
  for batch_start in tqdm(range(0, len(prompts), QWEN_BATCH_SIZE), desc="Qwen batches", unit="batch"):
      batch_end = batch_start + QWEN_BATCH_SIZE
      batch_prompts = prompts[batch_start:batch_end]
      
      # Get Qwen outputs for the batch
      qwen_texts, qwen_errors = call_local_qwen_batch(batch_prompts)

      for offset, chunk_idx in enumerate(range(batch_start, batch_end)):
          if chunk_idx >= len(input_data):
              break
          
          original_row = input_data[chunk_idx]
          qwen_text_result = qwen_texts[offset]
          qwen_error = qwen_errors[offset]

          if qwen_error:
              print(f"[qwen-error] {qwen_error}")

          append_podcast_result(
              chunk_text=original_row['chunk_text'],
              gemini_text=original_row['gemini_podcast_text'],
              qwen_text=qwen_text_result,
              csv_path=OUTPUT_FILE_PATH 
          )

if __name__=="__main__":
  generate_qwen_initial_response(training_samples=2000)