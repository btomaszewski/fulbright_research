import json
import logging
from typing import List, Dict, Union, Any
import os
import sys
from tqdm import tqdm

# Import the VectorClassifier class
from vectorClassifier import VectorClassifier

# Import the text cleaning function
from cleanText import clean_text

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("classifier.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("json_text_classifier")

# =====================================================================
# CONFIGURATION - MODIFY THESE PATHS TO MATCH YOUR ENVIRONMENT
# =====================================================================

# Path to the SentenceTransformer model
MODEL_PATH = "vector_model_package/sentence_transformer"

# Path to the category embeddings JSON file
CATEGORY_EMBEDDINGS_PATH = "vector_model_package/category_embeddings.json"

# Path to model metadata (optional)
METADATA_PATH = "vector_model_package/metadata.json"

# Classification threshold (0.0 to 1.0)
THRESHOLD = 0.6

# Enable multi-label classification (True/False)
MULTI_LABEL = True

# Path to input JSON file containing texts to classify
INPUT_JSON_PATH = "testVectorModel.json"

# Field name in the JSON that contains the text to classify
TEXT_FIELD = "sentence"

# Path to save the classification results
OUTPUT_PATH = "results/classified_results.json"

# Process in batches (0 for no batching)
BATCH_SIZE = 0

# Output raw classification results instead of enriching original items (True/False)
RAW_OUTPUT = False

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def load_texts_from_json(file_path: str, text_field: str = "text") -> List[Dict[str, Any]]:
    """
    Load texts from a JSON file that contains an array of objects.
    
    Args:
        file_path: Path to the JSON file
        text_field: Field name that contains the text to classify
        
    Returns:
        List of dictionaries from the JSON file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Handle both array and object formats
        if isinstance(data, dict):
            if 'items' in data and isinstance(data['items'], list):
                data = data['items']  # Extract items array if in that format
            else:
                data = [data]  # Convert single object to list
                
        # Validate that each item has the required text field
        valid_items = []
        for i, item in enumerate(data):
            if text_field in item and item[text_field]:
                valid_items.append(item)
            else:
                logger.warning(f"Item {i} is missing the '{text_field}' field and will be skipped")
                
        logger.info(f"Loaded {len(valid_items)} valid items from {file_path}")
        return valid_items
    except Exception as e:
        logger.error(f"Error loading texts from {file_path}: {e}")
        return []

def ensure_directory_exists(file_path: str) -> None:
    """
    Ensure that the directory for the given file path exists.
    
    Args:
        file_path: Path to a file
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def save_results(results: List[Dict], output_path: str) -> None:
    """
    Save classification results to a JSON file.
    
    Args:
        results: List of classification result dictionaries
        output_path: Path to save the results
    """
    try:
        ensure_directory_exists(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Saved results to {output_path}")
    except Exception as e:
        logger.error(f"Error saving results to {output_path}: {e}")

def process_batch(classifier, items: List[Dict[str, Any]], text_field: str, enrich: bool = True) -> List[Dict[str, Any]]:
    """
    Process a batch of items for classification.
    
    Args:
        classifier: Initialized VectorClassifier instance
        items: List of dictionaries with items to classify
        text_field: Field name containing the text to classify
        enrich: Whether to enrich the original items with classification results
        
    Returns:
        List of classification results
    """
    results = []
    
    for item in tqdm(items, desc="Classifying texts", unit="item"):
        original_text = item[text_field]
        cleaned_text = clean_text(original_text)
        
        # Get classification result
        classification_result = classifier.predict_categories(cleaned_text, original_text)
        
        if enrich:
            # Add classification data to the original item
            enriched_item = item.copy()
            enriched_item["classification"] = {
                "categories": classification_result["categories"],
                "confidence_scores": classification_result["confidence_scores"],
                "status": classification_result["status"]
            }
            
            # Add hierarchy info if available
            if "hierarchy_info" in classification_result:
                enriched_item["classification"]["hierarchy_info"] = classification_result["hierarchy_info"]
                
            results.append(enriched_item)
        else:
            # Return the raw classification results
            results.append(classification_result)
    
    return results

def resolve_path(path):
    """
    Resolve a path to an absolute path, checking various locations.
    
    Args:
        path: Path to resolve
        
    Returns:
        Absolute path that exists if possible
    """
    # Convert to absolute path if needed
    if not os.path.isabs(path):
        # First check relative to current directory
        if os.path.exists(path):
            return os.path.abspath(path)
        
        # Then check relative to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_relative_path = os.path.join(script_dir, path)
        if os.path.exists(script_relative_path):
            return script_relative_path
            
        # When packaged with PyInstaller, check relative to executable
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            exe_relative_path = os.path.join(exe_dir, path)
            if os.path.exists(exe_relative_path):
                return exe_relative_path
                
    return path  # Return original path if nothing else works

def main():
    """Main function to run the classifier."""
    # Resolve paths
    model_path = resolve_path(MODEL_PATH)
    category_embeddings_path = resolve_path(CATEGORY_EMBEDDINGS_PATH)
    metadata_path = resolve_path(METADATA_PATH) if METADATA_PATH else None
    input_json_path = resolve_path(INPUT_JSON_PATH)
    
    logger.info(f"Using model path: {model_path}")
    logger.info(f"Using category embeddings path: {category_embeddings_path}")
    if metadata_path:
        logger.info(f"Using metadata path: {metadata_path}")
    logger.info(f"Using input JSON path: {input_json_path}")
    
    # Initialize the classifier
    try:
        classifier = VectorClassifier(
            model_path=model_path,
            category_embeddings_path=category_embeddings_path,
            metadata_path=metadata_path,
            threshold=THRESHOLD,
            multi_label=MULTI_LABEL
        )
        logger.info(f"Initialized classifier with threshold={THRESHOLD}, multi_label={MULTI_LABEL}")
    except Exception as e:
        logger.error(f"Failed to initialize classifier: {e}")
        return
    
    # Process JSON file
    items = load_texts_from_json(input_json_path, TEXT_FIELD)
    if not items:
        logger.error(f"No valid items found in {input_json_path}")
        return
    
    # Process in batches if specified
    if BATCH_SIZE > 0:
        all_results = []
        batch_count = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division
        
        for i in range(batch_count):
            start_idx = i * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(items))
            
            logger.info(f"Processing batch {i+1}/{batch_count} (items {start_idx+1}-{end_idx})")
            batch_items = items[start_idx:end_idx]
            batch_results = process_batch(classifier, batch_items, TEXT_FIELD, not RAW_OUTPUT)
            all_results.extend(batch_results)
            
            # Save intermediate results if multiple batches
            if batch_count > 1:
                base_name, ext = os.path.splitext(OUTPUT_PATH)
                interim_output = f"{base_name}_batch{i+1}{ext}"
                save_results(all_results, interim_output)
        
        # Save final results
        save_results(all_results, OUTPUT_PATH)
        results = all_results
    else:
        # Process all at once
        logger.info(f"Processing {len(items)} items...")
        results = process_batch(classifier, items, TEXT_FIELD, not RAW_OUTPUT)
        save_results(results, OUTPUT_PATH)
    
    # Print summary
    categories_count = {}
    for result in results:
        if RAW_OUTPUT:
            cats = result.get("categories", [])
        else:
            cats = result.get("classification", {}).get("categories", [])
            
        for cat in cats:
            if cat not in categories_count:
                categories_count[cat] = 0
            categories_count[cat] += 1
    
    print("\nClassification Summary:")
    top_categories = sorted(categories_count.items(), key=lambda x: x[1], reverse=True)
    for cat, count in top_categories[:10]:  # Show top 10 categories
        percentage = (count / len(results)) * 100
        print(f"  {cat}: {count} items ({percentage:.1f}%)")
    
    print(f"\nTotal items processed: {len(results)}")
    print(f"Results saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()