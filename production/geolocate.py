import csv
import json
from aiLoader import loadAI

client = loadAI()

PROMPT_PART_1 = "Conduct a geographical analysis of text messages to determine if the English language text contains any geographical references.<start>"
PROMPT_PART_2 = "You will return several things"
PROMPT_PART_3 = "Each transled text corresponds to a message ID. For each translated text between the <start> and <end> tags determine a location. The geographical references you will be looking for will likely be, but not limited to, cities and provinces in Poland or cities in Ukraine. If a geographic reference was found, provide the corresponding information of country, city, province, county, commune, latitude and longitude. There is no  limit to the number of locations you want to find in a single text. There can be null values."
PROMPT_PART_4 = "Return a string of for each geographical reference found in the translated text between the <start> and <end> tags. Return the string in the formation of 'Country,City,Province,County,Communes,Latitude,Longitude,Geographic_Analysis,translated_message'. Allow null values in the string."
PROMPT_PART_5 = "Do not return any additional text, descriptions of your process or information beyond the items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters."
MOTIVATION_MESSAGE = "You are a skilled humanitarian analyst who is an expert in identifying geographic locations in English language texts."

json_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/processedJson/testgeo.json"
csv_output_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/GeocodingResults.csv"

GEOCODING_OUTPUT_FIELDS = ['Country', 'City', 'Province', 'County', 'Communes', 'Latitude', 'Longitude', 'Geographic_Analysis']

def geolocate(text):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "system", "content": MOTIVATION_MESSAGE},
                {"role": "user", "content": PROMPT_PART_1 + text +PROMPT_PART_2 + PROMPT_PART_3 + PROMPT_PART_4 + PROMPT_PART_5}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return None

# Open CSV file for writing
def process_messages(input_path, output_path):
    """Process messages from JSON file and write geographical analysis to CSV."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        messages = data.get("messages", [])
        if not messages:
            print("No messages found in the JSON file.")
            return

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.DictWriter(csvfile, fieldnames=GEOCODING_OUTPUT_FIELDS)
            csv_writer.writeheader()

            for message in messages:
                message_id = message.get("id")
                text_entities = message.get("text_entities", [])
                full_text = " ".join(entity.get("TRANSLATED_TEXT", "") for entity in text_entities if "TRANSLATED_TEXT" in entity)

                if full_text:
                    print(f"Processing Message {message_id}: {full_text}")
                    analysis = geolocate(full_text)

                    if analysis:
                        try:
                            analysis_rows = [row.split(",") for row in analysis.split("\n") if row.strip()]
                            for row in analysis_rows:
                                csv_writer.writerow(dict(zip(GEOCODING_OUTPUT_FIELDS, row)))
                        except Exception as e:
                            print(f"Error writing analysis for message {message_id}: {e}")
                else:
                    print(f"Message {message_id} has no translatable text.")
    except FileNotFoundError:
        print(f"File not found: {input_path}")
    except json.JSONDecodeError:
        print("Error decoding JSON file.")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    process_messages(json_file, csv_output_file)
