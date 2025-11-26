"""
Complete pipeline for finetuning RoBERTa on News Category Classification

This script orchestrates the entire pipeline:
1. Data preprocessing and balancing
2. Model training with wandb tracking
3. Inference on validation CSV
4. Comparison output generation
"""

import os
import sys
from data_preprocessing import load_and_balance_data, save_processed_data
from train_model import NewsClassificationTrainer
from inference import process_csv_and_compare

def load_api_keys():
    """Load API keys from secret files."""
    keys = {}
    
    # Load HuggingFace token
    hf_token_path = os.path.join('..', 'secrets', 'hf_token.txt')
    if os.path.exists(hf_token_path):
        with open(hf_token_path, 'r') as f:
            keys['hf_token'] = f.readline().strip()
        print(f"✓ Loaded HuggingFace token from {hf_token_path}")
    else:
        print(f"⚠ HuggingFace token not found at {hf_token_path} (optional)")
    
    # Load W&B API key
    wandb_key_path = os.path.join('..', 'secrets', 'wandb_api_key.txt')
    if os.path.exists(wandb_key_path):
        with open(wandb_key_path, 'r') as f:
            keys['wandb_key'] = f.readline().strip()
        print(f"✓ Loaded W&B API key from {wandb_key_path}")
        # Set W&B environment variable
        os.environ['WANDB_API_KEY'] = keys['wandb_key']
    else:
        print(f"⚠ W&B API key not found at {wandb_key_path}")
    
    # Set HuggingFace token if available
    if 'hf_token' in keys:
        os.environ['HF_TOKEN'] = keys['hf_token']
    
    return keys

def main():
    print("="*80)
    print(" "*20 + "NEWS CLASSIFICATION PIPELINE")
    print("="*80)
    
    # Load API keys from secret files
    print("\nLoading API keys...")
    api_keys = load_api_keys()
    print()
    
    # Configuration
    CONFIG = {
        'json_path': 'News_Category_Dataset_v3_mapped.json',
        'csv_path': 'studio_results_20251113_0934.csv',
        'samples_per_class': 1000,
        'test_size': 0.2,
        'random_seed': 42,
        'model_name': 'roberta-base',
        'output_dir': './results',
        'num_epochs': 3,
        'batch_size': 16,
        'learning_rate': 2e-5,
        'use_wandb': True,
        'project_name': 'news-classification-roberta'
    }
    
    # Step 1: Data Preprocessing
    print("\n" + "="*80)
    print("STEP 1: DATA PREPROCESSING AND BALANCING")
    print("="*80)
    
    train_df, test_df = load_and_balance_data(
        json_path=CONFIG['json_path'],
        samples_per_class=CONFIG['samples_per_class'],
        test_size=CONFIG['test_size'],
        random_seed=CONFIG['random_seed']
    )
    
    save_processed_data(train_df, test_df)
    
    # Step 2: Model Training
    print("\n" + "="*80)
    print("STEP 2: MODEL TRAINING")
    print("="*80)
    
    trainer = NewsClassificationTrainer(
        train_path='train_data.csv',
        test_path='test_data.csv',
        model_name=CONFIG['model_name'],
        output_dir=CONFIG['output_dir']
    )
    
    trained_model, results = trainer.train(
        num_epochs=CONFIG['num_epochs'],
        batch_size=CONFIG['batch_size'],
        learning_rate=CONFIG['learning_rate'],
        use_wandb=CONFIG['use_wandb'],
        project_name=CONFIG['project_name']
    )
    
    # Step 3: Inference on CSV
    print("\n" + "="*80)
    print("STEP 3: INFERENCE ON VALIDATION CSV")
    print("="*80)
    
    comparison_df = process_csv_and_compare(
        csv_path=CONFIG['csv_path'],
        model_path=os.path.join(CONFIG['output_dir'], 'final_model'),
        output_path='predictions_comparison.csv'
    )
    
    # Final Summary
    print("\n" + "="*80)
    print("PIPELINE COMPLETE!")
    print("="*80)
    print("\nGenerated Files:")
    print("  - train_data.csv: Processed training data")
    print("  - test_data.csv: Processed test data")
    print("  - ./results/final_model/: Trained model and tokenizer")
    print("  - predictions_comparison.csv: Side-by-side comparison of predictions")
    print("\nModel Performance:")
    print(f"  - Test Accuracy: {results.get('eval_accuracy', 0):.4f}")
    print(f"  - Test Precision: {results.get('eval_precision', 0):.4f}")
    print(f"  - Test Recall: {results.get('eval_recall', 0):.4f}")
    print(f"  - Test F1: {results.get('eval_f1', 0):.4f}")
    print("\n" + "="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
