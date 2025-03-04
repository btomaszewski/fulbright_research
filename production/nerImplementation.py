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
    text = re.sub(r'https?:\/\/(?:www\.)?[^\s]+', '', text)
    
    # Remove email addresses
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
    
    # Remove multiple periods and commas
    text = re.sub(r'([.,])\1+', r'\1', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text 

# Load custom model
current_dir = Path.cwd()
model_path = current_dir / "ner_model_optimized2"

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
    english_doc = english_nlp(doc.text)
    
    # Create a set to track token indices that are already part of entities
    used_tokens = set()
    for ent in original_ents:
        for i in range(ent.start, ent.end):
            used_tokens.add(i)
    
    # Try to add English model entities, but check for overlaps
    for ent in english_doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            # Check if any tokens in this span are already used
            span_tokens = set(range(ent.start, ent.end))
            if not span_tokens.intersection(used_tokens):  # No overlap
                try:
                    new_ent = Span(
                        doc, 
                        ent.start, 
                        ent.end, 
                        label="LOCATION"
                    )
                    original_ents.append(new_ent)
                    # Mark these tokens as used
                    used_tokens.update(span_tokens)
                except ValueError as e:
                    print(f"Warning: Couldn't create entity span: {e}")
    
    try:
        doc.ents = original_ents
    except ValueError as e:
        print(f"Warning: Error setting entities: {e}")
        # Fall back to just using the original entities
        doc.ents = doc.ents
        
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

def process_text(text, message_id=None):
    # Clean the text
    cleaned_text = clean_text(text)
    
    print(f"\nProcessing message{f' (ID: {message_id})' if message_id else ''}:")
    print(f"Original text: {text}")
    print(f"Cleaned text: {cleaned_text}")
    
    # Store the locations and coordinates
    locations = []
    
    try:
        # Process with NER model
        doc = nlp(cleaned_text)
        
        for ent in doc.ents:
            if ent.label_ == "LOCATION":
                try:
                    lat, lon = get_location_coords(ent.text)
                    location_info = {"name": ent.text}
                    
                    if lat and lon:
                        print(f"Location: {ent.text}")
                        print(f"Coordinates: {lat}, {lon}")
                        location_info["coordinates"] = {"latitude": lat, "longitude": lon}
                    else:
                        print(f"Could not find coordinates for location: {ent.text}")
                        location_info["coordinates"] = None
                        
                    locations.append(location_info)
                    time.sleep(1)  # Avoid rate-limiting
                except Exception as e:
                    print(f"Error processing location '{ent.text}': {e}")
    except Exception as e:
        print(f"Error processing document: {e}")
        
    return locations

def process_telegram_json(json_file_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # If the JSON structure doesn't match what we expected from the sample,
        # try to handle different possible structures
        if isinstance(data, dict):
            # Structure like your example with a messages array inside main object
            if 'messages' in data:
                messages = data['messages']
                chat_name = data.get('name', 'Unknown')
                chat_id = data.get('id', 'Unknown')
                chat_type = data.get('type', 'Unknown')
            else:
                print("Warning: No 'messages' field found in JSON. Using the entire object as a message list.")
                messages = [data]  # Treat the whole object as a single message
                chat_name = "Unknown"
                chat_id = "Unknown" 
                chat_type = "Unknown"
        elif isinstance(data, list):
            # The JSON might be an array of messages directly
            messages = data
            chat_name = "Unknown"
            chat_id = "Unknown"
            chat_type = "Unknown"
        else:
            print("Error: JSON data is neither an object nor an array")
            return
            
        print(f"Processing chat: {chat_name} (ID: {chat_id})")
        print(f"Type: {chat_type}")
        
        # Track whether any changes were made
        changes_made = False
        
        # Process each message
        for message in messages:
            if not isinstance(message, dict):
                continue
                
            # Get the translated text if available
            if 'TRANSLATED_TEXT' in message and message['TRANSLATED_TEXT']:
                translated_text = message['TRANSLATED_TEXT']
                message_id = message.get('id')
                
                try:
                    # Process the translated text with our NER pipeline
                    locations = process_text(translated_text, message_id)
                    
                    # Add the locations to the message if any were found
                    if locations:
                        message['LOCATIONS'] = locations
                        changes_made = True
                except Exception as e:
                    print(f"Error processing message {message_id}: {e}")
            else:
                message_id = message.get('id', 'Unknown')
                print(f"Skipping message {message_id} - No translated text available")
        
        # Save the updated JSON file if changes were made
        if changes_made:
            with open(json_file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            print(f"\nUpdated JSON saved to {json_file_path}")
        else:
            print("\nNo locations found, original file not modified")
        
        print("Processing complete!")
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in file {json_file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing JSON file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    input_file_path = "nerdata.json"  # Update this to your JSON file path
    
    # You can also create a backup of the original file
    backup = True  # Set to False to disable backups
    
    try:
        if backup:
            from shutil import copyfile
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{input_file_path}.{timestamp}.bak"
            
            copyfile(input_file_path, backup_path)
            print(f"Created backup at: {backup_path}")
        
        print(f"Processing JSON file: {input_file_path}")
        process_telegram_json(input_file_path)
    
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
