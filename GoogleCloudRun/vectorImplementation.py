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
import time 

# Set up logging - Use Cloud Run friendly configuration (output to stdout/stderr)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Cloud Run logs are captured from stdout/stderr
    ]
)
logger = logging.getLogger("vector_classifier")

# =====================================================================
# CONFIGURATION - Use environment variables for Cloud Run compatibility
# =====================================================================

# Root directory for the model package - customizable via environment variable
MODEL_ROOT = os.environ.get("VECTOR_MODEL_PATH", "/app/models/vector_model_package")

# Derived paths for model components
SENTENCE_TRANSFORMER_PATH = os.path.join(MODEL_ROOT, "sentence_transformer")
CATEGORY_EMBEDDINGS_PATH = os.path.join(MODEL_ROOT, "category_embeddings.json")
METADATA_PATH = os.path.join(MODEL_ROOT, "metadata.json")

# Allow configuring these via environment variables too
THRESHOLD = float(os.environ.get("VECTOR_THRESHOLD", "0.6"))
MULTI_LABEL = os.environ.get("VECTOR_MULTI_LABEL", "True").lower() == "true"

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
            model_path: Path to the trained model directory
            category_embeddings_path: Path to saved category embeddings
            metadata_path: Path to model metadata
            threshold: Minimum similarity score to assign a category
            multi_label: Whether to allow multiple categories per text
        """
        self.temp_dir = None
        self.threshold = threshold
        self.multi_label = multi_label
        
        # Initialize hierarchy containers
        self.category_hierarchy = {}
        self.child_to_parent = {}
        
        # Log model paths for debugging
        logger.info(f"Model path: {model_path}")
        logger.info(f"Category embeddings path: {category_embeddings_path}")
        if metadata_path:
            logger.info(f"Metadata path: {metadata_path}")
        
        # Check if model directory exists
        if not os.path.exists(model_path):
            logger.error(f"Model path does not exist: {model_path}")
            parent_dir = os.path.dirname(model_path)
            if os.path.exists(parent_dir):
                logger.info(f"Contents of parent directory: {os.listdir(parent_dir)}")
        else:
            # List model directory contents
            if os.path.isdir(model_path):
                logger.info(f"Model directory contents: {os.listdir(model_path)}")
        
        # Check if category embeddings file exists
        if not os.path.exists(category_embeddings_path):
            logger.error(f"Category embeddings file does not exist: {category_embeddings_path}")
            parent_dir = os.path.dirname(category_embeddings_path)
            if os.path.exists(parent_dir):
                logger.info(f"Contents of parent directory: {os.listdir(parent_dir)}")
        
        # Try to load the model
        try:
            logger.info(f"Loading SentenceTransformer model from: {model_path}")
            self.model = SentenceTransformer(model_path)
            logger.info("Successfully loaded SentenceTransformer model")
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {str(e)}")
            raise
        
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
                # Non-critical error, continue without metadata
        else:
            logger.info(f"No metadata file found or specified, using default settings")
        
        # Load category embeddings
        try:
            logger.info(f"Loading category embeddings from: {category_embeddings_path}")
            with open(category_embeddings_path, 'r') as f:
                self.category_embeddings = json.load(f)
                
            # Convert category embeddings to numpy arrays
            self.categories = list(self.category_embeddings.keys())
            self.category_vectors = np.array([self.category_embeddings[cat] for cat in self.categories])
            logger.info(f"Loaded {len(self.categories)} categories")
        except Exception as e:
            logger.error(f"Error loading category embeddings: {str(e)}")
            raise
    
    def __del__(self):
        """Clean up temporary files when the classifier is destroyed."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {str(e)}")
    
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
            
            # Collect all categories and their similarities
            all_similarities = [(self.categories[i], float(score)) for i, score in enumerate(similarities)]
            
            # Sort all categories by similarity score (descending)
            all_similarities = sorted(all_similarities, key=lambda x: x[1], reverse=True)
            
            # Use a lower threshold for child categories to improve their detection
            child_threshold = self.threshold * 0.5 # 10% lower threshold for child categories
            
            # Keep track of categories above threshold
            results = []
            for cat, score in all_similarities:
                # Use regular threshold for parent categories
                if cat in self.category_hierarchy and score >= self.threshold:
                    results.append((cat, score))
                # Use lower threshold for child categories
                elif cat in self.child_to_parent and score >= child_threshold:
                    results.append((cat, score))
                # Use regular threshold for standalone categories
                elif score >= self.threshold:
                    results.append((cat, score))
            
            # If no categories above threshold but we have valid scores
            if not results and len(all_similarities) > 0:
                # Get the best match
                best_cat, max_score = all_similarities[0]
                
                # Check if the max score is close to threshold
                if max_score > (self.threshold * 0.8):  # Within 80% of threshold
                    # Check if it's a child category that's close to the child threshold
                    if best_cat in self.child_to_parent and max_score > (child_threshold * 0.5):
                        return {
                            'original_text': original_text,
                            'cleaned_text': text,
                            'categories': [best_cat],
                            'confidence_scores': {best_cat: float(max_score)},
                            'status': 'low_confidence_child'  # Mark as low confidence child
                        }
                    else:
                        # Return best match but mark as low confidence
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
            
            # If not multi-label, only return the top category if it's above threshold
            if not self.multi_label and results:
                results = [results[0]]
            
            # Process results to handle hierarchy (add missing parent categories)
            processed_results = self._process_hierarchical_results(results)
            
            # Extract categories and scores
            categories = [cat for cat, _ in processed_results]
            confidence_scores = {cat: score for cat, score in processed_results}
            
            # Create hierarchy info for results
            hierarchy_info = self._create_hierarchy_info(categories)
            
            # Explicitly identify the top child category for the output
            top_child_category = None
            top_child_score = 0
            
            # Look for child categories in original results (before processing hierarchical results)
            # This helps ensure we find the actual top child, not one that was added for hierarchical consistency
            for cat, score in results:
                if cat in self.child_to_parent and score > top_child_score:
                    top_child_category = cat
                    top_child_score = score
            
            # If we didn't find any child categories in results, check all_similarities
            if top_child_category is None:
                for cat, score in all_similarities:
                    if cat in self.child_to_parent and score > top_child_score:
                        # Only add if it's reasonably close to the threshold
                        if score >= child_threshold * 0.5:
                            top_child_category = cat
                            top_child_score = score
            
            result = {
                'original_text': original_text,
                'cleaned_text': text,
                'categories': categories,
                'confidence_scores': confidence_scores,
                'hierarchy_info': hierarchy_info,
                'status': 'processed'
            }
            
            # Add top child category if found
            if top_child_category:
                result['top_child_category'] = top_child_category
                result['top_child_score'] = top_child_score
            
            return result
            
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

