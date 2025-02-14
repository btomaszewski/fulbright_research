import json
import re
import spacy

# Load the spaCy language model
nlp = spacy.load("en_core_web_sm")  # Change to "pl_core_news_sm" for Polish

def clean_text(text):
    """Cleans text by lowercasing, removing special characters, lemmatizing, and removing stopwords."""
    text = text.lower()  # Convert to lowercase
    text = re.sub(r'\s+', ' ', text)  # Remove extra spaces
    text = re.sub(r'[^a-zA-Z\s]', '', text)  # Keep only letters and spaces
    
    doc = nlp(text)
    cleaned_text = " ".join([token.lemma_ for token in doc if not token.is_stop])  # Lemmatize and remove stopwords
    return cleaned_text

# Load input JSON file
with open("vectortraining.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Clean each text entry and store only the cleaned text
cleaned_data = [{"cleaned_text": clean_text(item["text"])} for item in data]

# Save cleaned data to a new JSON file
with open("output_cleaned.json", "w", encoding="utf-8") as f:
    json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

print("Cleaning complete. Output saved as output_cleaned.json")
