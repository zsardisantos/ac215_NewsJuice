
###### IF bitsandbites WENT THROUGH THE INSTALLATION PROCESS,
###### MAKE SURE TO RESTART THE SESSION, OTHERWISE IT WILL NOT WORK

# !pip install bitsandbytes     ## Needed when training on Colab
# !pip install psycopg          ## Needed when training on Colab
# !pip install wandb            ## Needed when training on Colab

print("Starting Finetuning")
import os
import pandas as pd
import torch
import wandb
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
    pipeline,
)

print("Loaded Dependancies")

# Configuration
QWEN_MODEL_PATH = ("Qwen/Qwen3-0.6B")
QWEN_MAX_NEW_TOKENS = ("512")
QWEN_TEMPERATURE = ("0.7")
INPUT_FILE_PATH = "Output/02_get_gemini_training_data.csv"
WANDB_PROJECT = "newsjuice-finetune"

with open("../secrets/wandb_api_key.txt", "r") as f:
    WANDB_API_KEY = f.readline().strip()

with open("../secrets/hf_token.txt", "r") as f:
    HF_TOKEN = f.readline().strip()

if WANDB_API_KEY:
    wandb.login(key=WANDB_API_KEY)
    wandb.init(project=WANDB_PROJECT)

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


def _build_prompt(article_snippet: str, podcast_text: str) -> str:
    """Format training example into an instruction-style prompt."""

    article_snippet = "" if pd.isna(article_snippet) else str(article_snippet).strip()
    podcast_text = "" if pd.isna(podcast_text) else str(podcast_text).strip()

    return (
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
        ### Input:\n{article_snippet}\n\n
        ### Response:\n{podcast_text}"""
    )

def load_csv(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if "gemini_podcast_text" not in df.columns or "chunk_text" not in df.columns:
        raise ValueError("CSV must contain 'chunk_text' and 'gemini_podcast_text' columns")

    df["chunk_text"] = df["chunk_text"].dropna()
    df["gemini_podcast_text"] = df["gemini_podcast_text"].dropna()
    df = df[
        (df["chunk_text"].str.strip() != "") & (df["gemini_podcast_text"].str.strip() != "")
    ]

    if df.empty:
        raise ValueError("No valid training rows found in the CSV after cleaning.")

    return df

def split_train_test_and_tokanize(dataset, validation_split, max_seq_length):
        # Split into train and validation sets
    if validation_split > 0 and len(dataset) > 1:
        split_dataset = dataset.train_test_split(test_size=validation_split, seed=42)
        train_dataset = split_dataset["train"]
        eval_dataset = split_dataset["test"]
        print(f"📊 Dataset split: {len(train_dataset)} train / {len(eval_dataset)} validation")
    else:
        train_dataset = dataset
        eval_dataset = None
        print(f"⚠️  No validation split - training on all {len(train_dataset)} examples")

    tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL_PATH, token=HF_TOKEN, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    def tokenize_fn(batch):
        return tokenizer(
            batch["text"],
            padding=False,
            truncation=True,
            max_length=max_seq_length,
        )

    print("\n🔤 Tokenizing dataset...")
    tokenized_train = train_dataset.map(tokenize_fn, batched=True, remove_columns=train_dataset.column_names)
    tokenized_eval = eval_dataset.map(tokenize_fn, batched=True, remove_columns=eval_dataset.column_names) if eval_dataset else None
    print(f"✅ Tokenization complete: {len(tokenized_train)} train examples" + (f", {len(tokenized_eval)} validation examples" if tokenized_eval else ""))

    return tokenized_train, tokenized_eval, tokenizer


def finetune_qwen_with_qlora(
    csv_path: str = INPUT_FILE_PATH,
    output_dir: str = ("qwen_qlora_podcast"),
    num_train_epochs: int = 10,
    per_device_train_batch_size: int = 1,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 1024,
    warmup_steps: int = 20,
    logging_steps: int = 10,
    validation_split: float = 0.1,
):

    df = load_csv(csv_path)

    print("Starting QLoRA Fine-tuning for Qwen Model")
    print(f"Training Data: {len(df)} examples loaded from {csv_path}")
    print(f"Model: {QWEN_MODEL_PATH}")

    df["text"] = df.apply(lambda row: _build_prompt(row["chunk_text"], row["gemini_podcast_text"]), axis=1)

    dataset = Dataset.from_pandas(df[["text"]])
    dataset = dataset.shuffle(seed=42)
    
    tokenized_train, tokenized_eval, tokenizer = split_train_test_and_tokanize(dataset, validation_split, max_seq_length)

    compute_dtype = _infer_compute_dtype()
    print(f"\n⚙️  Compute dtype: {compute_dtype}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
    )

    print("\n📥 Loading model with 4-bit quantization...")
    model = AutoModelForCausalLM.from_pretrained(
        QWEN_MODEL_PATH,
        token=HF_TOKEN,
        trust_remote_code=True,
        quantization_config=bnb_config,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    print("✅ Model loaded successfully")

    model = prepare_model_for_kbit_training(model)
    lora_config = LoraConfig(
        r=64,
        lora_alpha=16,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.config.use_cache = False
    
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"\n🎯 LoRA Configuration:")
    print(f"   - Rank (r): {lora_config.r}")
    print(f"   - Alpha: {lora_config.lora_alpha}")
    print(f"   - Dropout: {lora_config.lora_dropout}")
    print(f"   - Trainable params: {trainable_params:,} ({100 * trainable_params / total_params:.2f}%)")
    print(f"   - Total params: {total_params:,}")

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    os.makedirs(output_dir, exist_ok=True)

    use_cuda = torch.cuda.is_available()
    use_bf16 = use_cuda and compute_dtype == torch.bfloat16
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_steps=warmup_steps,
        logging_steps=logging_steps,
        save_strategy="epoch",
        eval_strategy="epoch" if tokenized_eval else "no",
        save_total_limit=2,
        load_best_model_at_end=True if tokenized_eval else False,
        metric_for_best_model="eval_loss" if tokenized_eval else None,
        fp16=use_cuda and not use_bf16,
        bf16=use_bf16,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        report_to="wandb" if WANDB_API_KEY else "none",
        remove_unused_columns=False,
        logging_first_step=True,
        disable_tqdm=False,
    )

    print(f"\n{'='*60}")
    print("🏋️  Starting training...")
    print(f"{'='*60}\n")

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_eval,
        data_collator=data_collator,
    )

    trainer.train()
    print("Training completed!")
    print(f"\nSaving model and tokenizer to: {output_dir}")
    
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print(f"Model saved successfully!")
    print(f"\nFine-tuned adapter location: {output_dir}")
    print(f" Fine-tuning complete! You can now load the adapter with PEFT.\n")

    return output_dir

# Test the get_random_chunk function
if __name__ == "__main__":
    ### Run this function to generate training data points. it will take a while to run
    finetune_qwen_with_qlora()
    