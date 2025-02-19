import spacy
from spacy.tokens import DocBin
from spacy.training import Example
import json
import random
import re
from tqdm import tqdm

def clean_text(text):
    """
    Clean text while preserving important location context
    """
    # Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)

    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove multiple periods/commas
    text = re.sub(r'\.+', '.', text)
    text = re.sub(r',+', ',', text)
    
    return text.strip()

def validate_entity(nlp, text, entities):
    """
    Ensures entity spans align with spaCy's tokenization without rejecting valid entities.
    Returns aligned entities and provides warnings for potentially problematic spans.
    """
    doc = nlp.make_doc(text)  # Tokenize text with spaCy
    aligned_entities = []
    
    for start, end, label in entities:
        if not (0 <= start < end <= len(text)):
            continue  # Skip invalid spans
            
        span_text = text[start:end]
        if not span_text.strip():
            continue  # Skip empty spans
        
        # Rather than rejecting based on token boundaries, we keep all valid spans
        # but provide warnings for spans that might cause issues
        span_has_token_boundary = False
        for token in doc:
            if token.idx == start or token.idx + len(token.text) == end:
                span_has_token_boundary = True
                break
                
        if not span_has_token_boundary:
            print(f"Warning: Span '{span_text}' in '{text[:50]}...' doesn't align with token boundaries")
            
        aligned_entities.append([start, end, label])

    return aligned_entities

def adjust_entity_spans(original_text, cleaned_text, entities):
    """
    Adjust entity spans to match cleaned text positions
    """
    char_mapping = {}
    cleaned_pos = 0
    
    # Create mapping between original and cleaned text positions
    for orig_pos, char in enumerate(original_text):
        if cleaned_pos < len(cleaned_text) and char == cleaned_text[cleaned_pos]:
            char_mapping[orig_pos] = cleaned_pos
            cleaned_pos += 1
    
    # Adjust entity spans based on cleaning
    adjusted_entities = []
    for start, end, label in entities:
        # Find nearest mapped positions
        while start not in char_mapping and start > 0:
            start -= 1
        while (end-1) not in char_mapping and end > start:
            end -= 1
            
        if start in char_mapping and (end-1) in char_mapping:
            new_start = char_mapping[start]
            new_end = char_mapping[end-1] + 1
            adjusted_entities.append([new_start, new_end, label])
    
    return adjusted_entities

def load_and_validate_jsonl_data(file_path, nlp):
    """
    Loads JSONL data, cleans text, and validates entity alignments.
    """
    validated_data = []
    skipped = 0
    processed = 0
    
    with open(file_path, "r", encoding="utf-8") as f:
        line_number = 0
        batch_size = 1000
        batch = []
        
        for line in f:
            line_number += 1
            if not line.strip():
                continue
                
            try:
                data = json.loads(line)
                text = data.get("text", "")
                label_data = data.get("label", [])
                
                if not text or not label_data:
                    skipped += 1
                    continue
                
                # Clean the text
                cleaned_text = clean_text(text)
                
                # Adjust entity spans for cleaned text
                adjusted_entities = adjust_entity_spans(text, cleaned_text, label_data)
                
                # Validate adjusted entity spans
                valid_entities = validate_entity(nlp, cleaned_text, adjusted_entities)
                
                if valid_entities:
                    batch.append([cleaned_text, {"entities": valid_entities}])
                else:
                    skipped += 1
                
                # Process in batches
                if len(batch) >= batch_size:
                    validated_data.extend(batch)
                    processed += len(batch)
                    batch = []
                    print(f"Processed {processed} examples...")
                    
            except json.JSONDecodeError:
                print(f"Error decoding JSON at line {line_number}, skipping...")
                skipped += 1
            except Exception as e:
                print(f"Error processing line {line_number}: {e}, skipping...")
                skipped += 1
        
        # Process any remaining examples
        if batch:
            validated_data.extend(batch)
            processed += len(batch)
    
    print(f"Loaded {len(validated_data)} valid training examples")
    print(f"Skipped {skipped} examples due to errors or invalid entities")
    return validated_data

def train_spacy(data, iterations, model_name=None):
    """
    Train the NER model with improved parameters and monitoring.
    """
    if model_name:
        print(f"Loading base model: {model_name}")
        nlp = spacy.load(model_name)
    else:
        print("Initializing blank English model")
        nlp = spacy.blank("en")
    
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")
    
    labels = set()
    for text, annotations in data:
        for _, _, label in annotations.get("entities", []):
            labels.add(label)
    
    for label in labels:
        ner.add_label(label)
    
    print(f"Training with labels: {', '.join(labels)}")
    
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    batch_size = 16
    
    with nlp.disable_pipes(*other_pipes):
        if model_name:
            optimizer = nlp.resume_training()
        else:
            optimizer = nlp.initialize()
        
        print("Beginning training...")
        for itn in range(iterations):
            random.shuffle(data)
            losses = {}
            batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]
            
            with tqdm(total=len(batches), desc=f"Iteration {itn+1}/{iterations}") as pbar:
                for batch in batches:
                    examples = []
                    for text, annotations in batch:
                        doc = nlp.make_doc(text)
                        example = Example.from_dict(doc, annotations)
                        examples.append(example)
                    
                    nlp.update(
                        examples,
                        drop=0.3,
                        losses=losses
                    )
                    pbar.update(1)
                    pbar.set_postfix(losses=losses)
            
            print(f"\nLosses at iteration {itn+1}: {losses}")
    
    return nlp

def test_model(nlp, text, verbose=True):
    """
    Test the model with detailed output.
    """
    # Clean the test text the same way as training data
    cleaned_text = clean_text(text)
    doc = nlp(cleaned_text)
    
    if verbose:
        print("\nOriginal text:", text)
        print("Cleaned text:", cleaned_text)
        print("\nEntities found:")
        if not doc.ents:
            print("No entities detected")
        for ent in doc.ents:
            print(f"Text: {ent.text:<20} Label: {ent.label_:<10} Position: {ent.start_char}:{ent.end_char}")
    return doc.ents

if __name__ == "__main__":
    use_pretrained = True
    model_name = "en_core_web_sm" if use_pretrained else None
    
    if use_pretrained:
        print(f"Loading base spaCy model for tokenization: {model_name}")
        base_nlp = spacy.load(model_name, disable=["ner", "parser", "attribute_ruler"])
    else:
        print("Using blank model for tokenization")
        base_nlp = spacy.blank("en")
    
    print("Loading training data...")
    jsonl_file_path = "nataliecrowell.jsonl"
    validated_data = load_and_validate_jsonl_data(jsonl_file_path, base_nlp)
    
    if not validated_data:
        print("Error: No valid training data found!")
        exit(1)
    
    print("\nStarting training...")
    iterations = 100
    nlp = train_spacy(validated_data, iterations, model_name if use_pretrained else None)
    
    print("\nSaving model...")
    output_dir = "ner_model_optimized"
    nlp.to_disk(output_dir)
    
    test_cases = [
        "Who will be going to Warsaw tomorrow morning?",
        "Please tell me if carriers are traveling from Lviv to the Shehyni checkpoint today",
        "I need to get from Kyiv to Odesa this weekend.",
        "Are there any flights from London to Madrid available?"
    ]
    
    print("\nTesting model on multiple examples:")
    for test_text in test_cases:
        test_model(nlp, test_text)

    print("\nModel training completed!")
    print(f"Number of training examples: {len(validated_data)}")
    print(f"Model saved to: {output_dir}")