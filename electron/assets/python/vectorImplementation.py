import json
import numpy as np
from sentence_transformers import SentenceTransformer
import re
import os
import sys
from typing import List, Dict, Tuple
import logging

# Import our consistent text cleaning function
from cleanText import clean_text

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vector_classifier")

class VectorClassifier:
    def __init__(
        self, 
        model_path: str, 
        category_embeddings_path: str, 
        metadata_path: str = None,
        threshold: float = 0.6,  # Lower default threshold for multi-label
        multi_label: bool = True  # Default to multi-label mode
    ):
        """
        Initialize classifier with model and category embeddings.
        
        Args:
            model_path: Path to the trained model
            category_embeddings_path: Path to saved category embeddings
            metadata_path: Path to model metadata
            threshold: Minimum similarity score to assign a category
            multi_label: Whether to allow multiple categories per text
        """
        # Handle PyInstaller frozen environment for model paths
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            model_path = os.path.join(base_dir, model_path)
            category_embeddings_path = os.path.join(base_dir, category_embeddings_path)
            if metadata_path:
                metadata_path = os.path.join(base_dir, metadata_path)
            
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
    
    def evaluate_on_texts(self, texts_with_labels: List[Dict]) -> Dict:
        """
        Evaluate the classifier on a set of texts with known labels.
        
        Args:
            texts_with_labels: List of dicts with 'text' and 'label' keys
            
        Returns:
            Dict with precision, recall, f1, and per-category metrics
        """
        if not texts_with_labels:
            return {"error": "No evaluation data provided"}
            
        total_true_positives = 0
        total_false_positives = 0
        total_false_negatives = 0
        
        # Per-category metrics
        category_metrics = {cat: {"tp": 0, "fp": 0, "fn": 0} for cat in self.categories}
        
        # Hierarchy-specific metrics
        parent_metrics = {"tp": 0, "fp": 0, "fn": 0}
        child_metrics = {"tp": 0, "fp": 0, "fn": 0}
        
        for item in texts_with_labels:
            text = item['text']
            
            # Add parent categories to true labels if not already present
            true_labels = set(item['label'])
            parent_labels = set()
            for label in true_labels:
                if label in self.child_to_parent:
                    parent_labels.add(self.child_to_parent[label])
            true_labels.update(parent_labels)
            
            # Clean text
            cleaned_text = clean_text(text)
            
            # Get predictions
            result = self.predict_categories(cleaned_text, text)
            predicted_labels = set(result['categories'])
            
            # Count true positives, false positives, false negatives
            for cat in self.categories:
                if cat in true_labels and cat in predicted_labels:
                    total_true_positives += 1
                    category_metrics[cat]["tp"] += 1
                    
                    # Add to parent/child specific metrics
                    if cat in self.category_hierarchy:  # It's a parent
                        parent_metrics["tp"] += 1
                    elif cat in self.child_to_parent:  # It's a child
                        child_metrics["tp"] += 1
                    
                elif cat not in true_labels and cat in predicted_labels:
                    total_false_positives += 1
                    category_metrics[cat]["fp"] += 1
                    
                    # Add to parent/child specific metrics
                    if cat in self.category_hierarchy:  # It's a parent
                        parent_metrics["fp"] += 1
                    elif cat in self.child_to_parent:  # It's a child
                        child_metrics["fp"] += 1
                    
                elif cat in true_labels and cat not in predicted_labels:
                    total_false_negatives += 1
                    category_metrics[cat]["fn"] += 1
                    
                    # Add to parent/child specific metrics
                    if cat in self.category_hierarchy:  # It's a parent
                        parent_metrics["fn"] += 1
                    elif cat in self.child_to_parent:  # It's a child
                        child_metrics["fn"] += 1
        
        # Calculate overall metrics
        precision = total_true_positives / max(total_true_positives + total_false_positives, 1)
        recall = total_true_positives / max(total_true_positives + total_false_negatives, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-10)
        
        # Calculate parent category metrics
        parent_precision = parent_metrics["tp"] / max(parent_metrics["tp"] + parent_metrics["fp"], 1)
        parent_recall = parent_metrics["tp"] / max(parent_metrics["tp"] + parent_metrics["fn"], 1)
        parent_f1 = 2 * parent_precision * parent_recall / max(parent_precision + parent_recall, 1e-10)
        
        # Calculate child category metrics
        child_precision = child_metrics["tp"] / max(child_metrics["tp"] + child_metrics["fp"], 1)
        child_recall = child_metrics["tp"] / max(child_metrics["tp"] + child_metrics["fn"], 1)
        child_f1 = 2 * child_precision * child_recall / max(child_precision + child_recall, 1e-10)
        
        # Calculate per-category metrics
        for cat in category_metrics:
            tp = category_metrics[cat]["tp"]
            fp = category_metrics[cat]["fp"]
            fn = category_metrics[cat]["fn"]
            
            cat_precision = tp / max(tp + fp, 1)
            cat_recall = tp / max(tp + fn, 1)
            cat_f1 = 2 * cat_precision * cat_recall / max(cat_precision + cat_recall, 1e-10)
            
            category_metrics[cat]["precision"] = cat_precision
            category_metrics[cat]["recall"] = cat_recall
            category_metrics[cat]["f1"] = cat_f1
        
        return {
            "overall": {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "true_positives": total_true_positives,
                "false_positives": total_false_positives,
                "false_negatives": total_false_negatives
            },
            "parent_categories": {
                "precision": parent_precision,
                "recall": parent_recall,
                "f1": parent_f1,
                "true_positives": parent_metrics["tp"],
                "false_positives": parent_metrics["fp"],
                "false_negatives": parent_metrics["fn"]
            },
            "child_categories": {
                "precision": child_precision,
                "recall": child_recall,
                "f1": child_f1,
                "true_positives": child_metrics["tp"],
                "false_positives": child_metrics["fp"],
                "false_negatives": child_metrics["fn"]
            },
            "per_category": category_metrics
        }