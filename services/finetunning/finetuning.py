#############################################################################
###### This script is designed to run on colab. It was not tested elsewhere
#############################################################################
###### Dont forget to have the env variables setup in colab
#############################################################################
###### IF bitsandbites WENT THROUGH THE INSTALLATION PROCESS,
###### MAKE SURE TO RESTART THE SESSION, OTHERWISE IT WILL NOT WORK
#############################################################################
###### Data generation references the Cloud SQL, which needs the proxy,
###### So make sure to run the data generation nocally with the proxy running
#############################################################################

# !pip install bitsandbytes         ## Needed when training on Colab
# !pip install psycopg          ## Needed when training on Colab
import os
import csv
import pandas as pd
import torch
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel
import psycopg
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

# Configuration
GEMINI_SERVICE_ACCOUNT_PATH = os.environ.get("GEMINI_SERVICE_ACCOUNT_PATH", "../../../secrets/gemini-service-account.json")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = ( "us-central1")
QWEN_MODEL_PATH = ("Qwen/Qwen3-0.6B")
QWEN_MAX_NEW_TOKENS = ("512")
QWEN_TEMPERATURE = ("0.7")
PODCAST_LOG_CSV =("podcast_results.csv")

try:
    HF_TOKEN = os.environ.get("HF_TOKEN")
except:
    with open("../../../secrets/hf_token.txt", "r") as f:
        HF_TOKEN = f.readline().strip()

_qwen_pipeline = None

