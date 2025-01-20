import csv
import json
from aiLoader import loadAI

client = loadAI()

PROMPT_PART_1 = "Conduct a geographical analysis of text messages to determine if the English language text contains any geographical references."
PROMPT_PART_2 = "Return back two things"
PROMPT_PART_3 = "First Determine the location for these translated texts between the <start> and <end> tags. The geographical references you will be looking for will likely be, but not limited to, cities and provinces in Poland or cities in Ukraine. There are no  limit to the number of locations you want to find in a single text. Return any Country, City, Province, County, communes derived from the text and provide a longitude and latitude. Provide Null values in none found. Second provide an geographical analysis of the text between the start  the <start> and <end> tags"
PROMPT_PART_4 = "Put the two items you return into a string formatted like a CSV file. The string will contain information for “Country”  City” “Province” “County” “communes” “Latitude” “Longitude”. The string format should create a new row for a message if the message contains more than one location."

MOTIVATION_MESSAGE = "You are a skilled humanitarian analyst who is an expert in conducting identifying geographic locations in English language texts."

json_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/processedJson/testgeo.json"
csv_output_file = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/GeocodingResults.csv"

GEOCODING_OUTPUT_FIELDS = ['Country', 'City', 'Province', 'County', 'Communes', 'Latitude', 'Longitude',]

def geolocate(text):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "system", "content": MOTIVATION_MESSAGE},
                {"role": "user", "content": PROMPT_PART_1 + text +PROMPT_PART_2 + PROMPT_PART_3 + PROMPT_PART_4}
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


'''
   #write the geooding  results out to CSV for X Y table
      #GEOCODING_OUTPUT_FIELDS = ['MESSAGE_ID','MESSAGE_TEXT','GEONAME','TYPE','X','Y']
      GEOCODE_data_dict = {GEOCODING_OUTPUT_FIELDS[0]: Message_ID, 
                                          GEOCODING_OUTPUT_FIELDS[1]: message, 
                                          GEOCODING_OUTPUT_FIELDS[2]: latitude,
                                          GEOCODING_OUTPUT_FIELDS[3]: Longitude,  
                                          GEOCODING_OUTPUT_FIELDS[4]: Country, 
                                          GEOCODING_OUTPUT_FIELDS[5]: City,
                                          GEOCODING_OUTPUT_FIELDS[6]: Provice,
                                          GEOCODING_OUTPUT_FIELDS[7]: District,
                                          GEOCODING_OUTPUT_FIELDS[8]: Communes} 


      with open(ROOT_DIRECTORY + GEOCODING_OUTPUT, 'a',newline='', encoding="utf-8") as f_object:

        dictwriter_object = DictWriter(f_object, fieldnames=GEOCODING_OUTPUT_FIELDS)
          
              # Pass the dictionary as an argument to the Writerow()
        dictwriter_object.writerow(GEOCODE_data_dict)

        # Close the file object
        f_object.close()

    #for feature in features:

'''