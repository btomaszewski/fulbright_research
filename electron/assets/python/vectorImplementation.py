
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import spacy
import re
import os
import sys
from typing import List, Dict, Tuple

def get_spacy_model():
    """Get spaCy model with explicit path handling for PyInstaller."""
    import sys
    import os
    import logging
    import spacy
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("spacy_loader")
    
    # Check if we're running in a PyInstaller bundle
    if getattr(sys, 'frozen', False):
        logger.info("Running in PyInstaller bundled environment")
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        
        model_path = Path(base_dir) / "en_core_web_sm"
        logger.info(f"Looking for model at: {model_path}")
        
        # Debug info - list files in model directory
        if model_path.exists():
            logger.info(f"Model directory exists")
            files = list(model_path.glob('*'))
            logger.info(f"Files found: {[f.name for f in files]}")
            
            config_path = model_path / "config.cfg"
            if config_path.exists():
                logger.info(f"Config file exists: {os.path.getsize(config_path)} bytes")
                
                # Check if file is readable
                try:
                    with open(config_path, 'r') as f:
                        first_line = f.readline()
                    logger.info(f"Config file is readable, first line: {first_line[:30]}...")
                except Exception as e:
                    logger.error(f"Error reading config file: {e}")
            else:
                logger.error(f"Config file not found!")
        
        try:
            if model_path.exists():
                logger.info("Loading model from bundled path")
                logger.info(f"Using spaCy version: {spacy.__version__}")
                nlp = spacy.load(str(model_path))
                logger.info("Successfully loaded model")
                return nlp
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            logger.error(f"Error details: {type(e).__name__}")
        
        # If we reach here, fall back to a blank model
        logger.warning("Using blank English model as fallback")
        return spacy.blank("en")
    else:
        # For development environment
        try:
            return spacy.load("en_core_web_sm")
        except Exception:
            logger.warning("Using blank English model in development")
            return spacy.blank("en")
# Initialize NLP
nlp = get_spacy_model()

def clean_text(text: str) -> str:
    """Cleans text by lowercasing, removing special characters, lemmatizing, and removing stopwords."""
    if not text or not isinstance(text, str):
        return ""
        
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    try:
        doc = nlp(text)
        # Check if nlp is a blank model (fallback) or has full capabilities
        if hasattr(nlp, 'has_pipe') and nlp.has_pipe('lemmatizer'):
            cleaned_text = " ".join([token.lemma_ for token in doc if not token.is_stop])
        else:
            # Basic fallback without lemmatization or stopword removal
            cleaned_text = " ".join([token.text for token in doc])
    except Exception as e:
        print(f"Error in text cleaning: {e}")
        cleaned_text = text  # Fallback to just the preprocessed text
    
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
        # Handle PyInstaller frozen environment for model paths
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            model_path = os.path.join(base_dir, model_path)
            category_embeddings_path = os.path.join(base_dir, category_embeddings_path)
            
        print(f"Loading SentenceTransformer model from: {model_path}")
        self.model = SentenceTransformer(model_path)
        self.threshold = threshold
        
        print(f"Loading category embeddings from: {category_embeddings_path}")
        try:
            with open(category_embeddings_path, 'r') as f:
                self.category_embeddings = json.load(f)
                
            # Convert category embeddings to numpy arrays
            self.categories = list(self.category_embeddings.keys())
            self.category_vectors = np.array([self.category_embeddings[cat] for cat in self.categories])
            print(f"Loaded {len(self.categories)} categories")
        except FileNotFoundError:
            print(f"Category embeddings file not found at {category_embeddings_path}")
            print("Files in directory:", os.listdir(os.path.dirname(category_embeddings_path)))
            raise
    
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
        try:
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
        except Exception as e:
            print(f"Error in category prediction: {e}")
            return {
                'original_text': original_text,
                'cleaned_text': text,
                'categories': ['error'],
                'confidence_scores': {},
                'status': 'error',
                'error': str(e)
            }

def categorize(fullText):
    try:
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # Use _MEIPASS instead of executable path
            MODEL_PATH = os.path.join(base_dir, "vector_model_package/sentence_transformer")
            CATEGORY_EMBEDDINGS_PATH = os.path.join(base_dir, "vector_model_package/category_embeddings.json")
            
            # Verify model files exist
            print(f"Checking model paths:")
            print(f"  MODEL_PATH exists: {os.path.exists(MODEL_PATH)}")
            print(f"  CATEGORY_EMBEDDINGS_PATH exists: {os.path.exists(CATEGORY_EMBEDDINGS_PATH)}")
            
            # If they don't exist, fall back to default categories
            if not os.path.exists(MODEL_PATH) or not os.path.exists(CATEGORY_EMBEDDINGS_PATH):
                print("Model files not found, returning default categories")
                return {'categories': ['default']}
    
        # Initialize classifier
        print(f"Initializing VectorClassifier with model path: {MODEL_PATH}")
        classifier = VectorClassifier(
            model_path=MODEL_PATH,
            category_embeddings_path=CATEGORY_EMBEDDINGS_PATH,
            threshold=0.7
        )

        """Process input JSON and save categorized results."""
        print("Cleaning text...")
        cleaned_text = clean_text(fullText)
        
        # Get predictions
        print("Predicting categories...")
        result = classifier.predict_categories(cleaned_text, fullText)
        
        # If no categories were found, assign null
        if not result['categories']:
            result['categories'] = ['null']
        
        return result
    except Exception as e:
        print(f"Fatal error in categorize function: {e}")
        # Return in the expected format to ensure compatibility with the main script
        return {
            'original_text': fullText,
            'cleaned_text': clean_text(fullText) if callable(clean_text) else "",
            'categories': ['null'],  # Return 'null' instead of 'error' to match expected behavior
            'confidence_scores': {},
            'status': 'processed'  # Return 'processed' instead of 'error' to match expected behavior
        }
    
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