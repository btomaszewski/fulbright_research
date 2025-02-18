import json
import time
import warnings
from pathlib import Path
import sys
from geopy.geocoders import Nominatim
import spacy
from spacy.tokens import Span
from spacy.language import Language

warnings.filterwarnings("ignore", message="torch.utils._pytree._register_pytree_node is deprecated")

# Load custom model - Update the path to your new model trained from JSONL
current_dir = Path.cwd()
model_path = current_dir / "ner_model_optimized"  # Update to your new model path

try:
    nlp = spacy.load(str(model_path))
    print(f"Successfully loaded custom model from {model_path}")
except OSError as e:
    print(f"Error: Could not load model from {model_path}: {e}")
    sys.exit(1)

# Load SpaCy English model with necessary components
try:
    # Only disable parser as we need tagger and attribute_ruler for lemmatization
    english_nlp = spacy.load("en_core_web_sm", disable=["parser"])
    print("Successfully loaded English model")
except OSError as e:
    print(f"Error: Could not load English model: {e}")
    sys.exit(1)

# Register a custom component to carefully merge entities
@Language.component("entity_merger")
def merge_entities(doc):
    # Preserve original entities from your custom model
    original_ents = list(doc.ents)
    
    # Add entities from English model, avoiding duplicates
    for ent in english_nlp(doc.text).ents:
        # Only consider GPE (Geo-Political Entities) and LOC (Locations)
        if ent.label_ in ["GPE", "LOC"]:
            # Check if this entity doesn't already exist
            if not any(
                original_ent.start_char == ent.start_char 
                and original_ent.end_char == ent.end_char 
                for original_ent in original_ents
            ):
                # Convert to a new span in the current doc context
                new_ent = Span(
                    doc, 
                    ent.start, 
                    ent.end, 
                    label="LOCATION"  # Normalize label
                )
                original_ents.append(new_ent)
    
    # Set the merged entities
    doc.ents = original_ents
    return doc

# Add the English NER component
nlp.add_pipe("ner", source=english_nlp, name="english_ner", last=True)

# Add the entity merger component after the English NER
nlp.add_pipe("entity_merger", after="english_ner")

# Initialize Geopy geolocator with a custom user agent and timeout
geolocator = Nominatim(user_agent="ner_geocode_app", timeout=10)

# Function to get latitude and longitude with validation
def get_location_coords(location_name):
    try:
        location = geolocator.geocode(location_name)
        if location:
            lat, lon = location.latitude, location.longitude
            
            # Validate coordinates
            if validate_location(location_name, lat, lon):
                return lat, lon
            else:
                print(f"Warning: Invalid coordinates for {location_name}: {lat}, {lon}")
                return None, None
        else:
            return None, None
    except Exception as e:
        print(f"Error geocoding {location_name}: {e}")
        return None, None

# Simple validation function for coordinates
def validate_location(location_name, lat, lon):
    # Basic validation - check if coordinates are within valid range
    if lat < -90 or lat > 90 or lon < -180 or lon > 180:
        return False
    return True

# Process texts in batches for better performance
def process_texts_batch(texts, batch_size=32):
    docs = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_docs = list(nlp.pipe(batch_texts))
        docs.extend(batch_docs)
    return docs

# Main function to process JSON input
def process_texts_from_json(json_file_path, batch_size=32):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if not isinstance(data, list):
            raise ValueError("Input JSON must be a list of objects")

        texts = []
        text_ids = []
        
        for item in data:
            if not isinstance(item, dict) or 'id' not in item or 'text' not in item:
                print(f"Warning: Skipping invalid item in input: {item}")
                continue
                
            texts.append(item['text'])
            text_ids.append(item['id'])
        
        if not texts:
            raise ValueError("No valid text entries found in input file")
        
        # Process texts in batches
        docs = process_texts_batch(texts, batch_size)
        
        ner_output = []
        for doc, text_id, text in zip(docs, text_ids, texts):
            entities = [(ent.start_char, ent.end_char, ent.label_, ent.text) for ent in doc.ents]
            
            ner_output.append({
                'text_id': text_id,
                'text': text,
                'entities': entities
            })
        
        return ner_output
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in file {json_file_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing JSON file: {e}")
        sys.exit(1)

# Convert geocoded results to GeoJSON format
def convert_to_geojson(geocoded_results):
    features = []
    
    for result in geocoded_results:
        text_id = result['text_id']
        text = result['text']
        
        for location in result['locations']:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [location['longitude'], location['latitude']]
                },
                "properties": {
                    "id": text_id,
                    "name": location['name'],
                    "text": text,
                    "confidence": location.get('confidence', None)
                }
            }
            features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }

# Process NER output and geocode locations with rate limiting and retries
def process_ner_output(ner_output, max_retries=3):
    geocoded_results = []

    for entry in ner_output:
        text_id = entry['text_id']
        text = entry['text']
        entities = entry['entities']
        
        locations = []
        for _, _, label, location_name in entities:
            if label == "LOCATION":
                retry_count = 0
                lat, lon = None, None
                
                while retry_count < max_retries and not (lat and lon):
                    lat, lon = get_location_coords(location_name)
                    if lat and lon:
                        locations.append({
                            "name": location_name, 
                            "latitude": lat, 
                            "longitude": lon,
                            "confidence": None
                        })
                    else:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"Retrying geocoding for {location_name} (attempt {retry_count+1}/{max_retries})")
                            time.sleep(2)
                
                time.sleep(1)  # Avoid rate-limiting

        geocoded_results.append({"text_id": text_id, "text": text, "locations": locations})

    return geocoded_results

# Main function
def main():
    input_file_path = "test_ner.json"  # Update to your JSON file path
    geojson_output_path = "output_locations.geojson"
    batch_size = 32

    try:
        print(f"Processing JSON file: {input_file_path}")
        ner_output = process_texts_from_json(input_file_path, batch_size)
        
        # Run processing
        geocoded_results = process_ner_output(ner_output)
        geojson_data = convert_to_geojson(geocoded_results)

        # Save to GeoJSON file
        with open(geojson_output_path, "w", encoding="utf-8") as geojson_file:
            json.dump(geojson_data, geojson_file, indent=4)

        print(f"GeoJSON file saved to {geojson_output_path}")
        print(f"Processed {len(ner_output)} text entries")
        print(f"Found and geocoded locations in {len([r for r in geocoded_results if r['locations']])} entries")
    
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()



