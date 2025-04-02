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

# Create a tempdir that will be cleaned up on exit
temp_dir = tempfile.mkdtemp(prefix="ner_model_")
logger.info(f"Created temporary directory: {temp_dir}")

def cleanup_temp_dir():
    """Clean up temporary directory on exit"""
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory: {e}")

# Register cleanup function
atexit.register(cleanup_temp_dir)

def load_ner_model():
    """Load the NER model, handling both PyInstaller and development environments"""
    
    # Determine the base path depending on whether we're running in PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        model_package_path = "./ner_model_package"
        logger.info(f"Running in PyInstaller bundle, base path: {base_path}")
    else:
        # Running in normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
        model_package_path = os.path.join(base_path, "ner_model_package")
        logger.info(f"Running in normal Python environment, script dir: {base_path}")

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
        
        # Try to load the model
        logger.info(f"Attempting to load model from: {model_path}")
        try:
            nlp = spacy.load(model_path)
            logger.info(f"Successfully loaded NER model from: {model_path}")
            return nlp
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {model_path}: {e}")
    
    # If we get here, we couldn't find a model
    raise FileNotFoundError(f"Could not find NER model (neither uncompressed nor compressed) at {model_package_path}")

# Load the NER model
try:
    nlp = load_ner_model()
except Exception as e:
    logger.error(f"Failed to load NER model: {e}")
    sys.exit(1)

# Load SpaCy English model
try:
    # Determine the base path depending on whether we're running in PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        base_path = sys._MEIPASS
        
        # Look for tarball
        compressed_model_path = os.path.join(base_path, "en_core_web_sm.tar.gz")
        
        if os.path.exists(compressed_model_path):
            logger.info(f"Found compressed English model at {compressed_model_path}, extracting...")
            
            # Create extraction directory in temp dir
            extract_path = os.path.join(temp_dir, "en_core_web_sm")
            os.makedirs(extract_path, exist_ok=True)
            
            # Extract the tar file
            with tarfile.open(compressed_model_path) as tar:
                # Log tarball contents
                logger.info("Tarball contents:")
                for member in tar.getmembers():
                    logger.info(f"  {member.name} ({member.size} bytes)")
                
                # Extract all files
                tar.extractall(path=extract_path)
            
            # Log the extracted contents
            logger.info(f"Extracted English model to: {extract_path}")
            logger.info(f"Contents: {os.listdir(extract_path)}")
            
            # Recursively list all extracted files for debugging
            logger.info("All extracted files:")
            for root, dirs, files in os.walk(extract_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    logger.info(f"  {os.path.relpath(full_path, extract_path)} "
                                f"({os.path.getsize(full_path)} bytes)")
            
            # Verify config.cfg exists
            config_path = os.path.join(extract_path, "config.cfg")
            if os.path.exists(config_path):
                logger.info(f"Found config.cfg: {config_path}")
            else:
                # Search for config.cfg anywhere in the extracted directory
                logger.info("Searching for config.cfg...")
                config_files = list(Path(extract_path).rglob("config.cfg"))
                if config_files:
                    # Use the directory containing config.cfg as the model path
                    extract_path = os.path.dirname(config_files[0])
                    logger.info(f"Found config.cfg at: {config_files[0]}")
                    logger.info(f"Using model path: {extract_path}")
                else:
                    logger.error("No config.cfg found in extracted model!")
            
            # Load the model
            logger.info(f"Loading spaCy model from: {extract_path}")
            english_nlp = spacy.load(extract_path, disable=["parser"])
            logger.info("Successfully loaded English model from extracted tarball")
        else:
            raise FileNotFoundError(f"Compressed English model not found at: {compressed_model_path}")
    else:
        # Running in normal Python environment
        logger.info("Loading English model by name in development environment")
        english_nlp = spacy.load("en_core_web_sm", disable=["parser"])
    
    logger.info("Successfully loaded English model")
except OSError as e:
    logger.error(f"Failed to load English model: {e}")
    # Print detailed stack trace for debugging
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    english_model_path = os.path.join(sys._MEIPASS, "en_core_web_sm")
    logger.info(f"English model directory structure check:")
    if os.path.exists(english_model_path):
        logger.info(f"Directory exists: {english_model_path}")
        logger.info(f"Contents: {os.listdir(english_model_path)}")
        config_path = os.path.join(english_model_path, "config.cfg")
        if os.path.exists(config_path):
            logger.info(f"config.cfg exists and is size: {os.path.getsize(config_path)}")
        else:
            logger.info(f"config.cfg does not exist")
    else:
        logger.info(f"Directory doesn't exist: {english_model_path}")

@Language.component("entity_merger")
def merge_entities(doc):
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

# Add the English NER component and entity merger to the pipeline
nlp.add_pipe("ner", source=english_nlp, name="english_ner", last=True)
nlp.add_pipe("entity_merger", after="english_ner")

geolocator = Nominatim(user_agent="ner_geocode_app", timeout=10)

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
    try:
        location = geolocator.geocode(location_name)
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
            time.sleep(1)  # Avoid rate-limiting
    
    return locations