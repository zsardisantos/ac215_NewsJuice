import json
from pathlib import Path
import sys

def apply_mapping(original_dataset_path, mapping_path, new_dataset_path):
    """
    Applies category mappings to the dataset and saves a new version.
    """
    # 1. Load the category mapping
    with open(mapping_path, 'r', encoding='utf-8') as f:
        category_mapping = json.load(f)
    print(f"✓ Loaded {len(category_mapping)} category mappings.")

    # 2. Process the original dataset and apply mappings
    total_lines = 0
    processed_lines = 0
    print(f"\nProcessing original dataset: {original_dataset_path}")
    
    with open(original_dataset_path, 'r', encoding='utf-8') as infile, \
         open(new_dataset_path, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            total_lines += 1
            try:
                data = json.loads(line.strip())
                original_category = data.get('category')

                if original_category and original_category in category_mapping:
                    # Replace the category with the mapped value
                    data['category'] = category_mapping[original_category]
                    
                    # Write the updated record to the new file
                    outfile.write(json.dumps(data) + '\n')
                    processed_lines += 1
                else:
                    # If category is missing or not in mapping, write it as is
                    outfile.write(line)

            except json.JSONDecodeError:
                # If a line is not valid JSON, write it as is
                outfile.write(line)
                continue

    print("\n" + "="*80)
    print("Processing Complete!")
    print(f"  - Total lines read: {total_lines}")
    print(f"  - Lines with mapped categories: {processed_lines}")
    print(f"✓ New dataset saved to: {new_dataset_path}")
    print("="*80)

if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    
    # Default paths
    default_original_dataset = script_dir.parent / "News_Category_Dataset_v3.json"
    default_mapping = script_dir / "category_mapping.json"
    default_new_dataset = script_dir.parent / "News_Category_Dataset_v3_mapped.json"

    # Allow overriding paths via CLI arguments
    original_dataset = Path(sys.argv[1]) if len(sys.argv) > 1 else default_original_dataset
    mapping_file = Path(sys.argv[2]) if len(sys.argv) > 2 else default_mapping
    new_dataset = Path(sys.argv[3]) if len(sys.argv) > 3 else default_new_dataset

    # Verify paths exist
    if not original_dataset.exists():
        raise FileNotFoundError(f"Original dataset not found at: {original_dataset}")
    if not mapping_file.exists():
        raise FileNotFoundError(f"Mapping file not found at: {mapping_file}")

    apply_mapping(original_dataset, mapping_file, new_dataset)
