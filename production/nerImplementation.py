import warnings
warnings.filterwarnings("ignore", message="torch.utils._pytree._register_pytree_node is deprecated")

import spacy
import json
from pathlib import Path
from geopy.geocoders import Nominatim
import time

# Get current directory
current_dir = Path.cwd()
model_path = current_dir / "ner_model"
print(f"Loading model from: {model_path}")

# Load the spaCy model
nlp = spacy.load(str(model_path))
print("Model loaded successfully")

# Read and process the JSON file
def process_texts_from_json(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    ner_output = []
    for item in data:
        text = item['text']  # Extract text from the dictionary
        doc = nlp(text)  # Process text with the NER model
        print(f"\nProcessing text ID {item['id']}: {text}")
        entities = []
        
        # Extract entities
        for ent in doc.ents:
            print(f"Text: {ent.text}, Label: {ent.label_}")
            entities.append([ent.start_char, ent.end_char, ent.label_])
        
        # Store the text ID and associated entities
        ner_output.append({
            'text_id': item['id'],
            'text': text,
            'entities': entities
        })
    
    return ner_output

json_file_path = "test_ner.json"  # Replace with your JSON file path
ner_output = process_texts_from_json(json_file_path)

# Initialize Geopy geolocator
geolocator = Nominatim(user_agent="ner_geocode_app")

# Function to get latitude and longitude
def get_location_coords(location_name):
    try:
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None  # Location not found
    except Exception as e:
        print(f"Error geocoding {location_name}: {e}")
        return None, None

# Function to process NER output and maintain Text ID
def process_ner_output_with_id(text_id, text, entities):
    location_coords = []
    
    # Extract cities and landmarks based on NER output
    for entity in entities:
        location_name = text[entity[0]:entity[1]]  # Extracting entity text
        lat, lon = get_location_coords(location_name)
        if lat and lon:
            location_coords.append({
                'name': location_name,
                'latitude': lat,
                'longitude': lon
            })
        time.sleep(1)  # Be polite and avoid overloading the geocoder with requests
    
    return {
        'text_id': text_id,
        'text': text,
        'locations': location_coords
    }

# Process all texts and geocode their entities
geocoded_results = []
for entry in ner_output:
    text_id = entry['text_id']
    text = entry['text']
    entities = entry['entities']
    
    # Process the text and pass through Geopy to get coordinates
    result = process_ner_output_with_id(text_id, text, entities)
    geocoded_results.append(result)

# Print the geocoded results
for result in geocoded_results:
    print(f"Text ID: {result['text_id']}")
    print(f"Text: {result['text']}")
    print("Locations:")
    for location in result['locations']:
        print(f"- {location['name']}: Latitude: {location['latitude']}, Longitude: {location['longitude']}")
    print()
