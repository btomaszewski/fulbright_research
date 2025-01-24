import csv
import json
from aiLoader import loadAI

client = loadAI()
json_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/processedJson/imagelocationtest.json"
csv_output_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/imagelocation2.csv"

GEOCODING_OUTPUT_FIELDS = ['Message_ID', 'Text', 'Country', 'City', 'Province', 'County', 'Communes', 'Latitude', 'Longitude']
START_MARKER = "<start>"
END_MARKER = "<end>"

def processText(full_text_with_id):
    """Processes a single message text to extract geographic information using AI."""
    systemPrompt = {
        "role": "system",
        "content": (
            "You are an expert in identifying geographic locations and references in English language texts. "
            "Determine if the text contains any geographical references. Each text corresponds to a message id; some texts have the same message id. "
            "You will return a string of each geographical reference found in the text. The string will follow the format "
            "Message_ID,Country,City,Province,County,Communes,Latitude,Longitude,Text. For 'Text', return the entire text the reference was found in. "
            "If no value exists for a field, return 'null'. Do not return additional text or characters. Do not encapsulate the result in any characters or use newlines unnecessarily."
        )
    }

    userPrompt = {
        "role": "user",
        "content": (
            f"Determine the geographical references in the text. The text is as follows: {full_text_with_id}. "
            "If geographic references are found, provide them in the specified format. Latitude and longitude are mandatory if a location exists."
        )
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[systemPrompt, userPrompt]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error processing text: {e}")
        return None

def process_messages(input_path, output_path):
    """Processes all messages from a JSON file and writes results to a CSV."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        messages = data.get("messages", [])
        if not messages:
            print("No messages found in the JSON file.")
            return

        # Combine all relevant data into a single text block
        combined_text_parts = []
        for message in messages:
            message_id = message.get("id")
            photo_analysis = message.get("PHOTO_ANALYSIS", "")
            video_summary = message.get("VIDEO_SUMMARY", "")
            transcription_translation = message.get("TRANSCRIPTION_TRANSLATION", {}).get("translation", "")
            text_entities = message.get("text_entities", [])
            
            translated_texts = [
                entity.get("TRANSLATED_TEXT", "")
                for entity in text_entities
                if "TRANSLATED_TEXT" in entity
            ]

            content = []
            if photo_analysis:
                content.append(f"PHOTO_ANALYSIS: {photo_analysis}")
            if video_summary:
                content.append(f"VIDEO_SUMMARY: {video_summary}")
            if transcription_translation:
                content.append(f"TRANSCRIPTION_TRANSLATION: {transcription_translation}")
            if translated_texts:
                content.append(f"TRANSLATED_TEXT: {' '.join(translated_texts)}")

            if content:
                combined_content = "\n".join(content)
                combined_text_parts.append(f"{START_MARKER}Message ID: {message_id}\n{combined_content}{END_MARKER}")
            else:
                print(f"Skipping Message {message_id}: No relevant data.")

        combined_text = "\n".join(combined_text_parts)
        if not combined_text.strip():
            print("No valid data found.")
            return

        # Perform AI geolocation processing
        analysis = processText(combined_text)
        if analysis:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.DictWriter(csvfile, fieldnames=GEOCODING_OUTPUT_FIELDS)
                csv_writer.writeheader()

                rows = [row.strip() for row in analysis.split("\n") if row.strip()]
                for row in rows:
                    row_data = row.split(",")
                    if len(row_data) == len(GEOCODING_OUTPUT_FIELDS):
                        csv_writer.writerow(dict(zip(GEOCODING_OUTPUT_FIELDS, row_data)))
                    else:
                        print(f"Skipping malformed row: {row}")

    except FileNotFoundError:
        print(f"File not found: {input_path}")
    except json.JSONDecodeError:
        print("Error decoding JSON file.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    process_messages(json_file, csv_output_file)


'''
LOCATOR_OUTPUT_FIELDS = ['Message_ID', 'Text', 'Country', 'City', 'Province', 'County', 'Communes', 'Latitude', 'Longitude']

def processText(full_text_with_id):
    """Processes a single message text to extract geographic information using AI."""
    systemPrompt = {
        "role": "system",
        "content": (
            "You are an expert in identifying geographic locations and references in English language texts. "
            "Determine if the text contains any geographical references. Each text corresponds to a message id; some texts have the same message id. "
            "You will return a string of each geographical reference found in the text. The string will follow the format "
            "Message_id,Country,City,Province,County,Communes,Latitude,Longitude,text. For 'text' return the whole text the reference was found in. Do not return any additional text or descriptions. "
            "Do not encapsulate the result in any characters or use newlines unnecessarily."
        )
    }

    userPrompt = {
        "role": "user",
        "content": (
            f"Determine the geographical references in the text. The text is as follows: {full_text_with_id}. "
            "If geographic references are found, provide country, city, province, county, commune, latitude, longitude. "
            "If there is a location, latitude and longitude are mandatory. Other fields may be null. For null fields reutrn 'null'"
        )
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[systemPrompt, userPrompt]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error processing text: {e}")
        return None

def process_messages(input_path, output_path):
    """Processes messages from a JSON file and writes geographic analysis to a CSV."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        messages = data.get("messages", [])
        if not messages:
            print("No messages found in the JSON file.")
            return

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.DictWriter(csvfile, fieldnames=LOCATOR_OUTPUT_FIELDS)
            csv_writer.writeheader()

            for message in messages:
                message_id = message.get("id")
                text_entities = message.get("text_entities", [])
                full_text = " ".join(
                    entity.get("TRANSLATED_TEXT", "").replace(",", "") for entity in text_entities if "TRANSLATED_TEXT" in entity
                )

                if full_text:
                    print(f"Processing Message {message_id}: {full_text}")
                    full_text_with_id = f"Message ID: {message_id}\n{full_text}"
                    analysis = processText(full_text_with_id)

                    if analysis:
                        try:
                            rows = analysis.split("\n")
                            for row in rows:
                                row_data = row.split(",")
                                if len(row_data) == len(LOCATOR_OUTPUT_FIELDS):
                                    csv_writer.writerow(dict(zip(LOCATOR_OUTPUT_FIELDS, row_data)))
                                else:
                                    print(f"Skipping malformed row: {row}")
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
'''