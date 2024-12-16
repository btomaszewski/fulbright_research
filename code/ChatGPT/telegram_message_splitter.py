'''
utlity to split telegram messages into indiviual files and do an inital translation  
'''

#C:\Users\BrianT\AppData\Local\Programs\Python\Python310\openai-env\Scripts
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime
from csv import DictWriter
from bs4 import BeautifulSoup

#JSON Indexes and Keys
JSON_MESSAGES = "messages"
TEXT_ENTITIES = "text_entities"
TYPE_MESSAGE = "type" #check what kind if message it is - service vs. message

TEXT_INDEX = 0
TEXT_KEY = "text"
ID = "id"
DATE_HUMAN = "date"
DATE_UNIX = "1704439766"

#INPUT_FILE_AND_PATH = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Sample/result.json" 

WORKING_DIRECTORY = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Operativniy_ZSU/"
INPUT_FILE  = "result.json" 

#OUTPUT_FILE_AND_PATH = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Full/indiv_messages/" 

OUTPUT_FILE_AND_PATH = WORKING_DIRECTORY + "TRANSLATED/"


#documentation file for messages and evaluationBLUE_eval/
#put template in place if using first  time
MESSAGE_DOCUMENTATION_FILE = "TRANSLATED/TG_Operativniy_ZSU_23_May_2024.csv" 

#MESSAGE_ID,MESSAGE_FULL_DATE,MESSAGE_DATE_MONTH_DAY_YEAR,MESSAGE_DATE_HOUR_SEC,MESSAGE_FILE_NAME,MESSAGE_SOURCE_LANGUAGE,MESSAGE_DETECTED_LANGUAGE,MESSAGE_TRANSLATED_ENG
MESSAGE_DOCUMENTATION_FIELDS =  ['MESSAGE_ID', 'MESSAGE_FULL_DATE', 'MESSAGE_DATE_MONTH_DAY_YEAR',	'MESSAGE_DATE_HOUR_SEC', 'MESSAGE_FILE_NAME','MESSAGE_SOURCE_LANGUAGE','MESSAGE_DETECTED_LANGUAGE','MESSAGE_TRANSLATED_ENG']

#Error logging for large data processing
#C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Full/indiv_messages/
ERROR_LOG_FILE = "error_log.csv"
ERROR_LOG_FIELDS =  ['MESSAGE_ID','ERROR']


#first round of prompts - 17 Jan
""" PROMPT_PART_1 = "Translate from Ukranian to English this text <start> " 
PROMPT_PART_2 = " <end>. Only return back your translation from Ukranian to English of text that was between the <start> and <end> tags and do not return any additional information."
 """

PROMPT_PART_1 = "Translate this text to English <start> " 
PROMPT_PART_2 = " <end>. Return back two things. The first is your translation to English of text that was between the <start> and <end> tags. The second is a one word description of the language of text that was between the <start> and <end> tags. "

PROMPT_PART_3 = "Put the two items you return into a JSON structure. Your translation to English of text that was between the <start> and <end> tags placed inside a JSON tag named  translation. Your one word description of the language of text that was between the <start> and <end> tags inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified."

#MOTIVATION_MESSAGE = "You are a skilled linguist who is an expert in doing translations between Ukrainian and English."

MOTIVATION_MESSAGE = "You are a skilled linguist who is an expert in identifying what language a given text is a doing translationsof that text to English."

def LogError(MessageID, Error):
   with open(WORKING_DIRECTORY + ERROR_LOG_FILE, 'a',newline='', encoding="utf-8") as f_object:

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
test_loop = 10
current_interation = 0
short_test = False

#open a locally stored json file
with open(WORKING_DIRECTORY + INPUT_FILE,encoding='utf-8' ) as f:
  #returns dict
  json_data = json.load(f)

#get messages array from JSON
message_data = json_data[JSON_MESSAGES]

