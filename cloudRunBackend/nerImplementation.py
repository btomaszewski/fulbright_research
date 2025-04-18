import time
import json
import warnings
from pathlib import Path
import sys
import re
import os
from geopy.geocoders import Nominatim
import spacy
from spacy.tokens import Span
from spacy.language import Language
import tarfile
import tempfile
import shutil
import atexit
import logging
from typing import List, Dict, Any, Tuple, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ner_implementation')

warnings.filterwarnings("ignore", message="torch.utils._pytree._register_pytree_node is deprecated")

# Global variables
nlp = None  # Single best model
english_nlp = None
temp_dir = None
geolocator = None

def init_temp_dir():
    """Initialize a temporary directory that will be cleaned up on exit"""
    global temp_dir
    temp_dir = tempfile.mkdtemp(prefix="ner_model_")
    logger.info(f"Created temporary directory: {temp_dir}")
    
    # Register cleanup function
    atexit.register(cleanup_temp_dir)
    
    return temp_dir

def cleanup_temp_dir():
    """Clean up temporary directory on exit"""
    global temp_dir
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory: {e}")

def get_model_path():
    """Get the path to the best NER model, handling Cloud Run environment"""
    # Check environment variable first (for Cloud Run)
    env_path = os.environ.get("NER_MODEL_PATH")
    if env_path and os.path.exists(env_path):
        logger.info(f"Using NER model path from environment variable: {env_path}")
        return env_path
        
    # Fallback to relative path
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Check for best_model first
    best_model_path = os.path.join(base_path, "models/ner_model_package")
    if os.path.exists(best_model_path):
        logger.info(f"Using best model path: {best_model_path}")
        return best_model_path
        

def load_ner_model():
    """Load the NER model, handling Cloud Run environment"""
    global temp_dir
    
    # Initialize temp directory if needed
    if not temp_dir:
        init_temp_dir()
    
    # Get the model path
    model_package_path = get_model_path()
    logger.info(f"Looking for NER model at: {model_package_path}")
    
    # Check if model directory exists
    if not os.path.exists(model_package_path):
        raise FileNotFoundError(f"NER model package directory not found at: {model_package_path}")
    
    # Log directory contents for debugging
    logger.info(f"Contents of model directory: {os.listdir(model_package_path)}")
    
    # First try: Look for meta.json in the model directory (uncompressed model)
    meta_json_path = os.path.join(model_package_path, "meta.json")
    if os.path.exists(meta_json_path):
        logger.info(f"Found meta.json at {meta_json_path}, trying to load directly...")
        try:
            nlp = spacy.load(model_package_path)
            logger.info(f"Successfully loaded NER model directly from: {model_package_path}")
            return nlp
        except Exception as e:
            logger.warning(f"Error loading model directly from package: {e}")
            # Continue to try compressed model
    
    # Second try: Look for compressed model
    compressed_model_path = os.path.join(model_package_path, "ner_model.tar.gz")
    if os.path.exists(compressed_model_path):
        logger.info(f"Found compressed model at {compressed_model_path}, extracting...")
        
        # Create a clean extraction directory
        extract_path = os.path.join(temp_dir, "ner_model")
        os.makedirs(extract_path, exist_ok=True)
        
        # Extract the tar file
        with tarfile.open(compressed_model_path) as tar:
            # List contents before extraction
            members = [m.name for m in tar.getmembers()]
            logger.info(f"Contents of tar file: {members}")
            
            # Extract all files
            tar.extractall(path=extract_path)
        
        # Log the extracted contents
        logger.info(f"Extracted files to: {extract_path}")
        logger.info(f"Contents of extract directory: {os.listdir(extract_path)}")
        
        # Try to load the model
        logger.info(f"Attempting to load model from: {extract_path}")
        try:
            nlp = spacy.load(extract_path)
            logger.info(f"Successfully loaded NER model from: {extract_path}")
            return nlp
        except Exception as e:
            logger.error(f"Failed to load model from {extract_path}: {e}")
            
            # Try a more comprehensive search if direct loading fails
            try:
                # Check if meta.json is in the root or in a subdirectory
                if os.path.exists(os.path.join(extract_path, "meta.json")):
                    model_path = extract_path
                elif os.path.exists(os.path.join(extract_path, "ner", "meta.json")):
                    model_path = os.path.join(extract_path, "ner")
                else:
                    # Look for meta.json in any subdirectory
                    meta_paths = list(Path(extract_path).rglob("meta.json"))
                    if meta_paths:
                        model_path = os.path.dirname(meta_paths[0])
                    else:
                        raise FileNotFoundError(f"meta.json not found in extracted model at {extract_path}")
                
                logger.info(f"Trying alternative model path: {model_path}")
                nlp = spacy.load(model_path)
                logger.info(f"Successfully loaded model from alternative path: {model_path}")
                return nlp
            except Exception as nested_error:
                logger.error(f"All attempts to load model failed: {nested_error}")
                raise
    
    # If we get here, we couldn't find a model
    raise FileNotFoundError(f"Could not find NER model (neither uncompressed nor compressed) at {model_package_path}")

