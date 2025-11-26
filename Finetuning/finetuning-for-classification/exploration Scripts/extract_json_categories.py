import json
from collections import Counter
from pathlib import Path
import sys
import pandas as pd

def extract_unique_categories(json_path, output_csv_path=None):
    """
    Extract all unique categories from the News_Category_Dataset_v3.json file.
    Each line is a separate JSON object with a 'category' field.
    Optionally save the category counts to a CSV file.
    """
    categories = []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                category = data.get('category', None)
                
                if category:
                    categories.append(category)
            except json.JSONDecodeError as e:
                # Skip invalid JSON lines
                continue
    
    # Get unique categories and their counts
    category_counts = Counter(categories)
    sorted_categories = sorted(category_counts.items(), key=lambda x: (x[1], x[0]))

    print(f"Total rows processed: {len(categories)}")
    print(f"Number of unique categories: {len(sorted_categories)}")
    print("\n" + "="*60)
    print("UNIQUE CATEGORIES:")
    print("="*60)
    
    for category, count in sorted_categories:
        print(f"  - {category} (count: {count})")

    # Save to CSV if requested
    if output_csv_path:
        counts_df = pd.DataFrame(
            {
                "category": [category for category, _ in sorted_categories],
                "count": [count for _, count in sorted_categories]
            }
        )
        counts_df.to_csv(output_csv_path, index=False)
        print(f"\nSaved category counts to {output_csv_path}")

    return [category for category, _ in sorted_categories], category_counts

if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    default_path = script_dir.parent / "News_Category_Dataset_v3_mapped.json"
    json_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_path
    output_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else (script_dir / "category_counts.csv")

    if not json_path.exists():
        raise FileNotFoundError(f"Could not find dataset at {json_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    unique_categories, counts = extract_unique_categories(json_path, output_csv_path=output_path)
