import json
import time
import warnings
from pathlib import Path
import sys
import re
from geopy.geocoders import Nominatim
import spacy
from spacy.tokens import Span
from spacy.language import Language

warnings.filterwarnings("ignore", message="torch.utils._pytree._register_pytree_node is deprecated")

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

# Load custom model
current_dir = Path.cwd()
model_path = current_dir / "ner_model_optimized"

try:
    nlp = spacy.load(str(model_path))
    print(f"Successfully loaded custom model from {model_path}")
except OSError as e:
    print(f"Error: Could not load model from {model_path}: {e}")
    sys.exit(1)

# Load SpaCy English model
try:
    english_nlp = spacy.load("en_core_web_sm", disable=["parser"])
    print("Successfully loaded English model")
except OSError as e:
    print(f"Error: Could not load English model: {e}")
    sys.exit(1)

@Language.component("entity_merger")
def merge_entities(doc):
    original_ents = list(doc.ents)
    
    for ent in english_nlp(doc.text).ents:
        if ent.label_ in ["GPE", "LOC"]:
            if not any(
                original_ent.start_char == ent.start_char 
                and original_ent.end_char == ent.end_char 
                for original_ent in original_ents
            ):
                new_ent = Span(
                    doc, 
                    ent.start, 
                    ent.end, 
                    label="LOCATION"
                )
                original_ents.append(new_ent)
    
    doc.ents = original_ents
    return doc

nlp.add_pipe("ner", source=english_nlp, name="english_ner", last=True)
nlp.add_pipe("entity_merger", after="english_ner")

geolocator = Nominatim(user_agent="ner_geocode_app", timeout=10)

def get_location_coords(location_name):
    try:
        location = geolocator.geocode(location_name)
        if location:
            lat, lon = location.latitude, location.longitude
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
            else:
                print(f"Warning: Invalid coordinates for {location_name}: {lat}, {lon}")
                return None, None
        else:
            return None, None
    except Exception as e:
        print(f"Error geocoding {location_name}: {e}")
        return None, None

def process_text(text, text_id=None):
    # Clean the text
    cleaned_text = clean_text(text)
    
    # Process with NER model
    doc = nlp(cleaned_text)
    
    print(f"\nProcessing text{f' (ID: {text_id})' if text_id else ''}:")
    print(f"Original text: {text}")
    print(f"Cleaned text: {cleaned_text}")
    
    for ent in doc.ents:
        if ent.label_ == "LOCATION":
            lat, lon = get_location_coords(ent.text)
            if lat and lon:
                print(f"Location: {ent.text}")
                print(f"Coordinates: {lat}, {lon}")
            else:
                print(f"Could not find coordinates for location: {ent.text}")
            time.sleep(1)  # Avoid rate-limiting

def process_texts_from_json(json_file_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if not isinstance(data, list):
            raise ValueError("Input JSON must be a list of objects")

        for item in data:
            if not isinstance(item, dict) or 'id' not in item or 'text' not in item:
                print(f"Warning: Skipping invalid item in input: {item}")
                continue
            
            process_text(item['text'], item['id'])
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in file {json_file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing JSON file: {e}")
        sys.exit(1)

def main():
    input_file_path = "test_ner.json"  # Update this to your JSON file path

    try:
        print(f"Processing JSON file: {input_file_path}")
        process_texts_from_json(input_file_path)
        print("\nProcessing complete!")
    
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()



