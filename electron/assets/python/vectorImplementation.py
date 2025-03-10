import json
import numpy as np
from sentence_transformers import SentenceTransformer
import re
import os
import sys
import tarfile
import tempfile
import shutil
import logging
import contractions 
import unicodedata 
from typing import List, Dict, Tuple, Union, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vector_classifier.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("vector_classifier")

# =====================================================================
# CONFIGURATION - MODIFY THESE PATHS TO MATCH YOUR ENVIRONMENT
# =====================================================================

# Path to the SentenceTransformer model
MODEL_PATH = "../vector_model_package/sentence_transformer"

# Path to the category embeddings JSON file
CATEGORY_EMBEDDINGS_PATH = "../vector_model_package/category_embeddings.json"

# Path to model metadata (optional)
METADATA_PATH = "../vector_model_package/metadata.json"

# Classification threshold (0.0 to 1.0)
THRESHOLD = 0.6

# Enable multi-label classification (True/False)
MULTI_LABEL = True

# =====================================================================
# TEXT CLEANING FUNCTION
# =====================================================================

def clean_text(text: str) -> str:
    """
    Clean and normalize text for classification.
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text
    """
    if not text or not isinstance(text, str):
        return ""
        
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)

        # Normalize Unicode characters (fix encoding issues)
    text = unicodedata.normalize("NFKC", text)

    # Expand contractions (e.g., "I'm" -> "I am", "don't" -> "do not")
    text = contractions.fix(text)

    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# =====================================================================
# VECTOR CLASSIFIER CLASS
# =====================================================================