def load_english_model():
    """Load the English language model"""
    try:
        # Just load the model directly by name
        logger.info("Loading English model by name")
        english_nlp = spacy.load("en_core_web_sm", disable=["parser"])
        logger.info("Successfully loaded English model")
        return english_nlp
    except OSError as e:
        logger.error(f"Failed to load English model: {e}")
        # Try to download the model if it's not available
        logger.info("Attempting to download the English model")
        try:
            spacy.cli.download("en_core_web_sm")
            english_nlp = spacy.load("en_core_web_sm", disable=["parser"])
            logger.info("Successfully downloaded and loaded English model")
            return english_nlp
        except Exception as download_error:
            logger.error(f"Failed to download English model: {download_error}")
            raise

def setup_nlp_pipeline():
    """Set up the NLP pipeline with both models"""
    global nlp, english_nlp
    
    if nlp is None:
        nlp = load_ner_model()
    
    if english_nlp is None:
        english_nlp = load_english_model()
    
    # Add the English NER component to the pipeline if not already present
    if "english_ner" not in nlp.pipe_names:
        nlp.add_pipe("ner", source=english_nlp, name="english_ner", last=True)
    
    # Add the entity merger if not present
    if "entity_merger" not in nlp.pipe_names:
        nlp.add_pipe("entity_merger", after="english_ner")
    
    return nlp

def init_geolocator():
    """Initialize the geolocator with proper timeout for Cloud Run"""
    global geolocator
    if geolocator is None:
        geolocator = Nominatim(user_agent="cloud_run_geocode", timeout=5)
    return geolocator

def clean_text(text):
    """Clean text using the same preprocessing steps as training data"""
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove multiple periods/commas
    text = re.sub(r'\.+', '.', text)
    text = re.sub(r',+', ',', text)
    
    return text.strip()



def get_location_coords(location_name):
    """Get coordinates for a location name"""
    geo = init_geolocator()
    
    try:
        location = geo.geocode(location_name)
        if location:
            lat, lon = location.latitude, location.longitude
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return location_name, lat, lon
            else:
                logger.warning(f"Invalid coordinates for {location_name}: {lat}, {lon}")
                return location_name, None, None
        else:
            logger.info(f"Could not geocode location: {location_name}")
            return location_name, None, None
    except Exception as e:
        logger.error(f"Error geocoding {location_name}: {e}")
        return location_name, None, None

def getLocations(text):
    """Main function to extract locations from text"""
    # Initialize the pipeline if needed
    if nlp is None:
        setup_nlp_pipeline()
    
    # Clean the text
    cleaned_text = clean_text(text)
    
    # Process with NER model
    doc = nlp(cleaned_text)
    
    # Create a list to store all found locations with coordinates
    locations = []
    
    # Track locations we've already processed to avoid duplicates
    processed_locations = set()
    
    for ent in doc.ents:
        if ent.label_ == "LOCATION" and ent.text not in processed_locations:
            processed_locations.add(ent.text)
            location_name, lat, lon = get_location_coords(ent.text)
            
            if lat and lon:
                locations.append({
                    "location": location_name,
                    "latitude": lat,
                    "longitude": lon
                })
            time.sleep(0.5)  # Reduced sleep time for Cloud Run
    
    return locations

# Initialize the temp directory on module load
init_temp_dir()

