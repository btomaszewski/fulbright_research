import json
import time
import warnings
from pathlib import Path
from geopy.geocoders import Nominatim
import spacy

warnings.filterwarnings("ignore", message="torch.utils._pytree._register_pytree_node is deprecated")

# Load the spaCy model
current_dir = Path.cwd()
model_path = current_dir / "ner_model"
nlp = spacy.load(str(model_path))

# Initialize Geopy geolocator
geolocator = Nominatim(user_agent="ner_geocode_app")

# Function to get latitude and longitude
def get_location_coords(location_name):
    try:
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        print(f"Error geocoding {location_name}: {e}")
        return None, None

# Process texts from JSON file
def process_texts_from_json(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    ner_output = []
    for item in data:
        text = item['text']
        doc = nlp(text)
        entities = [(ent.start_char, ent.end_char, ent.label_, ent.text) for ent in doc.ents]
        
        ner_output.append({
            'text_id': item['id'],
            'text': text,
            'entities': entities
        })
    
    return ner_output

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
                    "coordinates": [location['longitude'], location['latitude']]  # GeoJSON uses [lon, lat]
                },
                "properties": {
                    "id": text_id,
                    "name": location['name'],
                    "text": text
                }
            }
            features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }

# Process NER output and geocode locations
def process_ner_output(ner_output):
    geocoded_results = []

    for entry in ner_output:
        text_id = entry['text_id']
        text = entry['text']
        entities = entry['entities']
        
        locations = []
        for _, _, _, location_name in entities:
            lat, lon = get_location_coords(location_name)
            if lat and lon:
                locations.append({"name": location_name, "latitude": lat, "longitude": lon})
            time.sleep(1)  # Avoid rate-limiting

        geocoded_results.append({"text_id": text_id, "text": text, "locations": locations})

    return geocoded_results

# File paths
json_file_path = "test_ner.json"
geojson_output_path = "output.geojson"

# Run processing
ner_output = process_texts_from_json(json_file_path)
geocoded_results = process_ner_output(ner_output)
geojson_data = convert_to_geojson(geocoded_results)

# Save to GeoJSON file
with open(geojson_output_path, "w", encoding="utf-8") as geojson_file:
    json.dump(geojson_data, geojson_file, indent=4)

print(f"GeoJSON file saved to {geojson_output_path}")

