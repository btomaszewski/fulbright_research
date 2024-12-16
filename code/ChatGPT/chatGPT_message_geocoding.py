'''
use ChatGPT to geocode messages  
'''

#C:\Users\BrianT\AppData\Local\Programs\Python\Python310\openai-env\Scripts
import os
import re
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime
import csv
from csv import DictWriter


#JSON Indexes and Keys
JSON_MESSAGES = "messages"
TEXT_ENTITIES = "text_entities"
TYPE_MESSAGE = "type" #check what kind if message it is - service vs. message


ROOT_DIRECTORY =  "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/analysis_March_2024/" 

MESSAGE_DOCUMENTATION_FILE = "TG_messages_Oct_2023.csv" 

GEOCODING_OUTPUT = "geocoding_Oct_2023.csv"
GEOCODING_OUTPUT_FIELDS = ['MESSAGE_ID','MESSAGE_TEXT','GEONAME','TYPE','X','Y']


THEMATIC_ANALYSIS_OUTPUT_FIELDS = ['MESSAGE_ID', 'THEMES', 'TOPICS'] 

#TODO - move this to a seperate module
#MESSAGE_ID,MESSAGE_FULL_DATE,MESSAGE_DATE_MONTH_DAY_YEAR,MESSAGE_DATE_HOUR_SEC,MESSAGE_FILE_NAME,MESSAGE_SOURCE_LANGUAGE,MESSAGE_DETECTED_LANGUAGE,MESSAGE_TRANSLATED_ENG
MESSAGE_DOCUMENTATION_FIELDS =  ['MESSAGE_ID', 'MESSAGE_FULL_DATE', 'MESSAGE_DATE_MONTH_DAY_YEAR',	'MESSAGE_DATE_HOUR_SEC', 'MESSAGE_FILE_NAME','MESSAGE_SOURCE_LANGUAGE','MESSAGE_DETECTED_LANGUAGE','MESSAGE_TRANSLATED_ENG']
MESSAGE_ID_FIELD = "MESSAGE_ID"
MACHINE_ENG_FIELD = "MESSAGE_TRANSLATED_ENG"



#Error logging for large data processing
ERROR_LOG_FILEPATH = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Full/indiv_messages/error_log.csv"
ERROR_LOG_FIELDS =  ['MESSAGE_ID','ERROR']


#first round of prompts 

PROMPT_PART_1 = "Please determine if this English language text contains any geographical references. <start> " 

PROMPT_PART_2 = " <end>. "

MOTIVATION_MESSAGE = "You are a skilled humanitarian analyst who is an expert in conducting identifying geographic locations in English language texts."

def extract_json_from_string(text):
    # Find the index of the first '{'
    start_index = text.find('{')
    if start_index == 0:
      #no need to further search
      return text

    if start_index == -1:
        return None  # No JSON found
    
    # Find the index of the last '}'
    end_index = text.rfind('}')
    if end_index == -1:
        return None  # No JSON found
    
    # Extract the JSON substring
    print("performing JSON extraction")
    json_string = text[start_index:end_index+1]
    return json_string


def WriteGeoCodeData (message_id, InputGEOJSON, message_text):

  #clean up the message: remove commas, \ other items

  #In this regular expression [\\,], the square brackets denote a character class, meaning it matches any one of the characters inside it. The backslash \ is escaped as \\ because it's a special character in regular expressions. This pattern matches either a backslash or a comma. The re.sub() function then replaces all occurrences of these characters with an empty string, effectively removing them from the message_text.

  clean_message = re.sub(r'[\\,]', '', message_text) 

  #go through th geoJSON and parse out the contents
  result_GeoJSON = json.loads(InputGEOJSON)
  features = result_GeoJSON["features"]

  try:

    for feature in features:

      #sometimes name does not come back?
      name = feature["properties"]["name"]
      geo_type = feature["properties"]["type"]

      if not name.strip():  # Using strip() to remove leading and trailing whitespace
        name = "UNKNOWN"

      #todo - check for NULL coordinates
      if feature['geometry'] is None:
        continue  # Skip this iteration if geometry is null
      
      #check to see if the coordinates are missing
      #avoid not enough values to unpack (expected 2, got 0) error
      #"coordinates": []
      
      coordinates = feature["geometry"].get("coordinates")
      
      if coordinates is None:
        print("Coordinates are not available")
        continue
      elif not isinstance(coordinates, list):
        print("Invalid coordinates format")
        continue
      elif len(coordinates) < 2:
        print("Insufficient number of coordinates")
        continue
      else:
        # At least two numeric values exist in coordinates
        print("Coordinates:", coordinates)
      
      
      
      
      
      # Splitting the coordinates into individual numbers tuple unpacking directly unpack values from a tuple into separate variables by assigning the tuple to variables separated by commas
      #sometimes they were backwards? TODO fix
      lon, lat  = coordinates
      if lon == 0 or lat == 0:
        print("lat or long  is equal to 0")
        #skip processing this item, no 0,0 items to be geocoded
        continue

      #strange problem with the coordinates switched sometimes
      #assume for this case study that that lat > long
      if (lon > lat):
        print ('switched coords')
        lat_temp = lon
        long_temp = lat
        lon = long_temp
        lat = lat_temp 

      print (name + ' lat:' + str(lat) + ' long:' + str(lon) )

      #write the geooding  results out to CSV for X Y table
      #GEOCODING_OUTPUT_FIELDS = ['MESSAGE_ID','MESSAGE_TEXT','GEONAME','TYPE','X','Y']
      GEOCODE_data_dict = {GEOCODING_OUTPUT_FIELDS[0]: message_id, 
                                          GEOCODING_OUTPUT_FIELDS[1]: clean_message, 
                                          GEOCODING_OUTPUT_FIELDS[2]: name,
                                          GEOCODING_OUTPUT_FIELDS[3]: geo_type,  
                                          GEOCODING_OUTPUT_FIELDS[4]: lon, 
                                          GEOCODING_OUTPUT_FIELDS[5]: lat}


      with open(ROOT_DIRECTORY + GEOCODING_OUTPUT, 'a',newline='', encoding="utf-8") as f_object:

        dictwriter_object = DictWriter(f_object, fieldnames=GEOCODING_OUTPUT_FIELDS)
          
              # Pass the dictionary as an argument to the Writerow()
        dictwriter_object.writerow(GEOCODE_data_dict)

        # Close the file object
        f_object.close()

    #for feature in features:
  except Exception as inst:
    print(inst)
    print("geo code processing error")
    #continue

