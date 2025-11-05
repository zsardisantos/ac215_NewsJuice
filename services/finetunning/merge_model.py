#### When running the inference on Qwen 0.6 with the 4bit quantization, each example 
#### Takes about 65 seconds to run. to speed up the inference, this code merges the model with the adapter
#### Merging helped reduce the time from 65 seconds per prompt to 40 seconds
#### After further investigation, i can see that the time taken is primeraly from prefilling (long prompt)

# !pip install bitsandbytes     ## Needed when training on Colab
import os
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# --- Configuration ---
BASE_MODEL_PATH = "Qwen/Qwen3-0.6B"
ADAPTER_PATH = "qwen_qlora_podcast"  # Path to your fine-tuned adapter
MERGED_MODEL_OUTPUT_PATH = "qwen_qlora_podcast_merged"

# Get Hugging Face token
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    try:
        with open("../../../secrets/hf_token.txt", "r") as f:
            HF_TOKEN = f.readline().strip()
    except FileNotFoundError:
        print("⚠️ Hugging Face token file not found. This may cause issues.")
        HF_TOKEN = None

def merge_qlora_model():
    """Merges a QLoRA adapter into the base model and saves the full model."""
    print(f"Base model: {BASE_MODEL_PATH}")
    print(f"Adapter: {ADAPTER_PATH}")
    print(f"Output directory: {MERGED_MODEL_OUTPUT_PATH}")

    # 1. Load the base model with 4-bit quantization
    print("\n1. Loading base model in 4-bit...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_PATH,
        quantization_config=bnb_config,
        trust_remote_code=True,
        token=HF_TOKEN,
        device_map="cpu",  # Load on CPU to avoid VRAM issues during merge
    )

    # 2. Load the PEFT model (applying the adapter)
    print("\n2. Loading PEFT model (adapter)...")
    peft_model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)

    # 3. Merge the adapter into the base model
    print("\n3. Merging adapter into the base model...")
    merged_model = peft_model.merge_and_unload()
    print("✅ Merge complete.")

    # 4. Save the merged model and tokenizer
    print(f"\n4. Saving merged model to {MERGED_MODEL_OUTPUT_PATH}...")
    os.makedirs(MERGED_MODEL_OUTPUT_PATH, exist_ok=True)
    merged_model.save_pretrained(MERGED_MODEL_OUTPUT_PATH)

    # Also save the tokenizer
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH, trust_remote_code=True, token=HF_TOKEN)
    tokenizer.save_pretrained(MERGED_MODEL_OUTPUT_PATH)

    print(f"\n🎉 Merged model saved successfully to {MERGED_MODEL_OUTPUT_PATH}")
    print("You can now load this model directly for fast inference.")

if __name__ == "__main__":
    merge_qlora_model()
