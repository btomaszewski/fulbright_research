#Update – forgot to include date in classification output! Needed for linking to other data sets

import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import re
from datetime import datetime
import csv
from csv import DictWriter
import pandas as pd

# JSON Indexes and Keys
JSON_MESSAGES = "messages"
TEXT_ENTITIES = "text_entities"
TYPE_MESSAGE = "type"

# File Paths
ROOT_DIRECTORY = 'C:/Users/BrianT/RIT/TEACHING/IGME_772_Geovisualization/Lectures/Week_4_Tableau/2025_dev/Thematic_Analysis/'
MESSAGE_DOCUMENTATION_FILE = "TG_messages_2022.csv"
CATEGORIES_FILE = "categories.csv"

THEMATIC_ANALYSIS_OUTPUT = "thematic_analysis_2025.csv"
THEMATIC_ANALYSIS_OUTPUT_FIELDS = ['MESSAGE_ID', 'CATEGORY', 'SUBCATEGORY', 'CONFIDENCE']

ERROR_LOG_FILEPATH = ROOT_DIRECTORY + "error_log.csv"
ERROR_LOG_FIELDS = ['MESSAGE_ID', 'ERROR']

# Prompt Constants
MOTIVATION_MESSAGE = "You are a skilled humanitarian analyst who is an expert in classifying English language texts."

RESULT_category = "category"
RESULT_subcategory = "subcategory"
RESULT_confidence = "confidence"

# Load API Key
load_dotenv()
MY_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=MY_KEY)

# Load categories from CSV
def load_categories(csv_file):
    df = pd.read_csv(csv_file)
    return df

# Create classification prompt
def create_classification_prompt(df, message):
    prompt = "You are an AI assistant designed to classify social media messages.\n\n"
    prompt += "Here are the categories, subcategories, and their associated keywords:\n\n"
    
    for _, row in df.iterrows():
        prompt += f"Category: {row['Category']}\n"
        prompt += f"Subcategory: {row['Subcategory']}\n"
        prompt += f"Keywords: {row['Keywords']}\n\n"
    
    prompt += f"Classify the following message into one of these categories and subcategories. If it doesn't fit, respond with 'Unknown'." 
    
    prompt += f" followed by your best guess of one word as to what a category and subcategory may be.  You must provide only one word as to your guess of the category and subcategory if it does not fit the categories and subcategories that were provided."
    
    prompt += f"Also, provide a confidence score from 0 to 1.\n\n"
    prompt += f"Message: \"{message}\"\n\n"
    prompt += (
    "Return ONLY a valid JSON object. "
    "Do not include any explanations, backticks, or formatting instructions. "
    "Output must strictly follow this format:\n"
    "{\n"
    "    \"category\": \"CategoryName\",\n"
    "    \"subcategory\": \"SubcategoryName\",\n"
    "    \"confidence\": 0.85\n"
    "}"
)

    
    return prompt

# Error Logging
def LogError(MessageID, Error):
    with open(ERROR_LOG_FILEPATH, 'a', newline='', encoding="utf-8") as f_object:
        dictwriter_object = DictWriter(f_object, fieldnames=ERROR_LOG_FIELDS)
        dictwriter_object.writerow({ERROR_LOG_FIELDS[0]: MessageID, ERROR_LOG_FIELDS[1]: str(Error)})

# ChatGPT Classification
def classify_message(message, df):
    prompt = create_classification_prompt(df, message)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": MOTIVATION_MESSAGE},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        temperature=0.3
    )
    
    result_json = clean_and_validate_json(response.choices[0].message.content)

    return result_json



def clean_and_validate_json(response_text):
    """
    Cleans and validates JSON output, removing any extra formatting like backticks or markdown.
    """
    try:
        # Step 1: Remove Markdown backticks and 'json' label
        cleaned_text = re.sub(r'```json\n?|```', '', response_text, flags=re.IGNORECASE).strip()

        # Step 2: Extract JSON object using regex (in case of extra text)
        json_match = re.search(r'{.*}', cleaned_text, re.DOTALL)
        if json_match:
            json_text = json_match.group()
        else:
            raise ValueError("No valid JSON object found in the response.")

        # Step 3: Validate the JSON
        parsed_json = json.loads(json_text)
        
        # Step 4: Check if required keys exist
        required_keys = ["category", "subcategory", "confidence"]
        if not all(key in parsed_json for key in required_keys):
            raise ValueError("Missing required keys in JSON.")

        return parsed_json

    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error cleaning JSON: {e}")
        # Return a fallback structure if invalid
        return {
            "category": "Unknown",
            "subcategory": "Unknown",
            "confidence": 0.0
        }

# Load categories from CSV
categories_df = load_categories(ROOT_DIRECTORY + CATEGORIES_FILE)

# Processing messages 
with open(ROOT_DIRECTORY + MESSAGE_DOCUMENTATION_FILE, 'r', newline='', encoding="utf-8-sig") as csvfile:
    reader = csv.DictReader(csvfile)
    
    for row in reader:
        message_id = row['MESSAGE_ID']
        message_text = row['MESSAGE_TRANSLATED_ENG']

        try:
            classification_result = classify_message(message_text, categories_df)
            
            detected_category = classification_result.get(RESULT_category, "Unknown")
            detected_subcategory = classification_result.get(RESULT_subcategory, "Unknown")
            confidence_score = classification_result.get(RESULT_confidence, 0.0)

            # Write classification results
            with open(ROOT_DIRECTORY + THEMATIC_ANALYSIS_OUTPUT, 'a', newline='', encoding="utf-8") as f_object:
                dictwriter_object = DictWriter(f_object, fieldnames=THEMATIC_ANALYSIS_OUTPUT_FIELDS)
                output_data = {
                    'MESSAGE_ID': message_id,
                    'CATEGORY': detected_category,
                    'SUBCATEGORY': detected_subcategory,
                    'CONFIDENCE': confidence_score
                }
                dictwriter_object.writerow(output_data)

            print(f"Processed Message ID: {message_id}")

        except Exception as error:
            LogError(message_id, error)
            print(f"Error processing Message ID: {message_id} - {error}")
            continue

print("Classification completed.")
