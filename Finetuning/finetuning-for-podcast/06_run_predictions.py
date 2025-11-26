### Observation
### Due to the large prompt, each example takes about 40 seconds to run 

# !pip install bitsandbytes     ## Needed when training on Colab
import os
import pandas as pd
import torch
from tqdm.auto import tqdm

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)

QWEN_MODEL_PATH = ("Qwen/Qwen3-0.6B")
QWEN_MAX_NEW_TOKENS = ("512")
QWEN_TEMPERATURE = ("0.7")
INPUT_FILE_PATH =("Output/03_get_Qwen_initial_response.csv")
OUTPUT_FILE_PATH =("Output/06_Qwen_outpute.csv")

with open("../secrets/hf_token.txt", "r") as f:
    HF_TOKEN = f.readline().strip()

def _infer_compute_dtype():
    """Return the best available compute dtype for QLoRA training."""
    if torch.cuda.is_available():
        try:
            major, _ = torch.cuda.get_device_capability()
            if major >= 8:
                return torch.bfloat16
        except Exception:
            pass
        return torch.float16
    return torch.float32

    
def run_predictions_on_finetuned_model(
    merged_model_path: str = "qwen_qlora_podcast_merged",
    csv_path: str = INPUT_FILE_PATH,
    output_csv_path: str = OUTPUT_FILE_PATH,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    resume: bool = False, 
    save_interval: int = 10 
):

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    if not os.path.exists(merged_model_path):
        raise FileNotFoundError(f"Merged model path not found: {merged_model_path}")
    
    print("Evaluating Merged Fine-tuned Qwen Model")
    
    # Load the CSV
    df = pd.read_csv(csv_path)
    if "chunk_text" not in df.columns:
        raise ValueError("CSV must contain 'chunk_text' column")
    
    print(f"Found {len(df)} examples to evaluate")

    output_column_name = "finetuned Qwen 0.6"
    if output_column_name not in df.columns:
        print(f"Creating new output column: {output_column_name}")
        df[output_column_name] = pd.NA
    else:
        # Ensure column is string type for checking 'nan'
        df[output_column_name] = df[output_column_name].astype(str)
    
    # Load the merged model (rest of this is unchanged)
    print(f"\n🚀 Loading merged model from {merged_model_path}...")
    model = AutoModelForCausalLM.from_pretrained(
        merged_model_path,
        token=HF_TOKEN,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.eval()
    
    tokenizer = AutoTokenizer.from_pretrained(merged_model_path, token=HF_TOKEN, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("Model and adapter loaded successfully")
    print("Starting inference...")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Inferencing", unit="example"):

        if resume and pd.notna(row[output_column_name]) and str(row[output_column_name]).strip() not in ["", "nan", "<NA>"]:
            tqdm.write(f"⏩ Skipping {idx + 1}/{len(df)} (already processed)")
            continue
        
        chunk_text = row["chunk_text"]
        if pd.isna(chunk_text) or str(chunk_text).strip() == "":
            df.loc[idx, output_column_name] = "" 
            continue
        
        # Build the prompt (unchanged)
        prompt = (
            f"""### Instruction:\n
        You are a news podcast host. Based on the following relevant news articles, create an engaging podcast-style script to the user's question. 
        The script must be no longer than 300 words under any circumstance. Make sure you dont go over the spesified word limit You should only include the text of the script. Do not include any of your thoughts or any sound effects.    

        Please create a podcast-style response that:
        1. Starts with a warm, engaging introduction
        2. Directly addresses the user's question using information from the articles
        3. Weaves together insights from the relevant news articles
        4. Maintains a conversational, podcast-like tone
        5. Ends with a thoughtful conclusion that stays within the 300-word limit

        If the articles don't contain enough information to fully answer the question, acknowledge this and provide what insights you can while being transparent about limitations.

        Format your response as if you're speaking directly to the listener in a podcast episode.
            ### Input:\n{str(chunk_text).strip()}\n\n
            ### Response:\n"""
        )
        
        # Tokenize and generate (unchanged)
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        # Decode and extract (unchanged)
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        if "### Response:" in full_text:
            response = full_text.split("### Response:")[1].strip()
        else:
            response = full_text[len(prompt):].strip() 
        print("This is the response")
        print(response)
        df.loc[idx, output_column_name] = response
        
        tqdm.write(f"✅ Processed {idx + 1}/{len(df)} examples")

        if (idx + 1) % save_interval == 0:
            df.to_csv(OUTPUT_FILE_PATH, index=False)
            tqdm.write(f"💾 Checkpoint saved at {idx + 1} rows to {OUTPUT_FILE_PATH}")
    
    # Save final CSV

    df.to_csv(OUTPUT_FILE_PATH, index=False)
    
    print(f"Evaluation completed! Final results saved to {OUTPUT_FILE_PATH}")
    
    return OUTPUT_FILE_PATH


if __name__ == "__main__":
    print("Running predictions in RESUME mode.")
    run_predictions_on_finetuned_model(
        resume=True,
    )