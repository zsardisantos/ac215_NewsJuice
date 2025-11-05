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

# os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")

GEMINI_SERVICE_ACCOUNT_PATH = os.environ.get("GEMINI_SERVICE_ACCOUNT_PATH", "../../../secrets/gemini-service-account.json")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = ( "us-central1")
QWEN_MODEL_PATH = ("Qwen/Qwen3-0.6B")
QWEN_MAX_NEW_TOKENS = ("512")
QWEN_TEMPERATURE = ("0.7")
PODCAST_LOG_CSV =("podcast_results.csv")
WANDB_PROJECT = "newsjuice-finetune"

try:
    WANDB_API_KEY = os.environ.get("WANDB_API_KEY")
except:
    with open("../../../secrets/wandb_api_key.txt", "r") as f:
        WANDB_API_KEY = f.readline().strip()

try:
    HF_TOKEN = os.environ.get("HF_TOKEN")
except:
    with open("../../../secrets/hf_token.txt", "r") as f:
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
    csv_path: str = PODCAST_LOG_CSV,
    output_csv_path: str = None,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
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
    
    # Load the merged model directly in bfloat16 for fast inference
    print(f"\n🚀 Loading merged model from {merged_model_path}...")
    model = AutoModelForCausalLM.from_pretrained(
        merged_model_path,
        token=HF_TOKEN,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.eval()
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(merged_model_path, token=HF_TOKEN, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("Model and adapter loaded successfully")
    print("Starting inference...")
    
    # Generate predictions for each example
    finetuned_outputs = []
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Inferencing", unit="example"):

        chunk_text = row["chunk_text"]
        if pd.isna(chunk_text) or str(chunk_text).strip() == "":
            finetuned_outputs.append("")
            continue
        
        # Build the prompt in the same format as training
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
        
        # Tokenize and generate
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
        
        # Decode and extract only the generated response (not the prompt)
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        if "### Response:" in full_text:
            response = full_text.split("### Response:")[1].strip()
        else:
            response = full_text[len(prompt):].strip()
        
        finetuned_outputs.append(response)
        
        tqdm.write(f"✅ Processed {idx + 1}/{len(df)} examples")
    
    # Add new column to dataframe
    df["finetuned Qwen 0.6"] = finetuned_outputs
    
    # Save to CSV
    output_path = output_csv_path if output_csv_path else csv_path
    df.to_csv(output_path, index=False)
    
    print("Evaluation completed!")
    
    return output_path


run_predictions_on_finetuned_model()