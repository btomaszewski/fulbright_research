import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime

#JSON Indexes and Keys
JSON_DATA_TYPE_NEWS_REPORT = "news_report"

SOURCE_INDEX = 0
TITLE_INDEX = 1
DATE_INDEX = 2
TEXT_INDEX = 3
TEXT_KEY = "text"

SAMPLES_PATH = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/NLP/samples/" 
RESULTS_FOLDER = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/code/results/"

BASIC_MAP_MAKING_MESSAGE = "Identify the latitude and longitude coordinates of the following cities:  New York, London, Berlin, and Tokyo.  If you find multiple matches for the names of these cities, select the city with the largest population And latitude and longitude coordinates for that City. After you have identified the latitude and longitude coordinates of the cities, create an  HTML web page  that has a  world map of those cities shown using the ArcGIS Maps SDK for JavaScript code. Only return back the HTML webpage and no additional messages."

MESSAGE = "Return back one paragraph of text that summarizes the sentiment of the text in terms of how the Ukrainian situation is being perceived by the government of poland. "

REPORT_FORMAT_MESSAGE_HTML = "Return back a report formatted as a basic HTML file where answers to the following questions are indicated using <H2> tags:"


DEMOGRAPHICS_MESSAGE = " 1. any discussion of Ukrainians who have fled Ukraine after February 2022. If you do not find any discussion of Ukrainians who fled after 2022, Indicate in your report that there is no discussion of Ukrainians who fled Ukraine after 2022. 2. Any discussion of the age or gender of Ukrainian refugees you find in the text. if you do not find any discussion of the age or gender of Ukrainian refugees in the text indicating your report that there was no discussion of the age and gender of Ukrainian refugees in the report. 3. One paragraph summary of what the text is discussing and the sentiment of the text." 

HEALTH_MESSAGE = "1. any discussion of Ukrainians who needed to access healthcare. If you do not find any discussion of Ukrainians who needed to access healthcare , Indicate in your report that there is no discussion of Ukrainians who needed to access healthcare.2. Any discussion of Ukrainians who were unable to obtain healthcare.If you do not find any discussion of Ukrainians who were unable to obtain healthcare , indicate in your report that there is no discussion of Ukrainians who were unable to obtain healthcare. 3. any discussion of barriers to obtain healthcare. If you do not find any discussion of barriers to obtain healthcare indicate in your report that there is no discussion of barriers to obtain healthcare. 4. any discussion of mental health and psychosocial support issues. If you do not find any discussion of mental health and psychosocial support issues, Indicate in your report that there is no discussion of mental health and psychosocial support issues. 5. One paragraph summary of what the text is discussing and the sentiment of the text. "
#Use HTML font formatting to assign a  relevant color to the text that discusses the sentiment of the text. Chose a color that represents the mood of the text.



GEOCODE_MESSAGE = "  Conduct a named entity recognition of the text to find person names, organizations, locations, medical codes, time expressions, quantities, monetary values, or percentages. If you find any references to locations such as countries, cities or towns in the text, geocode those locations to latitude and longitude coordinates and return back a hyperlink with the name of the location in the HREF property of the hyperlink formatted as a  Google Maps URLs with the Location and the target property the hyperlink set  to the value new. For any person names, organizations, medical codes, time expressions, quantities, monetary values, or percentages you find, provide a hyperlink that is derived from a Google search that you do of that person names, organizations, medical codes, time expressions, quantities, monetary values, or percentages and you take the very first result you find from the Google search. The target property the hyperlink must be set  to the value new.  Place the results of the named entity recognation into an HTML table using <table> <tr> and <td> tags with the following column heading: entity, entity type, and link. Format the HTML so that all the cells have a border and of 1. Put all the links you created into the link column of the HTML table for each entity you found. You must return back an HTML table with all of the results of what you found in from named entity recognation including person names, organizations, locations, medical codes, time expressions, quantities, monetary values, or percentages. If there is some type of named entity you did not find, indicate what specific name to entities you did not find  in a paragraph below the HTML table."


#MOVEMENT_MESSAGE = " Identify refugee movements in this text and identify dates of the movements and assign latitude and longitude coordinates to any origin or destination country, state, city or location found in this text as geoJSON. You must return your results as geoJSON."

#MOVEMENT_MESSAGE = " Identify the following 1 - movements of people in this text, 2 - dates of the movements. Assign latitude and longitude coordinates to any movement origin or destination country, state, city or location found . Even if you find general movements between the two countries without specifying particular cities or locations, you must geocode the countries and return all of the results structured as GML."

#MOVEMENT_MESSAGE = "Identify  movements in this text and identify and assign latitude and longitude coordinates to any country, state, city or location found in this text as Geography Markup Language (GML) along with the dates of the movements and number of people. Only return Geography Markup Language (GML) and no additional comments."



#MOTIVATION_MESSAGE = "You will be reviewing text in the Polish language that discusses the movement of refugees even though the word Refugee may not be found. you are skilled and knowledgeable in understanding geographical locations referenced in text."
MOTIVATION_MESSAGE = "You are a skilled humanitarian information analyst with knowledge of multiple languages and concepts related to humanitarian multisector needs assessment like that done by the United Nations High Commissioner for Refugees (UNHCR) and the International Organization of Migration."

#You are going to read a document in Polish and will specifically be looking for geographical locations  written in the Polish language from around the world in the document."





#couldn't do this - create a pop-up message for each city that has the name of the city and its population.
#Use a graduated symbol representation to make the markers for each City relative to the population of that city.  
#can you teach it make maps?


load_dotenv()
MY_KEY = os.getenv('OPENAI_API_KEY')

#client = OpenAI()

client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key=MY_KEY,
)


SAMPLE_TO_USE = "health_sample_english.json"

#open a locally stored json file
with open(SAMPLES_PATH + SAMPLE_TO_USE ,encoding='utf-8' ) as f:
  #returns dict
  json_data = json.load(f)

#get data element from JSON
content_data = json_data[JSON_DATA_TYPE_NEWS_REPORT][TEXT_INDEX]
#get content of the data element - key/value pair
content = content_data[TEXT_KEY]
#print (content)


use_CHAT_GPT = True
if use_CHAT_GPT:

  print ("sending message")



#{"role": "user", "content": "Examine the contexts of this text: " + content + REPORT_FORMAT_MESSAGE_HTML + HEALTH_MESSAGE + GEOCODE_MESSAGE}
  completion = client.chat.completions.create(
    model="gpt-3.5-turbo-0613",
    messages=[
      {"role": "system", "content": MOTIVATION_MESSAGE},
     {"role": "user", "content": "Examine the contexts of this text: " + content + HEALTH_MESSAGE + REPORT_FORMAT_MESSAGE_HTML}
    ]
  )

  #final_result = completion.choices[0].message
  final_result = completion.choices[0].message.content

  print(final_result)

  #write out the message
  # get current date and time
  current_datetime = datetime.now().strftime("%Y%m%d%H%M%S")


  message_result = open( RESULTS_FOLDER + current_datetime + ".txt", "w", encoding="utf-8")
  message_result.write (str(final_result))
  message_result.close()

#os.startfile('C:\Program Files (x86)\Google\Chrome\Application\chrome.exe ' + RESULTS_FOLDER + current_datetime + '.html')