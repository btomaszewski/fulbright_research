import pandas as pd

# URL of the public Google Sheets document exported as CSV
sheet_url = 'https://docs.google.com/spreadsheets/d/1jceJ7AZP93hMkkJGOBedUDhOYP77hj1X7GC8NtDX0wg/export?format=csv'

def GetPromptsFromGoogleSheet ():
    # Read the data directly into a DataFrame
    return pd.read_csv(sheet_url)

#gets the specific text of the selected prompt
def GetPromptFromID (promptID):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(sheet_url)
    # Filter the DataFrame by the prompt ID and get the specific text
    
    prompt_text = df.loc[df['ID'] == int(promptID), 'PROMPT_TEXT'].iloc[0]

    return prompt_text

def GetData ():
    data_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJdbcZaIQB4kdykY_8vcK9m1RN-zaHSsMPSnk5uwx4bz3jrY8Oa4McCXkX7fMzZiUk_9KsJ17doyUe/pub?gid=1358394962&single=true&output=csv"
    df = pd.read_csv(data_url)
    return df.to_string(index=False)


# Print the DataFrame
#print(df)