def connect_to_gc_db():
    DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:Newsjuice25%2B@dbproxy:5432/newsdb")
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
        with psycopg.connect(DB_URL) as conn:
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
    prompt = f"""You are a news podcast host. Based on the following relevant news articles, create an engaging podcast-style response to the user's question. 
            Please limit the podcast generation to one minute at maximum.  

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
        device = 0 if torch.cuda.is_available() else -1
        _qwen_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device=device,
        )
    return _qwen_pipeline


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


def call_gemini_api(prompt, model):
    """Call Google Gemini API with the question and context articles to generate a podcast-style response."""
    if not model:
        return None, "Gemini API not configured"
        
    response = model.generate_content(prompt)
    return response.text, None


def append_podcast_result(chunk_text, gemini_text, qwen_text, csv_path=PODCAST_LOG_CSV):
    fieldnames = [
        "chunk_text",
        "gemini_podcast_text",
        "qwen_podcast_text",
        "gemini_length",
        "qwen_length",
    ]
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
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
    return (
        "### Instruction:\n"
        "You are a news podcast host. Given the news article snippet, craft a one-minute "
        "podcast-style response that is warm, engaging, and transparent about any gaps.\n\n"
        f"### Input:\n{article_snippet.strip()}\n\n"
        f"### Response:\n{podcast_text.strip()}"
    )


def finetune_qwen_with_qlora(
    csv_path: str = PODCAST_LOG_CSV,
    output_dir: str = ("qwen_qlora_podcast"),
    num_train_epochs: int = 3,
    per_device_train_batch_size: int = 1,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 1024,
    warmup_steps: int = 50,
    logging_steps: int = 10,
    validation_split: float = 0.1,
):
    """Fine-tune the local Qwen model with QLoRA adapters using Gemini podcast outputs.

    Args:
        csv_path: Path to the CSV containing Gemini podcast outputs.
        output_dir: Directory where QLoRA adapters and tokenizer will be saved.
        num_train_epochs: Number of training epochs.
        per_device_train_batch_size: Batch size per device.
        gradient_accumulation_steps: Gradient accumulation steps.
        learning_rate: Learning rate for the optimizer.
        max_seq_length: Maximum token length for each training example.
        warmup_steps: Number of warmup steps.
        logging_steps: Logging frequency for the Trainer.
        validation_split: Fraction of data to use for validation (default 0.1 = 10%).

    Returns:
        The path where the fine-tuned adapter is stored.
    """

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if "gemini_podcast_text" not in df.columns or "chunk_text" not in df.columns:
        raise ValueError("CSV must contain 'chunk_text' and 'gemini_podcast_text' columns")

    df["chunk_text"] = df["chunk_text"].fillna("")
    df["gemini_podcast_text"] = df["gemini_podcast_text"].fillna("")
    df = df[
        (df["chunk_text"].str.strip() != "") & (df["gemini_podcast_text"].str.strip() != "")
    ]

    if df.empty:
        raise ValueError("No valid training rows found in the CSV after cleaning.")

    print(f"\n{'='*60}")
    print("🚀 Starting QLoRA Fine-tuning for Qwen Model")
    print(f"{'='*60}")
    print(f"📊 Training Data: {len(df)} examples loaded from {csv_path}")
    print(f"💾 Output Directory: {output_dir}")
    print(f"🔧 Model: {QWEN_MODEL_PATH}")

    df["text"] = df.apply(lambda row: _build_prompt(row["chunk_text"], row["gemini_podcast_text"]), axis=1)

    dataset = Dataset.from_pandas(df[["text"]])
    dataset = dataset.shuffle(seed=42)
    
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
    
    total_steps = (len(tokenized_train) // (per_device_train_batch_size * gradient_accumulation_steps)) * num_train_epochs
    print(f"\n📈 Training Configuration:")
    print(f"   - Epochs: {num_train_epochs}")
    print(f"   - Batch size: {per_device_train_batch_size}")
    print(f"   - Gradient accumulation: {gradient_accumulation_steps}")
    print(f"   - Effective batch size: {per_device_train_batch_size * gradient_accumulation_steps}")
    print(f"   - Learning rate: {learning_rate}")
    print(f"   - Total training steps: ~{total_steps}")
    print(f"   - Device: {'CUDA' if use_cuda else 'CPU'}")
    print(f"   - Precision: {'BF16' if use_bf16 else 'FP16' if use_cuda else 'FP32'}")

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_steps=warmup_steps,
        logging_steps=logging_steps,
        save_strategy="epoch",
        eval_strategy="epoch" if eval_dataset else "no",
        save_total_limit=2,
        load_best_model_at_end=True if eval_dataset else False,
        metric_for_best_model="eval_loss" if eval_dataset else None,
        fp16=use_cuda and not use_bf16,
        bf16=use_bf16,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        report_to="none",
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

    print(f"\n{'='*60}")
    print("✅ Training completed!")
    print(f"{'='*60}")
    print(f"\n💾 Saving model and tokenizer to: {output_dir}")
    
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print(f"✅ Model saved successfully!")
    print(f"\n📁 Fine-tuned adapter location: {output_dir}")
    print(f"🎉 Fine-tuning complete! You can now load the adapter with PEFT.\n")

    return output_dir


def evaluate_finetuned_model(
    adapter_path: str = "qwen_qlora_podcast",
    csv_path: str = PODCAST_LOG_CSV,
    output_csv_path: str = None,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
):
    """Evaluate the fine-tuned Qwen model on all examples in podcast_results.csv.
    
    Args:
        adapter_path: Path to the fine-tuned LoRA adapter directory.
        csv_path: Path to the input CSV with podcast examples.
        output_csv_path: Path to save the updated CSV. If None, overwrites input CSV.
        max_new_tokens: Maximum tokens to generate.
        temperature: Sampling temperature.
    
    Returns:
        Path to the output CSV file.
    """
    from peft import PeftModel
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    if not os.path.exists(adapter_path):
        raise FileNotFoundError(f"Adapter path not found: {adapter_path}")
    
    print("Evaluating Fine-tuned Qwen Model")
    
    # Load the CSV
    df = pd.read_csv(csv_path)
    if "chunk_text" not in df.columns:
        raise ValueError("CSV must contain 'chunk_text' column")
    
    print(f"Found {len(df)} examples to evaluate")
    
    # Load base model with quantization
    print("\nLoading base model...")
    compute_dtype = _infer_compute_dtype()
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
    )
    
    base_model = AutoModelForCausalLM.from_pretrained(
        QWEN_MODEL_PATH,
        token=HF_TOKEN,
        trust_remote_code=True,
        quantization_config=bnb_config,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    
    # Load the fine-tuned adapter
    print(f"🔧 Loading fine-tuned adapter from {adapter_path}...")
    model = PeftModel.from_pretrained(base_model, adapter_path)
    model.eval()
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(adapter_path, token=HF_TOKEN, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("Model and adapter loaded successfully")
    print("Starting inference...")
    
    # Generate predictions for each example
    finetuned_outputs = []
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    for idx, row in df.iterrows():
        chunk_text = row["chunk_text"]
        if pd.isna(chunk_text) or str(chunk_text).strip() == "":
            finetuned_outputs.append("")
            continue
        
        # Build the prompt in the same format as training
        prompt = (
            "### Instruction:\n"
            "You are a news podcast host. Given the news article snippet, craft a one-minute "
            "podcast-style response that is warm, engaging, and transparent about any gaps.\n\n"
            f"### Input:\n{str(chunk_text).strip()}\n\n"
            "### Response:\n"
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
        
        # Progress indicator
        if (idx + 1) % 10 == 0 or idx == len(df) - 1:
            print(f"✅ Processed {idx + 1}/{len(df)} examples")
    
    # Add new column to dataframe
    df["finetuned Qwen 0.6"] = finetuned_outputs
    
    # Save to CSV
    output_path = output_csv_path if output_csv_path else csv_path
    df.to_csv(output_path, index=False)
    
    print("Evaluation completed!")
    
    return output_path


def generate_training_data(training_samples):
    conn = connect_to_gc_db()
    model = connect_to_gemini()

    for i in range(training_samples):
        chunk, error = get_random_chunk(conn)
        if error:
            print(f"[error] {error}")
        else:
            prompt = create_prompt(chunk['chunk'])
            gemini_podcast_text, gemini_error = call_gemini_api(prompt, model)
            if gemini_error:
                print(f"[gemini-error] {gemini_error}")

            qwen_podcast_text, qwen_error = call_local_qwen(prompt)
            if qwen_error:
                print(f"[qwen-error] {qwen_error}")

            append_podcast_result(
                chunk['chunk'],
                gemini_podcast_text,
                qwen_podcast_text,
            )

        print("[info] Podcast texts appended to podcast_results.csv")

# Test the get_random_chunk function
if __name__ == "__main__":
    ### Run this function to generate training data points. it will take a while to run
    # generate_training_data(training_samples=2)
    # finetune_qwen_with_qlora()
    evaluate_finetuned_model()