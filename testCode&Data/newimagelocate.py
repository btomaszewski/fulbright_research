import csv
import json
from aiLoader import loadAI

client = loadAI()

# Consolidated prompt template
PROMPT_TEMPLATE = (
    "You are a skilled humanitarian analyst who is an expert in identifying geographic locations in English language texts. "
    "Conduct a geographical analysis of the following texts to determine if they contain any geographical references. "
    "Each text corresponds to a message ID. For each text between the <start> and <end> tags, determine a location. "
    "The geographical references you will be looking for will likely be, but not limited to, cities and provinces in Poland or cities in Ukraine. "
    "If a geographic reference is found, provide the corresponding information of country, city, province, county, commune, latitude, and longitude. "
    "There is no limit to the number of locations you can find in a single text. If there is a location, there must be a latitude and longitude. "
    "Other values may be null. Return a string of each geographical reference found in the text between the <start> and <end> tags. "
    "The string will follow the format Message_ID,Text,Country,City,Province,County,Communes,Latitude,Longitude. "
    "Do not return any additional text, descriptions of your process, or information beyond the specified format."
)

json_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/processedJson/imagelocationtest.json"
csv_output_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/imagelocation2.csv"

GEOCODING_OUTPUT_FIELDS = ['Message_ID', 'Text', 'Country', 'City', 'Province', 'County', 'Communes', 'Latitude', 'Longitude']

def geolocate_all(context, combined_text):
    """Send a single geolocation analysis request for all concatenated texts."""
    try:
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": combined_text}
        ]
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=messages
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error analyzing text: {e}")
        return None

def process_messages(input_path, output_path):
    """Process all messages from JSON file in a single request and write results to CSV."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        messages = data.get("messages", [])
        if not messages:
            print("No messages found in the JSON file.")
            return

        # Concatenate all PHOTO_ANALYSIS texts
        combined_text = ""
        message_id_map = {}
        for message in messages:
            message_id = message.get("id")
            photo_analysis = message.get("PHOTO_ANALYSIS")

            if photo_analysis:
                combined_text += f"<start>Message ID: {message_id}\n{photo_analysis}<end>\n"
                message_id_map[message_id] = photo_analysis
            else:
                print(f"Skipping Message {message_id} because it has no PHOTO_ANALYSIS data.")

        if not combined_text.strip():
            print("No valid PHOTO_ANALYSIS texts found.")
            return

        # Perform single geolocation request
        analysis = geolocate_all(PROMPT_TEMPLATE, combined_text)

        if analysis:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.DictWriter(csvfile, fieldnames=GEOCODING_OUTPUT_FIELDS)
                csv_writer.writeheader()

                try:
                    # Split analysis by lines and parse each row
                    analysis_rows = [row.split(",") for row in analysis.split("\n") if row.strip()]
                    for row in analysis_rows:
                        csv_writer.writerow(dict(zip(GEOCODING_OUTPUT_FIELDS, row)))
                except Exception as e:
                    print(f"Error writing analysis to CSV: {e}")
    except FileNotFoundError:
        print(f"File not found: {input_path}")
    except json.JSONDecodeError:
        print("Error decoding JSON file.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    process_messages(json_file, csv_output_file)