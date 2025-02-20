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

warnings.filterwarnings("ignore", message="torch.utils._pytree._register_pytree_node is deprecated")

# Load custom model
pyDir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(pyDir, "ner_model_optimized2")

try:
    nlp = spacy.load(str(model_path))
except OSError as e:
    sys.exit(1)

# Load SpaCy English model
try:
    english_nlp = spacy.load("en_core_web_sm", disable=["parser"])
except OSError as e:
    sys.exit(1)

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

# Properly get the English NER component and add it to the pipeline
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
                #print(f"Found coordinates for {location_name}: {lat}, {lon}")
                return location_name, lat, lon
            else:
                #print(f"Warning: Invalid coordinates for {location_name}: {lat}, {lon}")
                return location_name, None, None
        else:
            #print(f"Could not geocode location: {location_name}")
            return location_name, None, None
    except Exception as e:
        #print(f"Error geocoding {location_name}: {e}")
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