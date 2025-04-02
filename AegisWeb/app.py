from flask import Flask, render_template, request, send_file, send_from_directory, jsonify
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import gspread
from openai import OpenAI
import google_access
import pandas as pd
import os
import json
from dotenv import load_dotenv
from processJson import processJson

app = Flask(__name__)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
    
client = OpenAI(api_key=api_key)


@app.route('/')
def home():

    # prompts loads from  Google Sheets
    #prompt_data = pd.DataFrame(google_access.GetPromptsFromGoogleSheet)
    prompt_data = google_access.GetPromptsFromGoogleSheet()

    # Pass prompt data to the template to populate the selection box
    # Create a list of tuples from multiple columns
    prompt_items = list(zip(prompt_data['ID'], prompt_data['PROMPT_NAME']))
    
    ## Pass the list of tuples to the template, along with the length of the list
    return render_template('index.html', items=prompt_items, len=len)

#run the chat GPT open query
@app.route('/ask', methods=['POST'])
def ask():
    try:
        # Load dataset for context
        prompt_data = google_access.GetData()

        # User input
        user_input = request.form['user_input']

        # ChatGPT prompt
        prompt = (
            "Analyze the following CSV dataset of Telegram messages. "
            "The prompt between the <start> and <end> tags is user-generated. "
            "Use your analysis of the dataset to respond to the prompt.\n\n"
            f"{prompt_data}\n\n"
            f"<start>{user_input}<end>"
        )

        # Get AI response
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )

        return response.choices[0].message.content


    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ensure the /tmp/processing/rawJson directory exists
BASE_DIR = "/tmp/processing/rawJson"
os.makedirs(BASE_DIR, exist_ok=True)

@app.route("/upload-directory", methods=["POST"])
def upload_directory():
    if "files" not in request.files:
        return jsonify({"message": "No files provided"}), 400

    uploaded_files = request.files.getlist("files")

    # Save each file in the directory
    for file in uploaded_files:
        # Extract the relative path from the uploaded file
        relative_path = file.filename
        save_path = os.path.join(BASE_DIR, relative_path)

        # Create directories if they don't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Save the file
        file.save(save_path)

    return jsonify({
        "message": f"Uploaded {len(uploaded_files)} files successfully!"
    })

@app.route("/list-files", methods=["GET"])
def list_files():
    file_list = []
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            file_list.append(os.path.join(root, file))
    return jsonify({
        "files": file_list
})

@app.route("/process-json", methods=["POST"])
def process_json():
    try:
        # Get the directory name from the request
        data = request.get_json()
        directory_name = data.get('directory')

        if not directory_name:
            return jsonify({"message": "No directory name provided."}), 400

        # Path to the dataset in the /tmp directory
        dataset_path = os.path.join('/tmp/processing/rawJson', directory_name)

        if not os.path.exists(dataset_path):
            return jsonify({"message": f"Directory {directory_name} does not exist."}), 404

        # Call the processJson module
        processJson(dataset_path)

        # Return a success response
        return jsonify({"message": f"Dataset {directory_name} processed successfully."}), 200

    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@app.route('/upload-google-sheet', methods=['POST'])
