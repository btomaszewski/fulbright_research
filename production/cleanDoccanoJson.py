import json

def clean_and_format_doccano_json(input_text):
    """
    Format and clean unformatted Doccano JSON export.
    - Removes 'Comments' field
    - Ensures labels are in list format
    - Properly formats JSON with indentation
    
    Args:
        input_text (str): The unformatted JSON string from Doccano
        
    Returns:
        str: Properly formatted and cleaned JSON string
    """
    # Check if the input starts with '[' and ends with ']'
    if not input_text.startswith('['):
        input_text = '[' + input_text
    if not input_text.endswith(']'):
        # Remove trailing comma if it exists
        input_text = input_text.rstrip(',') + ']'
    
    try:
        # Parse the JSON string into a Python object
        data = json.loads(input_text)
        
        # Clean each entry
        cleaned_data = []
        for entry in data:
            cleaned_entry = {
                'id': entry['id'],
                'text': entry['text'],
                'label': entry['label'] if isinstance(entry['label'], list) else [entry['label']]
            }
            cleaned_data.append(cleaned_entry)
        
        # Format it with proper indentation
        formatted_json = json.dumps(cleaned_data, indent=4)
        return formatted_json
    
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
        return None

def main():
    # Input and output file names
    input_file = "nataliecrowell.json"  # Change this to your input file name
    output_file = "formatted_clean_export.json"
    
    try:
        # Read the unformatted JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            unformatted_json = f.read()
        
        # Format and clean the JSON
        formatted_json = clean_and_format_doccano_json(unformatted_json)
        
        if formatted_json:
            # Write the formatted JSON to a new file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_json)
            print(f"Successfully formatted and cleaned JSON. Saved to {output_file}")
            
            # Print sample of the changes
            cleaned_data = json.loads(formatted_json)
            print("\nFirst entry in cleaned data:")
            print(json.dumps(cleaned_data[0], indent=2))
        else:
            print("Failed to format JSON")
            
    except FileNotFoundError:
        print(f"Could not find input file: {input_file}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()