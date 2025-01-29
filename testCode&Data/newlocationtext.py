import json
import csv
from aiLoader import loadAI

client = loadAI()

# Function to remove commas from a string
def remove_commas(text):
    return text.replace(",", "")

# Function to interact with OpenAI API
def call_openai_api(system_prompt, user_prompt):
    try:
        response = loadAI.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error: {e}")
        return None

# Load JSON file
input_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/processedJson/imagelocationtest.json"
with open(input_file, "r", encoding="utf-8") as file:
    data = json.load(file)

# CSV output file
output_file = "output.csv"

# Open CSV file for writing
with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.writer(csvfile)
    # Write CSV header
    csv_writer.writerow(['Message_ID', 'Country', 'City', 'Province', 'County', 'Communes', 'Latitude', 'Longitude', 'Text'])

    # Process messages
    for message in data["messages"]:
        # Extract fields
        message_id = message.get("id")
        translated_text = message.get("text_entities", [{}])[0].get("TRANSLATED_TEXT", "")
        translation = message.get("TRANSCRIPTION_TRANSLATION", {}).get("translation", "")
        video_summary = message.get("VIDEO_SUMMARY", "")
        photo_analysis = message.get("PHOTO_ANALYSIS", "")

        # Clean data (remove commas)
        translated_text = remove_commas(translated_text)
        translation = remove_commas(translation)
        video_summary = remove_commas(video_summary)
        photo_analysis = remove_commas(photo_analysis)

        # Prepare system prompt and user prompt for OpenAI
        system_prompt = (
            "Determine if the text contains any geographical references. Each text corresponds to a message id; "
            "some texts have the same message id. Return the result in this exact format (comma-separated): "
            "Message_ID,Country,City,Province,County,Communes,Latitude,Longitude,Text. Use 'null' for any missing values. "
            "For text, return the whole text the geographical reference was found in. "
            "If a location is identified in the text, numerical coordinates for latitude and longitude must be provided for the location referenced. "
            "Do not return extra characters or newlines."
        )
        user_prompt = f"You are an expert in identifying geographic locations and references in English-language texts. Identify if there are any geographical references from the following text:\n\n{translated_text}\n\n{translation}\n\n{video_summary}\n\n{photo_analysis}"

        # Call OpenAI API
        location_info = call_openai_api(system_prompt, user_prompt)

        # Default to null for location fields
        country, city, province, county, communes, latitude, longitude = "null", "null", "null", "null", "null", "null", "null"

        # Parse location info if available
        if location_info:
            fields = location_info.split(",")
            if len(fields) == 9:
                # Extract fields safely
                country, city, province, county, communes, latitude, longitude = map(str.strip, fields[1:8])
                text = ",".join(fields[8:]).strip()
            else:
                text = translated_text
        else:
            text = translated_text

        # Replace empty strings with 'null'
        text = text or "null"

        # Write to CSV
        csv_writer.writerow([message_id, country, city, province, county, communes, latitude, longitude, text])

print(f"Processing complete. Results saved to {output_file}.")