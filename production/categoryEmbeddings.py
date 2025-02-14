import json
from sentence_transformers import SentenceTransformer
import numpy as np
from collections import defaultdict

def generate_category_embeddings(model_path: str, training_data_path: str, output_path: str):
    """
    Generate and save average embeddings for each category from training data.
    """
    print("Loading model and training data...")
    model = SentenceTransformer(model_path)
    
    with open(training_data_path, 'r', encoding='utf-8') as f:
        training_data = json.load(f)
    
    # Group texts by category
    category_texts = defaultdict(list)
    for item in training_data:
        for category in item['label']:
            category_texts[category].append(item['text'])
    
    print("\nGenerating category embeddings...")
    category_embeddings = {}
    
    for category, texts in category_texts.items():
        # Generate embeddings for all texts in this category
        embeddings = model.encode(texts)
        # Calculate average embedding for the category
        average_embedding = np.mean(embeddings, axis=0)
        category_embeddings[category] = average_embedding.tolist()
        print(f"Processed category: {category}")
    
    # Save category embeddings
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(category_embeddings, f, indent=2)
    
    print(f"\nCategory embeddings saved to {output_path}")

if __name__ == "__main__":
    # Call the function with your specific paths
    generate_category_embeddings(
        model_path="fine_tuned_model3",
        training_data_path="formatted_clean_export.json",
        output_path="category_embeddings.json"
    )