'''
import time
import json
import warnings
from pathlib import Path
import sys
import re
import os
from geopy.geocoders import Nominatim
import spacy
from spacy.tokens import Span
from spacy.language import Language
import tarfile
import tempfile
import shutil
import atexit
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ner_implementation')

warnings.filterwarnings("ignore", message="torch.utils._pytree._register_pytree_node is deprecated")

# Global variables
nlp = None
english_nlp = None
temp_dir = None
geolocator = None

def init_temp_dir():
    """Initialize a temporary directory that will be cleaned up on exit"""
    global temp_dir
    temp_dir = tempfile.mkdtemp(prefix="ner_model_")
    logger.info(f"Created temporary directory: {temp_dir}")
    
    # Register cleanup function
    atexit.register(cleanup_temp_dir)
    
    return temp_dir

def cleanup_temp_dir():
    """Clean up temporary directory on exit"""
    global temp_dir
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory: {e}")

def get_model_path():
    """Get the path to the NER model, handling Cloud Run environment"""
    # Check environment variable first (for Cloud Run)
    env_path = os.environ.get("NER_MODEL_PATH")
    if env_path and os.path.exists(env_path):
        logger.info(f"Using NER model path from environment variable: {env_path}")
        return env_path
        
    # Fallback to relative path
    base_path = os.path.dirname(os.path.abspath(__file__))
    model_package_path = os.path.join(base_path, "models/ner_model_package")
    logger.info(f"Using default model path: {model_package_path}")
    
    return model_package_path

def load_ner_model():
    """Load the NER model, handling Cloud Run environment"""
    global temp_dir
    
    # Initialize temp directory if needed
    if not temp_dir:
        init_temp_dir()
    
    # Get the model path
    model_package_path = get_model_path()
    logger.info(f"Looking for NER model at: {model_package_path}")
    
    # Check if model directory exists
    if not os.path.exists(model_package_path):
        raise FileNotFoundError(f"NER model package directory not found at: {model_package_path}")
    
    # Log directory contents for debugging
    logger.info(f"Contents of model directory: {os.listdir(model_package_path)}")
    
    # First try: Look for meta.json in the model directory (uncompressed model)
    meta_json_path = os.path.join(model_package_path, "meta.json")
    if os.path.exists(meta_json_path):
        logger.info(f"Found meta.json at {meta_json_path}, trying to load directly...")
        try:
            nlp = spacy.load(model_package_path)
            logger.info(f"Successfully loaded NER model directly from: {model_package_path}")
            return nlp
        except Exception as e:
            logger.warning(f"Error loading model directly from package: {e}")
            # Continue to try compressed model
    
    # Second try: Look for compressed model
    compressed_model_path = os.path.join(model_package_path, "ner_model.tar.gz")
    if os.path.exists(compressed_model_path):
        logger.info(f"Found compressed model at {compressed_model_path}, extracting...")
        
        # Create a clean extraction directory
        extract_path = os.path.join(temp_dir, "ner_model")
        os.makedirs(extract_path, exist_ok=True)
        
        # Extract the tar file
        with tarfile.open(compressed_model_path) as tar:
            # List contents before extraction
            members = [m.name for m in tar.getmembers()]
            logger.info(f"Contents of tar file: {members}")
            
            # Extract all files
            tar.extractall(path=extract_path)
        
        # Log the extracted contents
        logger.info(f"Extracted files to: {extract_path}")
        logger.info(f"Contents of extract directory: {os.listdir(extract_path)}")
        
        # Try to load the model
        logger.info(f"Attempting to load model from: {extract_path}")
        try:
            nlp = spacy.load(extract_path)
            logger.info(f"Successfully loaded NER model from: {extract_path}")
            return nlp
        except Exception as e:
            logger.error(f"Failed to load model from {extract_path}: {e}")
            
            # Try a more comprehensive search if direct loading fails
            try:
                # Check if meta.json is in the root or in a subdirectory
                if os.path.exists(os.path.join(extract_path, "meta.json")):
                    model_path = extract_path
                elif os.path.exists(os.path.join(extract_path, "ner", "meta.json")):
                    model_path = os.path.join(extract_path, "ner")
                else:
                    # Look for meta.json in any subdirectory
                    meta_paths = list(Path(extract_path).rglob("meta.json"))
                    if meta_paths:
                        model_path = os.path.dirname(meta_paths[0])
                    else:
                        raise FileNotFoundError(f"meta.json not found in extracted model at {extract_path}")
                
                logger.info(f"Trying alternative model path: {model_path}")
                nlp = spacy.load(model_path)
                logger.info(f"Successfully loaded model from alternative path: {model_path}")
                return nlp
            except Exception as nested_error:
                logger.error(f"All attempts to load model failed: {nested_error}")
                raise
    
    # If we get here, we couldn't find a model
    raise FileNotFoundError(f"Could not find NER model (neither uncompressed nor compressed) at {model_package_path}")

def load_english_model():
    """Load the English language model"""
    try:
        # Just load the model directly by name
        logger.info("Loading English model by name")
        english_nlp = spacy.load("en_core_web_sm", disable=["parser"])
        logger.info("Successfully loaded English model")
        return english_nlp
    except OSError as e:
        logger.error(f"Failed to load English model: {e}")
        # Try to download the model if it's not available
        logger.info("Attempting to download the English model")
        try:
            spacy.cli.download("en_core_web_sm")
            english_nlp = spacy.load("en_core_web_sm", disable=["parser"])
            logger.info("Successfully downloaded and loaded English model")
            return english_nlp
        except Exception as download_error:
            logger.error(f"Failed to download English model: {download_error}")
            raise

@Language.component("entity_merger")
def merge_entities(doc):
    """Merge entities from multiple models"""
    original_ents = list(doc.ents)
    new_ents = []
    
    # Get entities from English model
    english_doc = english_nlp(doc.text)
    
    for ent in english_doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            # Convert character offsets to token indices for this doc
            start_char = ent.start_char
            end_char = ent.end_char
            
            # Find corresponding token spans in the current doc
            start_token = None
            end_token = None
            
            for i, token in enumerate(doc):
                if token.idx <= start_char < token.idx + len(token.text):
                    start_token = i
                if token.idx <= end_char <= token.idx + len(token.text):
                    end_token = i + 1
                    break
            
            if start_token is not None and end_token is not None:
                # Check for overlap with existing entities
                overlap = False
                for existing_ent in original_ents:
                    # Check if spans overlap
                    if (start_token < existing_ent.end and end_token > existing_ent.start):
                        overlap = True
                        break
                
                if not overlap:
                    new_ent = Span(doc, start_token, end_token, label="LOCATION")
                    new_ents.append(new_ent)
    
    # Combine both entity lists and filter out any remaining overlaps
    all_ents = original_ents + new_ents
    
    # Sort by entity length (longer entities first) to prioritize them
    all_ents.sort(key=lambda x: (x.end - x.start), reverse=True)
    
    # Filter out overlapping entities
    filtered_ents = []
    taken_indices = set()
    
    for ent in all_ents:
        ent_indices = set(range(ent.start, ent.end))
        if not ent_indices.intersection(taken_indices):
            filtered_ents.append(ent)
            taken_indices.update(ent_indices)
    
    doc.ents = filtered_ents
    return doc

def setup_nlp_pipeline():
    """Set up the NLP pipeline with both models"""
    global nlp, english_nlp
    
    if nlp is None:
        nlp = load_ner_model()
    
    if english_nlp is None:
        english_nlp = load_english_model()
    
    # Add the English NER component and entity merger to the pipeline if not already present
    if "english_ner" not in nlp.pipe_names:
        nlp.add_pipe("ner", source=english_nlp, name="english_ner", last=True)
    
    if "entity_merger" not in nlp.pipe_names:
        nlp.add_pipe("entity_merger", after="english_ner")
    
    return nlp

def init_geolocator():
    """Initialize the geolocator with proper timeout for Cloud Run"""
    global geolocator
    if geolocator is None:
        geolocator = Nominatim(user_agent="cloud_run_geocode", timeout=5)
    return geolocator

def clean_text(text):
    """Clean text using the same preprocessing steps as training data"""
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove multiple periods/commas
    text = re.sub(r'\.+', '.', text)
    text = re.sub(r',+', ',', text)
    
    return text.strip()

def get_location_coords(location_name):
    """Get coordinates for a location name"""
    geo = init_geolocator()
    
    try:
        location = geo.geocode(location_name)
        if location:
            lat, lon = location.latitude, location.longitude
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return location_name, lat, lon
            else:
                logger.warning(f"Invalid coordinates for {location_name}: {lat}, {lon}")
                return location_name, None, None
        else:
            logger.info(f"Could not geocode location: {location_name}")
            return location_name, None, None
    except Exception as e:
        logger.error(f"Error geocoding {location_name}: {e}")
        return location_name, None, None

def getLocations(text):
    """Main function to extract locations from text"""
    # Initialize the pipeline if needed
    if nlp is None or english_nlp is None:
        setup_nlp_pipeline()
    
    # Clean the text
    cleaned_text = clean_text(text)
    
    # Process with NER model
    doc = nlp(cleaned_text)
    
    # Create a list to store all found locations with coordinates
    locations = []
    
    # Track locations we've already processed to avoid duplicates
    processed_locations = set()
    
    for ent in doc.ents:
        if ent.label_ == "LOCATION" and ent.text not in processed_locations:
            processed_locations.add(ent.text)
            location_name, lat, lon = get_location_coords(ent.text)
            
            if lat and lon:
                locations.append({
                    "location": location_name,
                    "latitude": lat,
                    "longitude": lon
                })
            time.sleep(0.5)  # Reduced sleep time for Cloud Run
    
    return locations

# Initialize the temp directory on module load
init_temp_dir()
'''