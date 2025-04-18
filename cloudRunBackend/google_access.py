import pandas as pd
import logging

# Configure logging
logger = logging.getLogger("google-access")

# URL of the public Google Sheets document exported as CSV
sheet_url = 'https://docs.google.com/spreadsheets/d/1jceJ7AZP93hMkkJGOBedUDhOYP77hj1X7GC8NtDX0wg/export?format=csv'

def GetPromptsFromGoogleSheet():
    """
    Fetches prompt data from Google Sheet.
    
    Returns:
        DataFrame: Pandas DataFrame containing prompts from Google Sheet
    """
    try:
        # Read the data directly into a DataFrame
        df = pd.read_csv(sheet_url)
        logger.info(f"Successfully loaded {len(df)} prompts from Google Sheet")
        return df
    except Exception as e:
        logger.error(f"Error fetching prompts from Google Sheet: {str(e)}")
        # Return empty DataFrame on error
        return pd.DataFrame(columns=['ID', 'PROMPT_NAME', 'PROMPT_TEXT'])

def GetPromptFromID(promptID):
    """
    Gets the specific text of the selected prompt.
    
    Args:
        promptID: The ID of the prompt to retrieve
        
    Returns:
        str: The prompt text for the given ID
    """
    try:
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(sheet_url)
        
        # Filter the DataFrame by the prompt ID and get the specific text
        # Convert promptID to int to ensure proper matching
        prompt_text = df.loc[df['ID'] == int(promptID), 'PROMPT_TEXT'].iloc[0]
        
        logger.info(f"Successfully retrieved prompt text for ID {promptID}")
        return prompt_text
    except Exception as e:
        logger.error(f"Error retrieving prompt text for ID {promptID}: {str(e)}")
        return f"Error: Unable to retrieve prompt text for ID {promptID}"

def GetData():
    """
    Fetches data from Google Sheet for analysis.
    
    Returns:
        str: String representation of the DataFrame
    """
    try:
        data_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJdbcZaIQB4kdykY_8vcK9m1RN-zaHSsMPSnk5uwx4bz3jrY8Oa4McCXkX7fMzZiUk_9KsJ17doyUe/pub?gid=1358394962&single=true&output=csv"
        df = pd.read_csv(data_url)
        logger.info(f"Successfully loaded data: {len(df)} rows and {len(df.columns)} columns")
        return df.to_string(index=False)
    except Exception as e:
        logger.error(f"Error fetching data from Google Sheet: {str(e)}")
        return "Error: Unable to retrieve data from Google Sheet"


'''
def home():

    # prompts loads from  Google Sheets
    #prompt_data = pd.DataFrame(google_access.GetPromptsFromGoogleSheet)
    prompt_data = google_access.GetPromptsFromGoogleSheet()

    # Pass prompt data to the template to populate the selection box
    # Create a list of tuples from multiple columns
    prompt_items = list(zip(prompt_data['ID'], prompt_data['PROMPT_NAME']))
    
    ## Pass the list of tuples to the template, along with the length of the list
    return render_template('index.html', items=prompt_items, len=len)

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

'''