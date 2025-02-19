import json
import numpy as np
from sentence_transformers import SentenceTransformer
import re
from typing import List, Dict, Tuple
import unicodedata
import contractions


def clean_text(text: str) -> str:

    # Normalize Unicode characters (fix encoding issues)
    text = unicodedata.normalize("NFKC", text)

    # Expand contractions (e.g., "I'm" -> "I am", "don't" -> "do not")
    text = contractions.fix(text)

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


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
            'confidence_scores': {cat: score for cat, score in results},
            'status': 'processed'
        }

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
        original_text = entry['text']
        cleaned_text = clean_text(original_text)
        
        # Get predictions
        result = classifier.predict_categories(cleaned_text, original_text)
        
        # If no categories were found, assign null
        if not result['categories']:
            result['categories'] = ['null']
        
        output_data.append(result)
        
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
    INPUT_FILE = "result.json"
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
        print("Loading model...")
        self.model = SentenceTransformer(model_path)
        self.threshold = threshold
        
        print("Loading category embeddings...")
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
            'confidence_scores': {cat: score for cat, score in results},
            'status': 'processed'
        }

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
        original_text = entry['text']
        cleaned_text = clean_text(original_text)
        
        # Get predictions
        result = classifier.predict_categories(cleaned_text, original_text)
        
        # If no categories were found, assign null
        if not result['categories']:
            result['categories'] = ['null']
        
        output_data.append(result)
        
        if i % 10 == 0:
            print(f"Processed {i}/{total_entries} entries...")
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessing complete. Results saved to {output_file}")

def main():
    # Configuration
    MODEL_PATH = "vectorModel"
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