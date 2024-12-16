import pandas as pd
import os

#date column
DATE_COLUMN = "MESSAGE_DATE_MONTH_DAY_YEAR"
CSV_FILE_NAME = "TG_messages.csv"

def GetCSVData (selected_start_date, selected_end_date):

    # Get the current directory of the Python script
    #TODO - make more flexible
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Construct the relative path to the CSV file
    csv_file_path = os.path.join(current_directory, 'data', CSV_FILE_NAME)

    

    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file_path)

    # Assuming your CSV has a column named 'date' containing date values
    # Convert the 'date' column to datetime if it's not already in datetime format
    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN])

    # Filter the DataFrame for rows within the date range
    date_range_df = df[(df[DATE_COLUMN] >= selected_start_date) & (df[DATE_COLUMN] <= selected_end_date)]

    # Now you have a DataFrame containing only rows within your specified date range
    return date_range_df
