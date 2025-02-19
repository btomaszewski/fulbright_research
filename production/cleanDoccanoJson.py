import json

def pretty_print_json(input_file, output_file):
    """Reads a minified JSON file and outputs a properly formatted JSON file."""
    try:
        # Read raw JSON data
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)  # Load JSON properly
        
        # Write formatted JSON to a new file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"Formatted JSON saved to {output_file}")

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
    except FileNotFoundError:
        print(f"Error: File {input_file} not found.")

# Example usage
input_file = "nataliecrowell.json"  # Your raw JSON file
output_file = "formatted_nataliecrowell.json"  # Output file with proper indentation
pretty_print_json(input_file, output_file)