import csv
import json
from collections import Counter

def extract_unique_categories(csv_path):
    """
    Extract all unique categories from the studio_results CSV file.
    The category is stored in the 'summary' column as JSON.
    """
    categories = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # Parse the JSON from the summary column
                summary_data = json.loads(row['summary'])
                category = summary_data.get('category', None)
                
                if category:
                    categories.append(category)
            except (json.JSONDecodeError, KeyError) as e:
                # Skip rows with invalid JSON or missing fields
                continue
    
    # Get unique categories and their counts
    category_counts = Counter(categories)
    unique_categories = sorted(category_counts.keys())
    
    print(f"Total rows processed: {len(categories)}")
    print(f"Number of unique categories: {len(unique_categories)}")
    print("\n" + "="*60)
    print("UNIQUE CATEGORIES:")
    print("="*60)
    
    for category in unique_categories:
        print(f"  - {category} (count: {category_counts[category]})")
    
    return unique_categories, category_counts

if __name__ == "__main__":
    csv_path = "studio_results_20251113_0934.csv"
    unique_categories, counts = extract_unique_categories(csv_path)
