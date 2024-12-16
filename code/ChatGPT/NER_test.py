#https://cookbook.openai.com/examples/named_entity_recognition_to_enrich_text
#C:\Users\BrianT\AppData\Local\Programs\Python\Python310\openai-env\Scripts
import os
from openai import OpenAI
#import openai  
from dotenv import load_dotenv
import json
from datetime import datetime

import wikipedia
import logging

labels = [
    "person",      # people, including fictional characters
    "fac",         # buildings, airports, highways, bridges
    "org",         # organizations, companies, agencies, institutions
    "gpe",         # geopolitical entities like countries, cities, states
    "loc",         # non-gpe locations
    "product",     # vehicles, foods, appareal, appliances, software, toys 
    "event",       # named sports, scientific milestones, historical events
    "work_of_art", # titles of books, songs, movies
    "law",         # named laws, acts, or legislations
    "language",    # any named language
    "date",        # absolute or relative dates or periods
    "time",        # time units smaller than a day
    "percent",     # percentage (e.g., "twenty percent", "18%")
    "money",       # monetary values, including unit
    "quantity",    # measurements, e.g., weight or distance
]

#The system message (prompt) sets the assistant's behavior by defining its desired persona and task. We also delineate the specific set of entity labels we aim to identify.
def system_message(labels):
    return f"""
You are an expert in Natural Language Processing. Your task is to identify common Named Entities (NER) in a given text.
The possible common Named Entities (NER) types are exclusively: ({", ".join(labels)})."""

#Assistant messages usually store previous assistant responses. However, as in our scenario, they can also be crafted to provide examples of the desired behavior.
def assisstant_message():
    return f"""
EXAMPLE:
    Text: 'In Germany, in 1440, goldsmith Johannes Gutenberg invented the movable-type printing press. His work led to an information revolution and the unprecedented mass-spread / 
    of literature throughout Europe. Modelled on the design of the existing screw presses, a single Renaissance movable-type printing press could produce up to 3,600 pages per workday.'
    {{
        "gpe": ["Germany", "Europe"],
        "date": ["1440"],
        "person": ["Johannes Gutenberg"],
        "product": ["movable-type printing press"],
        "event": ["Renaissance"],
        "quantity": ["3,600 pages"],
        "time": ["workday"]
    }}
--"""

#The user message provides the specific text for the assistant task:
def user_message(text):
    return f"""
TASK:
    Text: {text}
"""

#@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(5))
def find_link(entity: str):
    """
    Finds a Wikipedia link for a given entity.
    """
    try:
        titles = wikipedia.search(entity)
        if titles:
            # naively consider the first result as the best
            page = wikipedia.page(titles[0])
            return page.url
    except (wikipedia.exceptions.WikipediaException) as ex:
        logging.error(f'Error occurred while searching for Wikipedia link for entity {entity}: {str(ex)}')

    return None

def find_all_links(label_entities:dict) -> dict:
    """ 
    Finds all Wikipedia links for the dictionary entities in the whitelist label list.
    """
    whitelist = ['event', 'gpe', 'org', 'person', 'product', 'work_of_art']
    
    return {e: find_link(e) for label, entities in label_entities.items() 
                            for e in entities
                            if label in whitelist}

def enrich_entities(text: str, label_entities: dict) -> str:
    """
    Enriches text with knowledge base links.
    """
    entity_link_dict = find_all_links(label_entities)
    logging.info(f"entity_link_dict: {entity_link_dict}")
    
    for entity, link in entity_link_dict.items():
        text = text.replace(entity, f"[{entity}]({link})")

    return text

#we need to define the corresponding JSON schema to be passed to the functions parameter:
def generate_functions(labels: dict) -> list:
    return [
        {
            "name": "enrich_entities",
            "description": "Enrich Text with Knowledge Base Links",
            "parameters": {
                "type": "object",
                    "properties": {
                        "r'^(?:' + '|'.join({labels}) + ')$'": 
                        {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "additionalProperties": False
            },
        }
    ]





#@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(5))
def run_openai_task(labels, text):
    messages = [
          {"role": "system", "content": system_message(labels=labels)},
          {"role": "assistant", "content": assisstant_message()},
          {"role": "user", "content": user_message(text=text)}
      ]

#chat.completions.create\
#response = openai.ChatCompletion.create(

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0613",
        messages=messages,
        functions=generate_functions(labels),
        function_call={"name": "enrich_entities"}, 
        temperature=0,
        frequency_penalty=0,
        presence_penalty=0,
    )

    #nothing in content?\
    #response_message = response.choices[0].message.content
    #this has everything
    response_message = response.choices[0].message
    
    available_functions = {"enrich_entities": enrich_entities}  
    #function_name = response_message["function_call"]["name"]
    #the name of function  that should be used based on what was returned 
    function_name = response_message.function_call  
    
    function_to_call = available_functions[function_name.name] 
    logging.info(f"function_to_call: {function_to_call}")

    #function_args = json.loads(response_message["function_call"]["arguments"])
    #this is where the 'magic' from chatGPT is coming back - arguments created by ChatGPT to be plugged into a functions
    function_args = json.loads(response_message.function_call.arguments )
    logging.info(f"function_args: {function_args}")

    function_response = function_to_call(text, function_args)

    return {"model_response": response, 
            "function_response": function_response}
    




load_dotenv()
MY_KEY = os.getenv('OPENAI_API_KEY')



client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key=MY_KEY,
)


text = """The Beatles were an English rock band formed in Liverpool in 1960, comprising John Lennon, Paul McCartney, George Harrison, and Ringo Starr."""
result = run_openai_task(labels, text)
print(result)