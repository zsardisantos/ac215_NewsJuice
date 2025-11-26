import json
import pandas as pd
from collections import Counter
from sklearn.model_selection import train_test_split
import random

def load_and_balance_data(json_path, samples_per_class=1000, test_size=0.2, random_seed=42):
    """
    Load the News Category Dataset and balance it by sampling equal number of examples per class.
    
    Args:
        json_path: Path to the News_Category_Dataset_v3.json file
        samples_per_class: Number of samples to keep per category (for balancing)
        test_size: Proportion of data to use for testing
        random_seed: Random seed for reproducibility
    
    Returns:
        train_df, test_df: Balanced training and test dataframes
    """
    random.seed(random_seed)
    
    print("Loading data from JSON...")
    data = []
    with open(json_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line.strip())
                data.append(item)
            except json.JSONDecodeError:
                continue
    
    print(f"Loaded {len(data)} total samples")
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Combine headline and short_description for text input
    df['text'] = df['headline'] + " " + df['short_description']
    
    # Keep only necessary columns
    df = df[['text', 'category']]
    
    # Remove any rows with missing values
    df = df.dropna()
    
    print(f"\nOriginal category distribution:")
    category_counts = df['category'].value_counts()
    print(category_counts)
    
    # Balance the dataset by sampling equal number from each category
    print(f"\nBalancing dataset to {samples_per_class} samples per category...")
    balanced_dfs = []
    
    for category in df['category'].unique():
        category_df = df[df['category'] == category]
        
        # If category has fewer samples than desired, take all
        if len(category_df) < samples_per_class:
            balanced_dfs.append(category_df)
            print(f"  {category}: {len(category_df)} samples (less than {samples_per_class})")
        else:
            # Sample exactly samples_per_class
            sampled_df = category_df.sample(n=samples_per_class, random_state=random_seed)
            balanced_dfs.append(sampled_df)
            print(f"  {category}: {samples_per_class} samples")
    
    # Combine all balanced categories
    balanced_df = pd.concat(balanced_dfs, ignore_index=True)
    
    # Shuffle the dataset
    balanced_df = balanced_df.sample(frac=1, random_state=random_seed).reset_index(drop=True)
    
    print(f"\nBalanced dataset size: {len(balanced_df)}")
    print(f"Number of categories: {balanced_df['category'].nunique()}")
    
    # Split into train and test
    train_df, test_df = train_test_split(
        balanced_df, 
        test_size=test_size, 
        stratify=balanced_df['category'],
        random_state=random_seed
    )
    
    print(f"\nTrain size: {len(train_df)}")
    print(f"Test size: {len(test_df)}")
    
    return train_df, test_df

def save_processed_data(train_df, test_df, train_path='train_data.csv', test_path='test_data.csv'):
    """Save processed data to CSV files."""
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    print(f"\nSaved training data to {train_path}")
    print(f"Saved test data to {test_path}")

if __name__ == "__main__":
    # Load and balance the data
    train_df, test_df = load_and_balance_data(
        json_path="News_Category_Dataset_v3.json",
        samples_per_class=1000,
        test_size=0.2,
        random_seed=42
    )
    
    # Save processed data
    save_processed_data(train_df, test_df)
    
    print("\n" + "="*60)
    print("Data preprocessing complete!")
    print("="*60)