def LogError(MessageID, Error):
   with open(ERROR_LOG_FILEPATH, 'a',newline='', encoding="utf-8") as f_object:

      print("logging general error") 
      dictwriter_object = DictWriter(f_object, fieldnames=ERROR_LOG_FIELDS)
      ERROR_LOG_dict = {ERROR_LOG_FIELDS[0]:MessageID, ERROR_LOG_FIELDS[1]:Error}

      # Pass the dictionary as an argument to the Writerow()
      dictwriter_object.writerow(ERROR_LOG_dict)

      # Close the file object
      f_object.close()

#connect to ChatGPT
load_dotenv()
MY_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key=MY_KEY,
)

#use for smaller tests
test_loop = 50
current_interation = 0
short_test = False

#read external prompt
script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the Python script
file_path = os.path.join(script_dir, 'chatGPT_geocode_GeoJSON_format.txt')  # Construct the full path to the text file
    
with open(file_path, 'r',encoding="utf-8-sig") as file:
  geocode_prompt = file.read()
  file.close

END_MESSAGE = PROMPT_PART_2 + geocode_prompt

#open messages stored in CSV  file
with open(ROOT_DIRECTORY + MESSAGE_DOCUMENTATION_FILE,'r',newline='',encoding="utf-8-sig") as csvfile:

  reader = csv.DictReader(csvfile)
  #loop through the individual messages
  for row in reader:
    #print(row[MESSAGE_ID_FIELD],row[MACHINE_ENG_FIELD])

    #get the ChatGPT-translated message from the CSV
    message_id = row[MESSAGE_ID_FIELD]
    message_text = row[MACHINE_ENG_FIELD]
    
    #send the extracted text to chatGPT for translation
    use_CHAT_GPT = True

    if use_CHAT_GPT:

      #print ("sending message")
      if short_test:
        current_interation += 1  
      
    #{"role": "user", "content": "Examine the contexts of this text: " + content + REPORT_FORMAT_MESSAGE_HTML + HEALTH_MESSAGE + GEOCODE_MESSAGE}
      completion = client.chat.completions.create(
      model="gpt-3.5-turbo-0613",
      messages=[
        {"role": "system", "content": MOTIVATION_MESSAGE},
        {"role": "user", "content": PROMPT_PART_1  + message_text + END_MESSAGE}
        ]
      )

      final_result = completion.choices[0].message.content

      
      try:

        print(final_result)  

        #
        if not "none" in final_result.lower():

          # Search for JSON-like structure within the response
          #sometime a verbose message comes with the json, jut get the JSON
          # Extract JSON from the text string
          json_data = extract_json_from_string(final_result)
          if json_data:
            print(json_data)
            WriteGeoCodeData (message_id,json_data,message_text)  
          else:
            print("No JSON found in the string.")
 
        else:
          print("none found")
      #json.decoder.JSONDecodeError
      except Exception as inst:
        LogError(message_id,inst)
        print("error")
        continue
     
        #for short testing when do not want to go through everything
      if short_test:
        if (current_interation == test_loop):
          break
    #if (current_text != ''):
  #for row in reader:        

print("done")







