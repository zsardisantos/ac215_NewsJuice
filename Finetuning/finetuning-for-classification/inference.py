import pandas as pd
import json
import torch
from transformers import RobertaTokenizer, RobertaForSequenceClassification
from tqdm import tqdm
import os

class NewsClassifier:
    def __init__(self, model_path):
        """
        Initialize the classifier with a trained model.
        
        Args:
            model_path: Path to the saved model directory
        """
        print(f"Loading model from {model_path}...")
        
        # Load tokenizer and model
        self.tokenizer = RobertaTokenizer.from_pretrained(model_path)
        self.model = RobertaForSequenceClassification.from_pretrained(model_path)
        
        # Load label mappings
        with open(os.path.join(model_path, 'label_mappings.json'), 'r') as f:
            mappings = json.load(f)
            self.id2label = {int(k): v for k, v in mappings['id2label'].items()}
        
        # Set device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        self.model.eval()
        
        print(f"Model loaded successfully on {self.device}")
        print(f"Number of classes: {len(self.id2label)}")
    
    def predict(self, text):
        """
        Predict the category for a single text.
        
        Args:
            text: Input text string
            
        Returns:
            predicted_label: Predicted category
            confidence: Confidence score
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            padding='max_length',
            truncation=True,
            max_length=512,
            return_tensors='pt'
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)
            predicted_class = torch.argmax(probabilities, dim=1).item()
            confidence = probabilities[0][predicted_class].item()
        
        predicted_label = self.id2label[predicted_class]
        
        return predicted_label, confidence
    
    def predict_batch(self, texts, batch_size=32):
        """
        Predict categories for a batch of texts.
        
        Args:
            texts: List of text strings
            batch_size: Batch size for processing
            
        Returns:
            predictions: List of (predicted_label, confidence) tuples
        """
        predictions = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Predicting"):
            batch_texts = texts[i:i+batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch_texts,
                padding='max_length',
                truncation=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1)
                predicted_classes = torch.argmax(probabilities, dim=1)
                confidences = torch.max(probabilities, dim=1).values
            
            # Convert to labels
            for pred_class, confidence in zip(predicted_classes, confidences):
                predicted_label = self.id2label[pred_class.item()]
                predictions.append((predicted_label, confidence.item()))
        
        return predictions

def process_csv_and_compare(csv_path, model_path, output_path='predictions_comparison.csv'):
    """
    Run the trained model on the CSV file and create a comparison output.
    
    Args:
        csv_path: Path to the studio_results CSV file
        model_path: Path to the trained model
        output_path: Path to save the comparison results
    """
    print("="*60)
    print("Running inference on CSV file...")
    print("="*60)
    
    # Load CSV
    print(f"\nLoading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows")
    
    # Extract text and original categories
    texts = []
    original_categories = []
    missing_summary_count = 0
    
    for idx, row in df.iterrows():
        # Combine title and content for text
        text = str(row.get('title', '')) + " " + str(row.get('content', ''))
        texts.append(text)
        
        # Extract category from summary JSON
        try:
            summary = row['summary']
            # Check if summary is a valid string (not NaN or float)
            if pd.isna(summary) or not isinstance(summary, str):
                original_categories.append('Unknown')
                missing_summary_count += 1
            else:
                summary_data = json.loads(summary)
                category = summary_data.get('category', 'Unknown')
                original_categories.append(category)
        except (json.JSONDecodeError, KeyError, TypeError):
            original_categories.append('Unknown')
            missing_summary_count += 1
    
    # Report missing summaries
    if missing_summary_count > 0:
        print(f"\n⚠ Warning: {missing_summary_count} rows have missing or invalid summary data")
        print(f"  These will be labeled as 'Unknown' in the comparison output")
    
    # Initialize classifier
    classifier = NewsClassifier(model_path)
    
    # Make predictions
    print("\nMaking predictions...")
    predictions = classifier.predict_batch(texts, batch_size=32)
    
    # Create comparison DataFrame
    comparison_df = pd.DataFrame({
        'id': df['id'],
        'title': df['title'],
        'summary_category': original_categories,
        'predicted_category': [pred[0] for pred in predictions],
        'confidence': [pred[1] for pred in predictions],
        'match': [orig.upper() == pred[0].upper() for orig, pred in zip(original_categories, [p[0] for p in predictions])]
    })
    
    # Save results
    comparison_df.to_csv(output_path, index=False)
    print(f"\nComparison results saved to: {output_path}")
    
    # Print summary statistics
    print("\n" + "="*60)
    print("Summary Statistics:")
    print("="*60)
    print(f"Total samples: {len(comparison_df)}")
    print(f"Exact matches: {comparison_df['match'].sum()} ({comparison_df['match'].mean()*100:.2f}%)")
    print(f"Average confidence: {comparison_df['confidence'].mean():.4f}")
    print(f"\nTop 10 most common predicted categories:")
    print(comparison_df['predicted_category'].value_counts().head(10))
    
    # Show some examples
    print("\n" + "="*60)
    print("Sample Predictions (first 5):")
    print("="*60)
    for idx in range(min(5, len(comparison_df))):
        row = comparison_df.iloc[idx]
        print(f"\nTitle: {row['title'][:80]}...")
        print(f"Original Category: {row['summary_category']}")
        print(f"Predicted Category: {row['predicted_category']}")
        print(f"Confidence: {row['confidence']:.4f}")
        print(f"Match: {'✓' if row['match'] else '✗'}")
    
    return comparison_df

if __name__ == "__main__":
    # Run inference on the CSV file
    comparison_df = process_csv_and_compare(
        csv_path='studio_results_20251113_0934.csv',
        model_path='./results/final_model',
        output_path='predictions_comparison.csv'
    )
    
    print("\n" + "="*60)
    print("Inference complete!")
    print("="*60)