#loop through the individual messages
for individual_message in message_data:

  #17 Jan - only process messages of type 'message'
  if (individual_message[TYPE_MESSAGE] == "message"):

    #get the plain text message from the current message
    current_text = individual_message[TEXT_ENTITIES]
    #only go forward with text messages
    #TODO - process pictures/audio 
    if (len(current_text) > 0): 

      #keep going 1710722897
      if int(individual_message[ID]) > 145786: 

        #TODO - current text is null, when a picture comes
        #TODO - convert list to dict?
        message_text = current_text[TEXT_INDEX][TEXT_KEY]

        #send the extracted text to chatGPT for translation
        use_CHAT_GPT = True

 

        if use_CHAT_GPT:

          print ("sending message")
          if short_test:
            current_interation += 1  
          
        #print (individual_message["id"])
    


    #{"role": "user", "content": "Examine the contexts of this text: " + content + REPORT_FORMAT_MESSAGE_HTML + HEALTH_MESSAGE + GEOCODE_MESSAGE}
        completion = client.chat.completions.create(
          model="gpt-3.5-turbo-0613",
          messages=[
            {"role": "system", "content": MOTIVATION_MESSAGE},
          {"role": "user", "content": PROMPT_PART_1 + message_text + PROMPT_PART_2 + PROMPT_PART_3}
          ]
        )

      #final_result = completion.choices[0].message
        final_result = completion.choices[0].message.content
      
        try:

          result_JSON = json.loads(final_result)
          ChatGPTOutput_Detected_Language = result_JSON["language"]
          ChatGPTOutput_ENG_Translated_Message = result_JSON["translation"]

          #print(final_result)
        
        #json.decoder.JSONDecodeError
        except Exception as inst:
          LogError(individual_message[ID],inst)
          print("error")
          continue
      

      ### 30 Jan 2024  probably not needed ***   

      #plug the ENG translation back into individual message JSON 
      #https://www.w3schools.com/python/python_ref_dictionary.asp
      #individual_message is DICT
        individual_message.update({'MESSAGE_ENG' : ChatGPTOutput_ENG_Translated_Message})

     
      
      #write out the individual message as a file
      # get current date and time
      #current_datetime = datetime.now().strftime("%Y%m%d%H%M%S")

      #use the message ID as the filename
        file_name = individual_message[ID]

        #make the DICT a string, replace ' with " for json
        string_individual_message = str(individual_message)
        final_json = string_individual_message.replace('\'', "\"")


        message_file_name =  str(individual_message[ID]) + ".json"
        
        #uncomment if needed to write indivudal files out
        #message_result = open( OUTPUT_FILE_AND_PATH + message_file_name, "w", encoding="utf-8")
        #message_result.write (final_json)
        #message_result.close()

        ## document message  in a CSV file ##
        #parse the date by day/month/second for showing message volumes
        #2024-01-05T13:30:41 > 2024-01-05 and  13:30:41 
        message_dates = str(individual_message[DATE_HUMAN]).split("T")


        #  combne the inventory and BLUE file outputs, do not need two seperate files 
        #documentation file for messages 
        #MESSAGE_DOCUMENTATION_FILE = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Indivual_Messages/TG_messages.csv" 
        #MESSAGE_ID,MESSAGE_FULL_DATE,MESSAGE_DATE_MONTH_DAY_YEAR,MESSAGE_DATE_HOUR_SEC,MESSAGE_FILE_NAME,MESSAGE_SOURCE_LANGUAGE,MESSAGE_DETECTED_LANGUAGE,MESSAGE_TRANSLATED_ENG
        #MESSAGE_DOCUMENTATION_FIELDS =  ['MESSAGE_ID', 'MESSAGE_FULL_DATE', 'MESSAGE_DATE_MONTH_DAY_YEAR',	'MESSAGE_DATE_HOUR_SEC', 'MESSAGE_FILE_NAME','MESSAGE_SOURCE_LANGUAGE','MESSAGE_DETECTED_LANGUAGE','MESSAGE_TRANSLATED_ENG']

        #0 MESSAGE_ID, 1 MESSAGE_FULL_DATE, 2 MESSAGE_DATE_MONTH_DAY_YEAR, 3 MESSAGE_DATE_HOUR_SEC, 4 MESSAGE_FILE_NAME, 5 MESSAGE_SOURCE_LANGUAGE, 6 MESSAGE_DETECTED_LANGUAGE, 7 MESSAGE_TRANSLATED_ENG   
        MESSAGE_DOCUMENTATION_dict = {MESSAGE_DOCUMENTATION_FIELDS[0]: individual_message[ID], 
                                      MESSAGE_DOCUMENTATION_FIELDS[1]: individual_message[DATE_HUMAN], 
                                      MESSAGE_DOCUMENTATION_FIELDS[2]: message_dates[0], 
                                      MESSAGE_DOCUMENTATION_FIELDS[3]: message_dates[1], 
                                      MESSAGE_DOCUMENTATION_FIELDS[4]: message_file_name,
                                      MESSAGE_DOCUMENTATION_FIELDS[5]: message_text,
                                      MESSAGE_DOCUMENTATION_FIELDS[6]: ChatGPTOutput_Detected_Language,
                                      MESSAGE_DOCUMENTATION_FIELDS[7]: ChatGPTOutput_ENG_Translated_Message}

        with open(WORKING_DIRECTORY + MESSAGE_DOCUMENTATION_FILE, 'a',newline='', encoding="utf-8") as f_object:  
      
          # Pass the file object and a list
          # of column names to DictWriter()
          # You will get a object of DictWriter
          dictwriter_object = DictWriter(f_object, fieldnames=MESSAGE_DOCUMENTATION_FIELDS)
      
          # Pass the dictionary as an argument to the Writerow()
          dictwriter_object.writerow(MESSAGE_DOCUMENTATION_dict)
    
          # Close the file object
          f_object.close()

        
          #for short testing when do not want to go through everything
          if short_test:
            if (current_interation == test_loop):
              break
    #if (current_text != ''):
  #if (individual_message[TEXT_ENTITIES] == "message"):        
#os.startfile('C:\Program Files (x86)\Google\Chrome\Application\chrome.exe ' + RESULTS_FOLDER + current_datetime + '.html')



print("done")







