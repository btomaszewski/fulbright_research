import os
import json
import csv
import pandas as pd
from aiLoader import loadAI
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError
from geopy.extra.rate_limiter import RateLimiter

client = loadAI()


# Function to remove commas from a string
def remove_commas(text):
    return text.replace(",", "") if text else ""

# Function to interact with OpenAI API
def call_openai_api(system_prompt, user_prompt):
    try:
        response = client.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

# Load JSON data
def load_json_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return None

# Write data to CSV
def write_to_csv(filepath, data, headers):
    with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(headers)
        csv_writer.writerows(data)

# Main processing function
def process_messages(input_file, output_file):
    data = load_json_file(input_file)
    if not data:
        return

    # Define system prompt for OpenAI
    system_prompt = (
        "You are an expert in identifying geographic locations and references in English-language texts. "
        "Determine if the text contains any geographical references. Return the result in this exact format (comma-separated): "
        "Message_ID,Lankmark,Country,City,County,Address,Text. Some values may be null."
    )

    results = []

    for message in data.get("messages", []):
        # Extract fields
        message_id = message.get("id", "null")
        translated_text = remove_commas(message.get("text_entities", [{}])[0].get("TRANSLATED_TEXT", ""))
        translation = remove_commas(message.get("TRANSCRIPTION_TRANSLATION", {}).get("translation", ""))
        video_summary = remove_commas(message.get("VIDEO_SUMMARY", ""))
        photo_analysis = remove_commas(message.get("PHOTO_ANALYSIS", ""))

        # Prepare user prompt
        user_prompt = f"{translated_text} {translation} {video_summary} {photo_analysis}".strip()

        # Call OpenAI API
        location_info = call_openai_api(system_prompt, user_prompt)

        # Parse API response
        if location_info:
            fields = location_info.split(",")
            if len(fields) >= 7:
                landmark, country, city, county, address, text = map(
                    lambda x: x.strip() or 'null', fields[1:7]
                )
            else:
                print(f"Malformed response: {location_info}")
                landmark = country = city = county = address = text = 'null'
        else:
            landmark = country = city = county = address = text = 'null'

        # Append results
        results.append([message_id, landmark, country, city, county, address, text])

    # Write results to CSV
    headers = ['Message_ID', 'Lankmark', 'Country', 'City', 'County', 'Address', 'Text']
    write_to_csv(output_file, results, headers)

# Geocode data with GeoPy
def geocode_data(input_csv, output_csv):
    df = pd.read_csv(input_csv, sep=",")

    # Create query column
    df['query'] = df[['Lankmark', 'Country', 'City', 'County', 'Address']].apply(
        lambda x: " ".join(x.dropna().astype(str)).strip(), axis=1
    )

    # Initialize geolocator with rate limiter
    geolocator = Nominatim(user_agent="myApp")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    # Add lat/long columns
    df['location_lat'] = ""
    df['location_long'] = ""
    df['location_address'] = ""

    for i in df.index:
        try:
            location = geocode(df['query'][i])
            if location:
                df.loc[i, 'location_lat'] = location.latitude
                df.loc[i, 'location_long'] = location.longitude
                df.loc[i, 'location_address'] = location.address
            else:
                raise GeopyError("No location found")
        except GeopyError as e:
            print(f"Geopy error for index {i}: {e}")

    # Write updated data to new CSV
    df.to_csv(output_csv, index=False)

if __name__ == "__main__":
    # File paths
    input_json = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/processedJson/resultProcessed.json"
    intermediate_csv = "output3.csv"
    final_csv = "geopy_data.csv"

    # Process messages and geocode
    process_messages(input_json, intermediate_csv)
    geocode_data(intermediate_csv, final_csv)

    print(f"Processing complete. Output saved to {final_csv}")



'''
import json
import csv
from aiLoader import loadAI
client = loadAI()

def send_to_openai_with_system_prompt(text, system_prompt):
    try:
        # Create a list of messages for the OpenAI API, including the system message
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        # Call the OpenAI API
        response = client.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Or the model you are using
            messages=messages,
            max_tokens=1000  # You can adjust based on the text length
        )
        
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Function to handle each of the relevant fields and log output to CSV
def process_text_and_log_to_csv(json_data, system_prompt, csv_filename):
    results = []
    
    for message in json_data.get("messages", []):
        analysis_row = {}

        # Process VIDEO_SUMMARY
        if "VIDEO_SUMMARY" in message:
            video_summary = message["VIDEO_SUMMARY"]
            analysis_row["VIDEO_SUMMARY"] = send_to_openai_with_system_prompt(video_summary, system_prompt)

        # Process PHOTO_ANALYSIS
        if "PHOTO_ANALYSIS" in message:
            photo_analysis = message["PHOTO_ANALYSIS"]
            analysis_row["PHOTO_ANALYSIS"] = send_to_openai_with_system_prompt(photo_analysis, system_prompt)

        # Process TRANSLATED_TEXT
        for entity in message.get("text_entities", []):
            if "TRANSLATED_TEXT" in entity:
                translated_text = entity["TRANSLATED_TEXT"]
                analysis_row["TRANSLATED_TEXT"] = send_to_openai_with_system_prompt(translated_text, system_prompt)

            if "translation" in entity:
                translation = entity["translation"]
                analysis_row["translation"] = send_to_openai_with_system_prompt(translation, system_prompt)

        # Process VIDEO_TRANSCRIPTION
        if "VIDEO_TRANSCRIPTION" in message:
            video_transcription = message["VIDEO_TRANSCRIPTION"]
            analysis_row["VIDEO_TRANSCRIPTION"] = send_to_openai_with_system_prompt(video_transcription, system_prompt)

        # Only add rows to the results if any analysis was made
        if analysis_row:
            results.append(analysis_row)

# Define your system prompt
system_prompt = """
You are an AI trained to analyze text critically and provide useful insights. Please process the following text and provide a detailed summary, explanation, or analysis based on the content. Respond clearly and concisely, with emphasis on important details.
"""

# Load the provided JSON data (replace 'your_file.json' with your actual file path)
with open('your_file.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Process the text and log the analysis to a CSV file
process_text_and_log_to_csv(data, system_prompt, 'ai_analysis_results.csv')
'''



