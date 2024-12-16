'''
use ChatGPT to conduct thematic and topic analysis  
'''

#C:\Users\BrianT\AppData\Local\Programs\Python\Python310\openai-env\Scripts
import os
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

THEMATIC_ANALYSIS_OUTPUT = "thematic_analysis_Oct_2023.csv"
THEMATIC_ANALYSIS_OUTPUT_FIELDS = ['MESSAGE_ID', 'THEMES', 'TOPICS'] 

#TODO - move this to a seperate module
#MESSAGE_ID,MESSAGE_FULL_DATE,MESSAGE_DATE_MONTH_DAY_YEAR,MESSAGE_DATE_HOUR_SEC,MESSAGE_FILE_NAME,MESSAGE_SOURCE_LANGUAGE,MESSAGE_DETECTED_LANGUAGE,MESSAGE_TRANSLATED_ENG
MESSAGE_DOCUMENTATION_FIELDS =  ['MESSAGE_ID', 'MESSAGE_FULL_DATE', 'MESSAGE_DATE_MONTH_DAY_YEAR',	'MESSAGE_DATE_HOUR_SEC', 'MESSAGE_FILE_NAME','MESSAGE_SOURCE_LANGUAGE','MESSAGE_DETECTED_LANGUAGE','MESSAGE_TRANSLATED_ENG']
MESSAGE_ID_FIELD = "MESSAGE_ID"
MACHINE_ENG_FIELD = "MESSAGE_TRANSLATED_ENG"



#Error logging for large data processing
ERROR_LOG_FILEPATH = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Full/indiv_messages/error_log.csv"
ERROR_LOG_FIELDS =  ['MESSAGE_ID','ERROR']


#first round of prompts - 1 Feb
PROMPT_PART_1 = "Conduct a thematic analysis of this text <start> " 
PROMPT_PART_2 = " <end>. Return back two things."

PROMPT_PART_3 = "The first is your general thematic assesment of text that was between the <start> and <end> tags. The second are any topics you found in  the text that was between the <start> and <end> tags. "

PROMPT_PART_4 = "Put the two items you return into a JSON structure. Your general thematic assesment of text that was between the <start> and <end> tags placed inside a JSON tag named theme. Any topics you found in the text that was between the <start> and <end> tags inside a JSON tag named topic."

PROMPT_PART_5 = "Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified."

MOTIVATION_MESSAGE = "You are a skilled humanitarian analyst who is an expert in conducting thematic analysis of English language texts."

#result JSON tags
RESULT_theme = "theme"
RESULT_topic = "topic"

def LogError(MessageID, Error):
   with open(ERROR_LOG_FILEPATH, 'a',newline='', encoding="utf-8") as f_object:

      print("logging error") 
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
test_loop = 100
current_interation = 0
short_test = False

#open messages stored in CSV  file
with open(ROOT_DIRECTORY + MESSAGE_DOCUMENTATION_FILE,'r',newline='',encoding="utf-8-sig") as csvfile:

  reader = csv.DictReader(csvfile)
  #loop through the individual messages
  for row in reader:
    print(row[MESSAGE_ID_FIELD],row[MACHINE_ENG_FIELD])

    #get the ChatGPT-translated message from the CSV
    message_id = row[MESSAGE_ID_FIELD]
    message_text = row[MACHINE_ENG_FIELD]
    
    #send the extracted text to chatGPT for translation
    use_CHAT_GPT = True

    if use_CHAT_GPT:

      print ("sending message")
      if short_test:
        current_interation += 1  
      
    #{"role": "user", "content": "Examine the contexts of this text: " + content + REPORT_FORMAT_MESSAGE_HTML + HEALTH_MESSAGE + GEOCODE_MESSAGE}
      completion = client.chat.completions.create(
      model="gpt-3.5-turbo-0613",
      messages=[
        {"role": "system", "content": MOTIVATION_MESSAGE},
        {"role": "user", "content": PROMPT_PART_1 + message_text + PROMPT_PART_2 + PROMPT_PART_3 + PROMPT_PART_4 + PROMPT_PART_5}
        ]
      )

      #final_result = completion.choices[0].message
      final_result = completion.choices[0].message.content

      
      try:

        result_JSON = json.loads(final_result)
        ChatGPTOutput_Detected_Theme = result_JSON[RESULT_theme]
        ChatGPTOutput_Detected_Topic = result_JSON[RESULT_topic]

        print(final_result)
      
      #json.decoder.JSONDecodeError
      except Exception as inst:
        LogError(message_id,inst)
        print("error")
        continue
     
      #write the thematic analysis results out
      #THEMATIC_ANALYSIS_OUTPUT_FIELDS = ['MESSAGE_ID', 'THEMES', 'TOPICS'] 
      with open(ROOT_DIRECTORY + THEMATIC_ANALYSIS_OUTPUT, 'a',newline='', encoding="utf-8") as f_object:
    

        dictwriter_object = DictWriter(f_object, fieldnames=THEMATIC_ANALYSIS_OUTPUT_FIELDS)
        THEMATIC_ANALYSIS_OUTPUT_dict = {THEMATIC_ANALYSIS_OUTPUT_FIELDS[0]: message_id, 
                                    THEMATIC_ANALYSIS_OUTPUT_FIELDS[1]: ChatGPTOutput_Detected_Theme,
                                    THEMATIC_ANALYSIS_OUTPUT_FIELDS[2]: ChatGPTOutput_Detected_Topic}
        dictwriter_object.writerow(THEMATIC_ANALYSIS_OUTPUT_dict)

        # Close the file object
        f_object.close()

        #for short testing when do not want to go through everything
      if short_test:
        if (current_interation == test_loop):
          break
    #if (current_text != ''):
  #for row in reader:        




print("done")