class VectorClassifier:
    def __init__(
        self, 
        model_path: str, 
        category_embeddings_path: str, 
        metadata_path: str = None,
        threshold: float = 0.6,
        multi_label: bool = True
    ):
        """
        Initialize classifier with model and category embeddings.
        
        Args:
            model_path: Path to the trained model or compressed model archive
            category_embeddings_path: Path to saved category embeddings
            metadata_path: Path to model metadata
            threshold: Minimum similarity score to assign a category
            multi_label: Whether to allow multiple categories per text
        """
        # Handle PyInstaller frozen environment for model paths
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            model_path = self.resolve_path(model_path)
            category_embeddings_path = self.resolve_path(category_embeddings_path)
            if metadata_path:
                metadata_path = self.resolve_path(metadata_path)
            
        # Check if model is compressed
        self.temp_dir = None
        if model_path.endswith('.tar.gz') or model_path.endswith('.tgz'):
            logger.info(f"Decompressing model from: {model_path}")
            # Create temp directory for the decompressed model
            self.temp_dir = tempfile.mkdtemp(prefix="vector_model_")
            
            try:
                # Decompress the model
                with tarfile.open(model_path, "r:gz") as tar:
                    tar.extractall(path=self.temp_dir)
                
                # Find the model directory in the decompressed files
                # Typically it's the sentence_transformer directory
                model_dirs = [d for d in os.listdir(self.temp_dir) 
                             if os.path.isdir(os.path.join(self.temp_dir, d))]
                
                if 'sentence_transformer' in model_dirs:
                    # Direct match
                    model_path = os.path.join(self.temp_dir, 'sentence_transformer')
                elif model_dirs:
                    # Take the first directory
                    model_path = os.path.join(self.temp_dir, model_dirs[0])
                else:
                    # Use the temp dir itself
                    model_path = self.temp_dir
                    
                logger.info(f"Decompressed model to: {model_path}")
            except Exception as e:
                logger.error(f"Error decompressing model: {str(e)}")
                # Clean up the temp directory if decompression fails
                if self.temp_dir and os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir)
                    self.temp_dir = None
                raise
        
        logger.info(f"Loading SentenceTransformer model from: {model_path}")
        self.model = SentenceTransformer(model_path)
        self.threshold = threshold
        self.multi_label = multi_label
        
        # Initialize hierarchy containers
        self.category_hierarchy = {}
        self.child_to_parent = {}
        
        # Load metadata if available
        if metadata_path and os.path.exists(metadata_path):
            logger.info(f"Loading model metadata from: {metadata_path}")
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                # Set multi-label mode from metadata if available
                if 'multi_label' in metadata:
                    self.multi_label = metadata['multi_label']
                    logger.info(f"Using multi_label={self.multi_label} from metadata")
                
                # Load hierarchy information
                if 'category_hierarchy' in metadata:
                    self.category_hierarchy = metadata['category_hierarchy']
                    logger.info(f"Loaded hierarchy with {len(self.category_hierarchy)} parent categories")
                    
                    # If child_to_parent is provided in metadata, use it
                    if 'child_to_parent' in metadata:
                        self.child_to_parent = metadata['child_to_parent']
                    else:
                        # Otherwise build it from category_hierarchy
                        for parent, children in self.category_hierarchy.items():
                            for child in children:
                                self.child_to_parent[child] = parent
                    
                    logger.info(f"Loaded {len(self.child_to_parent)} child-to-parent mappings")
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        else:
            logger.info(f"No metadata file found or specified, using default settings")
        
        logger.info(f"Loading category embeddings from: {category_embeddings_path}")
        try:
            with open(category_embeddings_path, 'r') as f:
                self.category_embeddings = json.load(f)
                
            # Convert category embeddings to numpy arrays
            self.categories = list(self.category_embeddings.keys())
            self.category_vectors = np.array([self.category_embeddings[cat] for cat in self.categories])
            logger.info(f"Loaded {len(self.categories)} categories")
        except FileNotFoundError:
            logger.error(f"Category embeddings file not found at {category_embeddings_path}")
            logger.error(f"Files in directory: {os.listdir(os.path.dirname(category_embeddings_path))}")
            raise
    
    def __del__(self):
        """Clean up temporary files when the classifier is destroyed."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {str(e)}")
    
    @staticmethod
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
                
                # Also check in the _MEIPASS directory (PyInstaller's temp directory)
                if hasattr(sys, '_MEIPASS'):
                    meipass_relative_path = os.path.join(sys._MEIPASS, path)
                    if os.path.exists(meipass_relative_path):
                        return meipass_relative_path
                    
                    # Also try removing the first directory component
                    if '/' in path or '\\' in path:
                        parts = re.split(r'[/\\]', path, 1)
                        if len(parts) > 1:
                            simpler_path = parts[1]
                            meipass_simpler_path = os.path.join(sys._MEIPASS, simpler_path)
                            if os.path.exists(meipass_simpler_path):
                                return meipass_simpler_path
                
        return path  # Return original path if nothing else works
    
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
            
            # Calculate cosine similarities with all category embeddings
            # Proper normalization for cosine similarity
            text_norm = np.linalg.norm(text_embedding)
            if text_norm == 0:
                logger.warning("Text embedding has zero norm, cannot calculate similarities")
                return {
                    'original_text': original_text,
                    'cleaned_text': text,
                    'categories': ['null'],
                    'confidence_scores': {},
                    'status': 'error',
                    'error': 'Zero embedding vector'
                }
                
            text_embedding_normalized = text_embedding / text_norm
            category_norms = np.linalg.norm(self.category_vectors, axis=1)
            category_vectors_normalized = self.category_vectors / category_norms[:, np.newaxis]
            similarities = np.dot(category_vectors_normalized, text_embedding_normalized)
            
            # Get categories above threshold
            results = []
            max_score = 0
            max_category_idx = -1
            
            for i, (cat, score) in enumerate(zip(self.categories, similarities)):
                if score > max_score:
                    max_score = score
                    max_category_idx = i
                    
                if score >= self.threshold:
                    results.append((cat, float(score)))
            
            # If no categories above threshold but we have valid scores
            if not results and max_score > 0:
                # Check if the max score is close to threshold
                if max_score > (self.threshold * 0.8):  # Within 80% of threshold
                    # Return best match but mark as low confidence
                    best_cat = self.categories[max_category_idx]
                    return {
                        'original_text': original_text,
                        'cleaned_text': text,
                        'categories': [best_cat],
                        'confidence_scores': {best_cat: float(max_score)},
                        'status': 'low_confidence'
                    }
                else:
                    # No good match at all
                    return {
                        'original_text': original_text,
                        'cleaned_text': text,
                        'categories': ['no_category'],
                        'confidence_scores': {},
                        'status': 'no_match'
                    }
            
            # Sort by similarity score
            results = sorted(results, key=lambda x: x[1], reverse=True)
            
            # If not multi-label, only return the top category if it's above threshold
            if not self.multi_label and results:
                results = [results[0]]
            
            # Process results to handle hierarchy
            processed_results = self._process_hierarchical_results(results)
            
            # Extract categories and scores
            categories = [cat for cat, _ in processed_results]
            confidence_scores = {cat: score for cat, score in processed_results}
            
            # Create hierarchy info for results
            hierarchy_info = self._create_hierarchy_info(categories)
            
            return {
                'original_text': original_text,
                'cleaned_text': text,
                'categories': categories,
                'confidence_scores': confidence_scores,
                'hierarchy_info': hierarchy_info,
                'status': 'processed'
            }
        except Exception as e:
            logger.error(f"Error in category prediction: {str(e)}")
            return {
                'original_text': original_text,
                'cleaned_text': text,
                'categories': ['error'],
                'confidence_scores': {},
                'status': 'error',
                'error': str(e)
            }
    
    def _process_hierarchical_results(self, results: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """
        Process results to include parent categories when child categories are detected.
        
        Args:
            results: List of (category, score) tuples
            
        Returns:
            Processed list of (category, score) tuples with parent categories added
        """
        processed_results = []
        seen_categories = set()
        
        # First pass: add all direct matches
        for cat, score in results:
            if cat not in seen_categories:
                processed_results.append((cat, score))
                seen_categories.add(cat)
        
        # Second pass: add parent categories for any children that were detected
        for cat, score in results:
            if cat in self.child_to_parent:
                parent = self.child_to_parent[cat]
                if parent not in seen_categories:
                    # Add parent with the same score as the highest scoring child
                    processed_results.append((parent, score))
                    seen_categories.add(parent)
        
        # Sort processed results by score
        return sorted(processed_results, key=lambda x: x[1], reverse=True)
    
    
    def _create_hierarchy_info(self, categories: List[str]) -> Dict:
        """
        Create hierarchy information for the predicted categories.
        
        Args:
            categories: List of predicted category names
            
        Returns:
            Dictionary with hierarchy information for each category
        """
        hierarchy_info = {}
        
        for cat in categories:
            if cat in self.category_hierarchy:
                # It's a parent category
                children = self.category_hierarchy[cat]
                # Only include children that are in the prediction results
                detected_children = [c for c in children if c in categories]
                hierarchy_info[cat] = {
                    "type": "parent",
                    "children": children,
                    "detected_children": detected_children
                }
            elif cat in self.child_to_parent:
                # It's a child category
                parent = self.child_to_parent[cat]
                hierarchy_info[cat] = {
                    "type": "child",
                    "parent": parent
                }
            else:
                # It's a standalone category (neither parent nor child)
                hierarchy_info[cat] = {
                    "type": "standalone"
                }
        
        return hierarchy_info

# =====================================================================
# MAIN CATEGORIZATION FUNCTION
# =====================================================================

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

# Global variable to store the classifier instance (initialize on first use)
_classifier = None

def get_classifier():
    """Get or initialize the classifier instance."""
    global _classifier
    if _classifier is None:
        # Resolve paths
        model_path = resolve_path(MODEL_PATH)
        category_embeddings_path = resolve_path(CATEGORY_EMBEDDINGS_PATH)
        metadata_path = resolve_path(METADATA_PATH) if METADATA_PATH else None
        
        logger.info(f"Using model path: {model_path}")
        logger.info(f"Using category embeddings path: {category_embeddings_path}")
        if metadata_path:
            logger.info(f"Using metadata path: {metadata_path}")
        
        # Initialize the classifier
        try:
            _classifier = VectorClassifier(
                model_path=model_path,
                category_embeddings_path=category_embeddings_path,
                metadata_path=metadata_path,
                threshold=THRESHOLD,
                multi_label=MULTI_LABEL
            )
            logger.info(f"Initialized classifier with threshold={THRESHOLD}, multi_label={MULTI_LABEL}")
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            raise
    
    return _classifier

def categorize(text):
    """
    Main function to categorize text, returning a format compatible with the Google Sheets uploader.
    
    Args:
        text: Text to categorize
        
    Returns:
        List containing one item with classification results in Google Sheets compatible format
    """
    logger.info(f"Categorizing text: {text[:50]}...")
    
    try:
        # Get or initialize classifier
        classifier = get_classifier()
        
        # Clean the text
        original_text = text
        cleaned_text = clean_text(original_text)
        
        # Get classification result
        classification_result = classifier.predict_categories(cleaned_text, original_text)
        
        # Format the result for Google Sheets compatibility
        # We'll create a structure that matches what the Google Sheets uploader expects
        confidence_scores = classification_result.get("confidence_scores", {})
        categories = classification_result.get("categories", [])
        
        # Create return object in format expected by main.py
        result = [{
            "classification": {
                # This format matches what the Google Sheets uploader expects
                "confidence_scores": confidence_scores
            }
        }]
        
        # Optional: Add formatted output that matches Google Sheets expected format directly
        if categories and confidence_scores:
            # Sort categories by confidence score (descending)
            sorted_categories = sorted(
                [(cat, score) for cat, score in confidence_scores.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Create the result object in the format expected by Google Sheets uploader
            result[0]["classification"]["categories"] = categories
            
            # This exactly matches the format used in the Google Sheets uploader
            # See the uploadToGoogleSheets function in your JS code
            result[0]["classification"]["formatted_output"] = {
                "categories": ";".join([cat for cat, _ in sorted_categories]), 
                "confidence_scores": ";".join([f"{cat}: {score:.2f}" for cat, score in sorted_categories])
            }
            
            # Hierarchy data is commented out as requested, but available
            """
            if "hierarchy_info" in classification_result:
                result[0]["classification"]["hierarchy_info"] = classification_result["hierarchy_info"]
            """
        
        logger.info(f"Categorization complete. Found categories: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in categorize function: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [{"classification": {"error": str(e)}}]

# For testing
if __name__ == "__main__":
    # Test the categorization function
    test_text = "This is a test message to categorize."
    result = categorize(test_text)
    print(json.dumps(result, indent=2))
    
