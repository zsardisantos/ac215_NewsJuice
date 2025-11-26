# Fine-tuning Experiments

This directory contains experimental fine-tuning work aimed at improving the NewsJuice application. Two main approaches were explored:

1. **Podcast Script Generation** - Fine-tuning Qwen to reduce latency compared to Gemini
2. **Article Classification** - Fine-tuning RoBERTa/DistilBERT for news categorization

> **Status**: Both experiments were ultimately **not adopted** for production. See details below.

---

## 1. Podcast Script Generation (Qwen Fine-tuning)

### Motivation

The production system uses **Gemini 2.5 Flash** to generate podcast-style scripts from news article chunks. While Gemini produces high-quality output, it has a latency of approximately **~7 seconds per generation**. The goal was to fine-tune a smaller, self-hosted model (Qwen 0.6B) to replicate Gemini's output quality with reduced latency.

### Approach

1. **Data Generation** (`1_finetuning-for-podcast-Generate-Data.ipynb`)
   - Extracted 2,000 random article chunks from the PostgreSQL database
   - Generated podcast scripts using Gemini as the "teacher" model
   - Saved chunk-script pairs to `podcast_results.csv`

2. **QLoRA Fine-tuning** (`2_finetune-for-podcast-pipeline.ipynb`)
   - Base model: `Qwen/Qwen3-0.6B`
   - Technique: QLoRA with 4-bit quantization
   - Training: 3 epochs, 1800 train / 200 validation split
   - LoRA config: rank=64, alpha=16, dropout=0.05
   - Trainable parameters: 40.3M (9.7% of total)

3. **Model Merging & Inference** (`3_finetune-for-podcast-predictions.ipynb`)
   - Merged LoRA adapter into base model for faster inference
   - Ran predictions on the validation set

### Training Metrics

![Podcast Qwen Training Loss](../../Finetuning/wandb%20Screenshots/Podcast_qwen06_train.png)

![Podcast Qwen Evaluation](../../Finetuning/wandb%20Screenshots/Podcast_Qwen06_Eval.png)

### Results & Conclusion

| Metric | Gemini 2.5 Flash | Qwen 0.6B (Fine-tuned) |
|--------|------------------|------------------------|
| Latency | ~7 seconds | ~45 seconds |
| Quality | High | Lower (inconsistent) |

**Outcome**: The experiment was **not successful**. Despite fine-tuning:
- **Latency increased** to ~45 seconds per prompt (vs. 7s for Gemini)
- The bottleneck was identified as **prefilling time** due to long context prompts
- Output quality did not match Gemini's coherence and style
- Even after merging the adapter (reducing from 65s to 40s), performance remained unacceptable

The team concluded that for this use case, Gemini's API latency is acceptable given its superior quality, and self-hosting a small model does not provide benefits.

---

## 2. Article Classification (RoBERTa/DistilBERT)

### Motivation

The goal was to automatically classify news articles into predefined categories to enable fixed-category filtering and organization within the application.

### Approach

Located in `finetuning-for-classification/`:

1. **Data Preprocessing** (`data_preprocessing.py`)
   - Dataset: HuffPost News Category Dataset (209,527 articles) (source:https://www.kaggle.com/datasets/rmisra/news-category-dataset)
   - Balanced to 1,000 samples per category (29 categories)
   - Train/test split: 80/20 (23,200 train / 5,800 test)

2. **Model Training** (`train_model.py`, `run_pipeline.py`)
   - Models tested: RoBERTa-base, DistilBERT
   - Training: 3 epochs with early stopping
   - Metrics tracked via Weights & Biases

3. **Inference** (`inference.py`)
   - Evaluated on external validation CSV
   - Generated prediction comparisons

### Training Metrics

#### DistilBERT

![Classification DistilBERT Training](../../Finetuning/wandb%20Screenshots/Classification_Distillbert_Train.png)

![Classification DistilBERT Evaluation](../../Finetuning/wandb%20Screenshots/Classification%20Distillbert%20Eval.png)

#### RoBERTa

![Classification RoBERTa](../../Finetuning/wandb%20Screenshots/Classification%20_%20RoBerta.png)

![Classification RoBERTa Evaluation](../../Finetuning/wandb%20Screenshots/Classification_Roberta_Eval.png)

### Results

| Model | Test Accuracy | Precision | Recall | F1 |
|-------|---------------|-----------|--------|-----|
| RoBERTa-base | 68.78% | 68.83% | 68.78% | 68.71% |
| DistilBERT | ~65% | - | - | - |

**Per-category performance** (RoBERTa, selected):
- Best: WEDDINGS (86.1% F1), FOOD & DRINK (83.8% F1), DIVORCE (83.5% F1)
- Worst: IMPACT (52.5% F1), WOMEN (55.0% F1), BLACK VOICES (56.5% F1)

### Conclusion

**Outcome**: This experiment was **aborted**. The team decided to pivot toward **pre-retrieval optimization** strategies instead of fixed classification:
- Classification accuracy (~69%) was not sufficient for production use
- Many categories had significant overlap (e.g., PARENTING vs PARENTS)
- The team determined that dynamic retrieval-based approaches would better serve user needs than rigid category assignments

---

## Directory Structure

```
V2/Finetuning/
├── README.md                                    # This file
├── 1_finetuning-for-podcast-Generate-Data.ipynb # Data generation for podcast
├── 2_finetune-for-podcast-pipeline.ipynb        # QLoRA training pipeline
├── 3_finetune-for-podcast-predictions.ipynb     # Inference & evaluation
├── Classification-pipeline.ipynb                # Classification notebook
├── wandb Screenshots/                           # Training visualizations
│   ├── Podcast_qwen06_train.png
│   ├── Podcast_Qwen06_Eval.png
│   ├── Classification_Distillbert_Train.png
│   ├── Classification Distillbert Eval.png
│   ├── Classification _ RoBerta.png
│   └── Classification_Roberta_Eval.png
├── finetuning-for-podcast/                      # Podcast fine-tuning scripts
│   ├── 00_Finetuning pipeline.ipynb
│   ├── 01_get_chucks_from_db.py
│   ├── 02_get_gemini_training_data.py
│   ├── 03_get_Qwen_initial_response.py
│   ├── 04_finetuning.py
│   ├── 05_merge_model.py
│   ├── 06_run_predictions.py
│   └── Output/
└── finetuning-for-classification/               # Classification scripts
    ├── run_pipeline.py
    ├── data_preprocessing.py
    ├── train_model.py
    ├── inference.py
    ├── requirements.txt
    └── News_Category_Dataset_v3.json
```

---

## Requirements

### Podcast Fine-tuning
```
torch
transformers
peft
bitsandbytes
datasets
wandb
psycopg
vertexai
```

### Classification
```
torch
transformers
datasets
scikit-learn
pandas
wandb
```

---

## Key Learnings

1. **Small models struggle with long-context tasks** - The prefilling overhead for Qwen negated any potential latency gains
2. **Teacher-student distillation has limits** - Smaller models cannot always replicate larger model quality
3. **Classification granularity matters** - 29 overlapping categories led to confusion; fewer, well-defined categories might perform better
4. **Pre-retrieval > Post-classification** - For news applications, optimizing retrieval is more impactful than rigid categorization
