import json

# Load JSON file
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Remove null values recursively
def remove_null_values(data):
    """
    Recursively remove null (None) values from dictionaries and lists.
    """
    if isinstance(data, dict):
        return {k: remove_null_values(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [remove_null_values(v) for v in data if v is not None]
    else:
        return data

# Filter and transform JSON data
def filter_and_group_data(data):
    result = {"GeoJSON": []}

    for message in data.get("messages", []):
        filtered_message = {
            "id": message.get("id"),
            "PHOTO_ANALYSIS": message.get("PHOTO_ANALYSIS"),
            "VIDEO_SUMMARY": message.get("VIDEO_SUMMARY"),
            "VIDEO_TRANSCRIPTION": message.get("VIDEO_TRANSCRIPTION"),
        }

        if "TRANSCRIPTION_TRANSLATION" in message:
            filtered_message["TRANSCRIPTION_TRANSLATION"] = {
                "translation": message["TRANSCRIPTION_TRANSLATION"].get("translation")
            }

        if "text_entities" in message:
            filtered_message["text_entities"] = [
                {
                    "text": entity.get("text"),
                    "TRANSLATED_TEXT": entity.get("TRANSLATED_TEXT")
                }
                for entity in message["text_entities"]
                if "text" in entity
            ]

        result["GeoJSON"].append(filtered_message)

    return result

# Save filtered data to a new file
def save_json(data, output_path):
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Main script
if __name__ == "__main__":
    input_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/processedJson/resultProcessed.json"  # Replace with your input file path
    output_file = "GeoJSON.json"

    # Load, filter, and clean JSON data
    json_data = load_json(input_file)
    filtered_data = filter_and_group_data(json_data)
    cleaned_data = remove_null_values(filtered_data)
    save_json(cleaned_data, output_file)

    print(f"Filtered and cleaned data has been saved to {output_file}")