def find_model_path(root_path):
    """
    Find the sentence transformer model path, looking for directory structure
    with safetensors as the weights file.
    
    Args:
        root_path: Root directory to search in
        
    Returns:
        Path to the model directory
    """
    # First, check standard path
    sentence_transformer_path = os.path.join(root_path, "sentence_transformer")
    
    if os.path.isdir(sentence_transformer_path):
        # List all files to debug
        logger.info(f"Files in {sentence_transformer_path}: {os.listdir(sentence_transformer_path)}")
        
        # Check for safetensors
        if os.path.exists(os.path.join(sentence_transformer_path, "model.safetensors")):
            logger.info(f"Found model.safetensors at expected location")
            return sentence_transformer_path
    
    # If we're here, we need to look in deeper or make assumptions
    sentence_transformer_path = os.path.join(root_path, "sentence_transformer")
    
    if os.path.isdir(sentence_transformer_path):
        # First, check if model.safetensors exists as a direct file
        if os.path.exists(os.path.join(sentence_transformer_path, "model.safetensors")):
            logger.info(f"Found model with safetensors at: {sentence_transformer_path}")
            return sentence_transformer_path
        
        # Check if required configuration files exist
        config_files = ['config.json', 'tokenizer_config.json']
        found_configs = all(os.path.exists(os.path.join(sentence_transformer_path, f)) for f in config_files)
        
        if found_configs:
            logger.info(f"Found model with config files at: {sentence_transformer_path}")
            return sentence_transformer_path
    
    # If we didn't find a standard structure, we'll have to be adaptive
    # Look for directories that might contain model.safetensors
    logger.info(f"Searching for model.safetensors in subdirectories of {root_path}")
    
    for root, dirs, files in os.walk(root_path):
        if "model.safetensors" in files:
            logger.info(f"Found model.safetensors in: {root}")
            return root
    
    # If we're here, we've searched everywhere without success
    # Just return the standard path and hope for the best
    logger.warning(f"Could not locate model.safetensors, using standard path: {sentence_transformer_path}")
    return sentence_transformer_path

# Global variable to store the classifier instance (initialize on first use)
_classifier = None

def ensure_model_compatibility(model_dir):
    safetensors_path = os.path.join(model_dir, "model.safetensors")
    if os.path.exists(safetensors_path) and not os.path.exists(os.path.join(model_dir, "pytorch_model.bin")):
        # Create symlink or copy - symlink might not work in all environments
        shutil.copy(safetensors_path, os.path.join(model_dir, "pytorch_model.bin"))
        logger.info("Created compatible model file from safetensors")

