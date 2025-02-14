import json
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple

class VectorClassifier:
    def __init__(self, model_path: str, category_embeddings_path: str, threshold: float = 0.7):
        """
        Initialize classifier with model and category embeddings.
        
        Args:
            model_path: Path to the trained model
            category_embeddings_path: Path to saved category embeddings
            threshold: Minimum similarity score to assign a category
        """
        print("Loading model...")
        self.model = SentenceTransformer(model_path)
        self.threshold = threshold
        
        print("Loading category embeddings...")
        with open(category_embeddings_path, 'r') as f:
            self.category_embeddings = json.load(f)
            
        # Convert category embeddings to numpy arrays
        self.categories = list(self.category_embeddings.keys())
        self.category_vectors = np.array([self.category_embeddings[cat] for cat in self.categories])
    
    def predict_categories(self, text: str) -> List[Tuple[str, float]]:
        """
        Predict categories for a text with confidence scores.
        """
        # Generate embedding for input text
        text_embedding = self.model.encode(text)
        
        # Calculate similarities with all category embeddings
        similarities = np.dot(self.category_vectors, text_embedding) / (
            np.linalg.norm(self.category_vectors, axis=1) * np.linalg.norm(text_embedding)
        )
        
        # Get categories above threshold
        results = []
        for cat, score in zip(self.categories, similarities):
            if score >= self.threshold:
                results.append((cat, float(score)))
        
        # Sort by similarity score
        return sorted(results, key=lambda x: x[1], reverse=True)

def process_input_file(input_file: str, output_file: str, classifier: VectorClassifier):
    """Process input JSON and save categorized results."""
    # Load input data
    with open(input_file, 'r', encoding='utf-8') as f:
        input_data = json.load(f)
    
    # Process each entry
    output_data = []
    total_entries = len(input_data)
    
    print(f"\nProcessing {total_entries} entries...")
    for i, entry in enumerate(input_data, 1):
        text = entry['text']
        predictions = classifier.predict_categories(text)
        
        # Create output entry
        output_entry = {
            'text': text,
            'categories': [cat for cat, _ in predictions],
            'confidence_scores': {cat: score for cat, score in predictions}
        }
        output_data.append(output_entry)
        
        if i % 10 == 0:
            print(f"Processed {i}/{total_entries} entries...")
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessing complete. Results saved to {output_file}")

def main():
    # Configuration
    MODEL_PATH = "fine_tuned_model3"
    CATEGORY_EMBEDDINGS_PATH = "category_embeddings.json"
    INPUT_FILE = "input_data.json"
    OUTPUT_FILE = "categorized_output.json" 
    
    # Initialize classifier
    classifier = VectorClassifier(
        model_path=MODEL_PATH,
        category_embeddings_path=CATEGORY_EMBEDDINGS_PATH,
        threshold=0.7
    )
    
    # Process input file
    process_input_file(INPUT_FILE, OUTPUT_FILE, classifier)

if __name__ == "__main__":
    main()
'''
from sentence_transformers import SentenceTransformer
import json
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from tqdm import tqdm  # Import tqdm for progress bar

# Load your trained embedding model (replace with your actual model path)
embedder = SentenceTransformer('fine_tuned_model2')

# Load data from JSON file
with open('testVectorModel.json', 'r') as f:
    data = json.load(f)

# Extract sentences
message = [item['sentence'] for item in data]
queries = ["Barriers to Education", "Access to Healthcare", "Employment"]

# Embed all sentences in the file with a progress bar
print("Embedding sentences...")
message_embeddings = np.array(list(tqdm(
    embedder.encode(message, convert_to_tensor=True),
    total=len(message),
    desc="Embedding Sentences"
)))

# Embed query sentences with progress bar
print("Embedding queries...")
queries_embeddings = np.array(list(tqdm(
    embedder.encode(queries, convert_to_tensor=True),
    total=len(queries),
    desc="Embedding Queries"
)))

# Find the closest 5 sentences for each query based on cosine similarity
top_k = 5
for query, query_embedding in tqdm(
    zip(queries, queries_embeddings), 
    total=len(queries), 
    desc="Processing Queries"
):
    # Compute cosine similarity
    similarity_scores = cosine_similarity(
        query_embedding.reshape(1, -1), 
        message_embeddings
    ).flatten()
    
    # Get the top 5 most similar sentences
    top_k_indices = np.argsort(similarity_scores)[::-1][:top_k]
    
    print("\nQuery:", query)
    print("Top 5 most similar sentences in file:")
    for idx in top_k_indices:
        print(f"{message[idx]} (Score: {similarity_scores[idx]:.4f})") 
'''