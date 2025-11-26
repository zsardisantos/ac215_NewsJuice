import pandas as pd
import numpy as np
import torch
from transformers import (
    RobertaTokenizer,
    RobertaForSequenceClassification,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback
)
from datasets import Dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
import wandb
import os

class NewsClassificationTrainer:
    def __init__(self, train_path, test_path, model_name='roberta-base', output_dir='./results'):
        """
        Initialize the trainer for news classification.
        
        Args:
            train_path: Path to training CSV file
            test_path: Path to test CSV file
            model_name: Pretrained model name
            output_dir: Directory to save model and results
        """
        self.train_path = train_path
        self.test_path = test_path
        self.model_name = model_name
        self.output_dir = output_dir
        
        # Load data
        print("Loading training and test data...")
        self.train_df = pd.read_csv(train_path)
        self.test_df = pd.read_csv(test_path)
        
        # Create label mappings
        self.labels = sorted(self.train_df['category'].unique())
        self.label2id = {label: idx for idx, label in enumerate(self.labels)}
        self.id2label = {idx: label for label, idx in self.label2id.items()}
        
        print(f"Number of classes: {len(self.labels)}")
        print(f"Training samples: {len(self.train_df)}")
        print(f"Test samples: {len(self.test_df)}")
        
        # Initialize tokenizer
        print(f"\nLoading tokenizer: {model_name}")
        self.tokenizer = RobertaTokenizer.from_pretrained(model_name)
        
        # Prepare datasets
        self.train_dataset = self._prepare_dataset(self.train_df)
        self.test_dataset = self._prepare_dataset(self.test_df)
        
        # Initialize model
        print(f"Loading model: {model_name}")
        self.model = RobertaForSequenceClassification.from_pretrained(
            model_name,
            num_labels=len(self.labels),
            id2label=self.id2label,
            label2id=self.label2id
        )
        
    def _prepare_dataset(self, df):
        """Convert DataFrame to HuggingFace Dataset with tokenization."""
        # Add numeric labels
        df['label'] = df['category'].map(self.label2id)
        
        # Create dataset
        dataset = Dataset.from_pandas(df[['text', 'label']])
        
        # Tokenize
        def tokenize_function(examples):
            return self.tokenizer(
                examples['text'],
                padding='max_length',
                truncation=True,
                max_length=512
            )
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        return tokenized_dataset
    
    def compute_metrics(self, eval_pred):
        """Compute accuracy, precision, recall, and F1 score."""
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        
        # Calculate metrics
        accuracy = accuracy_score(labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, average='weighted', zero_division=0
        )
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }
    
    def train(self, 
              num_epochs=3,
              batch_size=16,
              learning_rate=2e-5,
              warmup_steps=500,
              weight_decay=0.01,
              use_wandb=True,
              project_name="news-classification-roberta"):
        """
        Train the model with specified hyperparameters.
        
        Args:
            num_epochs: Number of training epochs
            batch_size: Training batch size
            learning_rate: Learning rate
            warmup_steps: Number of warmup steps
            weight_decay: Weight decay for regularization
            use_wandb: Whether to use Weights & Biases for tracking
            project_name: W&B project name
        """
        # Initialize wandb
        if use_wandb:
            wandb.init(
                project=project_name,
                config={
                    "model": self.model_name,
                    "epochs": num_epochs,
                    "batch_size": batch_size,
                    "learning_rate": learning_rate,
                    "num_classes": len(self.labels),
                    "train_samples": len(self.train_df),
                    "test_samples": len(self.test_df)
                }
            )
        
        # Define training arguments
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            weight_decay=weight_decay,
            logging_dir=f'{self.output_dir}/logs',
            logging_steps=100,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            greater_is_better=True,
            report_to="wandb" if use_wandb else "none",
            save_total_limit=2,
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.train_dataset,
            eval_dataset=self.test_dataset,
            compute_metrics=self.compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
        )
        
        # Train the model
        print("\n" + "="*60)
        print("Starting training...")
        print("="*60)
        trainer.train()
        
        # Evaluate on test set
        print("\n" + "="*60)
        print("Evaluating on test set...")
        print("="*60)
        test_results = trainer.evaluate()
        
        print("\nTest Results:")
        for key, value in test_results.items():
            print(f"  {key}: {value:.4f}")
        
        # Get detailed classification report
        predictions = trainer.predict(self.test_dataset)
        pred_labels = np.argmax(predictions.predictions, axis=1)
        true_labels = predictions.label_ids
        
        print("\n" + "="*60)
        print("Classification Report:")
        print("="*60)
        report = classification_report(
            true_labels, 
            pred_labels, 
            target_names=self.labels,
            digits=4
        )
        print(report)
        
        # Save the model
        model_save_path = os.path.join(self.output_dir, 'final_model')
        trainer.save_model(model_save_path)
        self.tokenizer.save_pretrained(model_save_path)
        
        print(f"\nModel saved to: {model_save_path}")
        
        # Save label mappings
        import json
        with open(os.path.join(model_save_path, 'label_mappings.json'), 'w') as f:
            json.dump({
                'label2id': self.label2id,
                'id2label': self.id2label
            }, f, indent=2)
        
        if use_wandb:
            wandb.finish()
        
        return trainer, test_results

if __name__ == "__main__":
    # Initialize trainer
    trainer = NewsClassificationTrainer(
        train_path='train_data.csv',
        test_path='test_data.csv',
        output_dir='./results'
    )
    
    # Train the model
    trained_model, results = trainer.train(
        num_epochs=3,
        batch_size=16,
        learning_rate=2e-5,
        use_wandb=True,
        project_name="news-classification-roberta"
    )
    
    print("\n" + "="*60)
    print("Training complete!")
    print("="*60)
