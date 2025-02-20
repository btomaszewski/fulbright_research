import json
import numpy as np
from sentence_transformers import SentenceTransformer
import spacy
import re
from typing import List, Dict, Tuple

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def clean_text(text: str) -> str:
    """Cleans text by lowercasing, removing special characters, lemmatizing, and removing stopwords."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    doc = nlp(text)
    cleaned_text = " ".join([token.lemma_ for token in doc if not token.is_stop])
    
    return cleaned_text

class VectorClassifier:
    def __init__(self, model_path: str, category_embeddings_path: str, threshold: float = 0.7):
        """
        Initialize classifier with model and category embeddings.
        
        Args:
            model_path: Path to the trained model
            category_embeddings_path: Path to saved category embeddings
            threshold: Minimum similarity score to assign a category
        """
        self.model = SentenceTransformer(model_path)
        self.threshold = threshold
        
        with open(category_embeddings_path, 'r') as f:
            self.category_embeddings = json.load(f)
            
        # Convert category embeddings to numpy arrays
        self.categories = list(self.category_embeddings.keys())
        self.category_vectors = np.array([self.category_embeddings[cat] for cat in self.categories])
    
    def predict_categories(self, text: str, original_text: str) -> Dict:
        """
        Predict categories for a text with confidence scores.
        Returns results with both cleaned and original text.
        """
        # If cleaned text is empty, return null categories
        if not text.strip():
            return {
                'original_text': original_text,
                'cleaned_text': text,
                'categories': [],
                'confidence_scores': {},
                'status': 'filtered'
            }
        
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
        results = sorted(results, key=lambda x: x[1], reverse=True)
        
        return {
            'original_text': original_text,
            'cleaned_text': text,
            'categories': [cat for cat, _ in results],
            'confidence_scores': [score for _, score in results],
            'status': 'processed'
        }

def categorize(fullText):
    # Configuration
    MODEL_PATH = "vector_model_package/sentence_transformer"
    CATEGORY_EMBEDDINGS_PATH = "vector_model_package/category_embeddings.json"
    
    # Initialize classifier
    classifier = VectorClassifier(
        model_path=MODEL_PATH,
        category_embeddings_path=CATEGORY_EMBEDDINGS_PATH,
        threshold=0.7
    )

    """Process input JSON and save categorized results."""
    cleaned_text = clean_text(fullText)
    
    # Get predictions
    result = classifier.predict_categories(cleaned_text, fullText)
    
    # If no categories were found, assign null
    if not result['categories']:
        result['categories'] = ['null']
    
    return result

'''
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