def get_classifier():
    """Get or initialize the classifier instance."""
    global _classifier
    if _classifier is None:
        try:
            start_time = time.time()
            logger.info(f"Starting to load model at {start_time}")
            # Log environment variables for debugging in Cloud Run
            logger.info(f"Environment variables:")
            logger.info(f"  VECTOR_MODEL_PATH: {os.environ.get('VECTOR_MODEL_PATH', 'Not set')}")
            logger.info(f"  MODEL_ROOT: {MODEL_ROOT}")
            
            # List model root directory if it exists
            if os.path.exists(MODEL_ROOT):
                logger.info(f"Contents of MODEL_ROOT: {os.listdir(MODEL_ROOT)}")
                
                # Find model directory looking for safetensors
                model_path = find_model_path(MODEL_ROOT)
                
                # Ensure model compatibility - add this line
                ensure_model_compatibility(model_path)
                
                # Get category embeddings and metadata paths
                category_embeddings_path = os.path.join(MODEL_ROOT, "category_embeddings.json")
                metadata_path = os.path.join(MODEL_ROOT, "metadata.json")
                
                # Verify paths
                logger.info(f"Using model path: {model_path}")
                logger.info(f"Using category embeddings path: {category_embeddings_path}")
                if os.path.exists(metadata_path):
                    logger.info(f"Using metadata path: {metadata_path}")
                else:
                    logger.warning(f"Metadata file not found at: {metadata_path}")
                
                # Initialize the classifier
                _classifier = VectorClassifier(
                    model_path=model_path,
                    category_embeddings_path=category_embeddings_path,
                    metadata_path=metadata_path,
                    threshold=THRESHOLD,
                    multi_label=MULTI_LABEL
                )
                logger.info(f"Initialized classifier with threshold={THRESHOLD}, multi_label={MULTI_LABEL}")
            else:
                logger.error(f"MODEL_ROOT does not exist: {MODEL_ROOT}")
                # Try alternative paths
                alternative_paths = [
                    "/app/models/vector_model_package",
                    os.path.join(os.getcwd(), "models/vector_model_package"),
                    os.path.dirname(os.path.abspath(__file__))
                ]
                
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        logger.info(f"Found alternative path: {alt_path}")
                        model_path = find_model_path(alt_path)
                        # Add model compatibility check here too
                        ensure_model_compatibility(model_path)
                        category_embeddings_path = os.path.join(alt_path, "category_embeddings.json")
                        metadata_path = os.path.join(alt_path, "metadata.json")
                        
                        # Initialize classifier with alternative paths
                        _classifier = VectorClassifier(
                            model_path=model_path,
                            category_embeddings_path=category_embeddings_path,
                            metadata_path=metadata_path,
                            threshold=THRESHOLD,
                            multi_label=MULTI_LABEL
                        )
                        logger.info(f"Initialized classifier with alternative paths")
                        break
                
                if _classifier is None:
                    raise FileNotFoundError(f"Could not find model files in any expected location")
            
            end_time = time.time()  # Fix indentation - this should be outside the else block
            logger.info(f"Model loading completed in {end_time - start_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR: Failed to initialize classifier: {e}")
            logger.error(f"Error loading model: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    return _classifier  # Make sure this return statement is present

def categorize(text):
    """
    Main function to categorize text with separate parent and child categories.
    
    Args:
        text: Text to categorize
        
    Returns:
        List containing one item with classification results in the desired format
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
        
        # Format the result
        confidence_scores = classification_result.get("confidence_scores", {})
        categories = classification_result.get("categories", [])
        hierarchy_info = classification_result.get("hierarchy_info", {})
        
        # Get top child category from result
        top_child_category = classification_result.get("top_child_category", None)
        top_child_score = classification_result.get("top_child_score", 0)
        
        # Find parent category (assume first category that's a parent)
        parent_category = None
        parent_score = 0
        
        for cat in categories:
            if cat in classifier.category_hierarchy:  # If it's a parent category
                parent_category = cat
                parent_score = confidence_scores.get(cat, 0)
                break
        
        # Make sure to format scores as strings with 2 decimal places
        parent_score_str = f"{parent_score:.2f}" if parent_score else ""
        child_score_str = f"{top_child_score:.2f}" if top_child_score else ""
        
        # Create return object with the new desired structure
        result = [{
            "classification": {
                "parent_category": parent_category or "",
                "parent_confidence_score": parent_score_str,
                "child_category": top_child_category or "",
                "child_confidence_score": child_score_str,
                "all_confidence_scores": confidence_scores,
                "all_categories": categories
            }
        }]
        
        logger.info(f"Categorization complete. Parent: {parent_category}, Child: {top_child_category}")
        return result
        
    except Exception as e:
        logger.error(f"Error in categorize function: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Return a properly structured fallback response
        return [{
            "classification": {
                "parent_category": "Error",
                "parent_confidence_score": "",
                "child_category": "",
                "child_confidence_score": "",
                "error": str(e)
            }
        }]
        
        # Also include the full data for backward compatibility
        result[0]["classification"]["all_confidence_scores"] = confidence_scores
        result[0]["classification"]["all_categories"] = categories
        
        logger.info(f"Categorization complete. Parent: {parent_category}, Child: {top_child_category}")
        return result
        
    except Exception as e:
        logger.error(f"Error in categorize function: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return [{"classification": {"error": str(e)}}]

# For testing
if __name__ == "__main__":
    # Test the categorization function
    test_text = "This is a test message to categorize."
    result = categorize(test_text)
    print(json.dumps(result, indent=2)) 