def upload_google_sheet():
    print("upload function called")
    try:
        data = request.json
        file_path = data['filePath']
        print(file_path)

        # Credentials loaded from environment variables
        SHEET_ID = os.getenv('SHEET_ID')
        CLIENT_EMAIL = os.getenv('CLIENT_EMAIL')
        PRIVATE_KEY = os.getenv('PRIVATE_KEY').replace('\\n', '\n')

        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        creds = Credentials.from_service_account_info({
            "type": "service_account",
            "project_id": "your-project-id",
            "private_key_id": "your-private-key-id",
            "private_key": PRIVATE_KEY,
            "client_email": CLIENT_EMAIL,
            "client_id": "your-client-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "your-cert-url"
        }, scopes=SCOPES)

        try:
            client = gspread.authorize(creds)
            sheet = client.open_by_key(SHEET_ID)
            sheet_name = "allMessages"
        except Exception as auth_error:
            print("Google Sheets Authentication Failed:", str(auth_error))
        
        # Load or create the sheet
        try:
            worksheet = sheet.worksheet(sheet_name)
            print("sheet found")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="14")
            worksheet.append_row([
                "id", "date", "date_unixtime", "from", "text", "reply_id", "LANGUAGE", 
                "TRANSLATED_TEXT", "parent_category", "parent_confidence_score", 
                "child_category", "child_confidence_score", "locations_names", "locations_coordinates", "location_confidence"
            ])
            print("sheet created")

        try:
            # Load JSON file
            with open(file_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
            
            if 'messages' not in json_data or not isinstance(json_data['messages'], list):
                return jsonify({'error': 'Invalid JSON structure'}), 400
            
            messages = json_data['messages']
            if not messages:
                return jsonify({'error': 'No messages to upload'}), 400
            
            print("MESSAGES")
            print(messages)
        except Exception as json_load_error:
            print("Loading messages error:", json_load_error)
        
        try:
            new_rows = []
            for msg in messages:
                location_name, location_coords, location_confidence = "", "", ""
                if 'LOCATIONS' in msg and isinstance(msg['LOCATIONS'], list) and msg['LOCATIONS']:
                    first_location = msg['LOCATIONS'][0]
                    location_name = first_location.get('location', '')
                    if 'latitude' in first_location and 'longitude' in first_location:
                        location_coords = f"({first_location['latitude']}, {first_location['longitude']})"
                    if 'confidence' in first_location:
                        location_confidence = str(first_location.confidence)


                
                parent_category, parent_score, child_category, child_score = "", "", "", ""
                if 'CATEGORIES' in msg and isinstance(msg['CATEGORIES'], list) and msg['CATEGORIES']:
                    category_data = msg['CATEGORIES'][0].get('classification', {})
                    parent_category = category_data.get('parent_category', '')
                    parent_score = category_data.get('parent_confidence_score', '')
                    child_category = category_data.get('child_category', '')
                    child_score = category_data.get('child_confidence_score', '')
                
                new_rows.append([
                    msg.get('id', ''),
                    msg.get('date', ''),
                    msg.get('date_unixtime', ''),
                    msg.get('from', ''),
                    msg.get('text', '').strip(),
                    msg.get('reply_to_message_id', ''),
                    msg.get('LANGUAGE', ''),
                    msg.get('TRANSLATED_TEXT', ''),
                    parent_category,
                    parent_score,
                    child_category,
                    child_score,
                    location_name,
                    location_coords,
                    location_confidence
                ])
            print("NEW ROWS")
            for row in new_rows:
                print(row)
        except Exception as new_rows_error:
            print("Error adding new rows", new_rows_error)

        
        if new_rows:
            worksheet.append_rows(new_rows)
            return jsonify({'message': f'Successfully uploaded {len(new_rows)} rows'}), 200
        else:
            return jsonify({'message': 'No valid rows to upload'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/generate_summary", methods=["POST"])
def generate_summary():
    try:
        data = request.get_json()
        query = data.get("query", "")
        prompt_data = google_access.GetData()

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "Generate a summary report of the following dataframe:" + prompt_data},
                      {"role": "user", "content": query},
                      {"role": "system", "content": "You are a humanitarian researcher and data analyst. Your goal is to generate a report of the data that will be useful in identifying the concerns of potential beneficiaries, their biggest questions, and what aid needs to be provided. Retrun only the summary, do not add trailing characters such as *** to your response. Structure your summary based on the following example:"
                      "Date Range: xx/xx/xxxx - xx/xx/xxxx"
                      "Top Categories: (List most commonly listed categories here.)"
                      "Top Locations: (List most commonly listed locations here.)"
                      "Top Questions: (List most commonly asked questions here.)" 
                      "Data Inferences: (Use your skills as an advanced data analyst to make inferences about and highlight trends in the data. List trends and inferences here.)"
                       }]
        )

        summary_text = response.choices[0].message.content.strip()
        return jsonify({"summary": summary_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

