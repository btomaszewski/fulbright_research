import spacy
from spacy.tokens import DocBin
from spacy.training import Example
import json
import random
from tqdm import tqdm

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

def load_and_validate_jsonl_data(file_path, nlp):
    """
    Loads JSONL data and validates entity alignments with improved error handling.
    Processes the file in chunks to handle large datasets efficiently.
    """
    validated_data = []
    skipped = 0
    processed = 0
    
    # Process the file in batches to handle large files
    with open(file_path, "r", encoding="utf-8") as f:
        line_number = 0
        batch_size = 1000  # Process 1000 lines at a time
        batch = []
        
        for line in f:
            line_number += 1
            if not line.strip():  # Skip empty lines
                continue
                
            try:
                data = json.loads(line)
                batch.append(data)
                
                # Process in batches
                if len(batch) >= batch_size:
                    process_batch(batch, validated_data, skipped, processed, nlp)
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
            process_batch(batch, validated_data, skipped, processed, nlp)
            processed += len(batch)
    
    print(f"Loaded {len(validated_data)} valid training examples")
    print(f"Skipped {skipped} examples due to missing or invalid entities")
    return validated_data

def process_batch(batch, validated_data, skipped, processed, nlp):
    """
    Process a batch of examples, validating entities and adding to training data.
    """
    for data in batch:
        text = data.get("text", "")
        label_data = data.get("label", [])
        
        if not text or not label_data:
            skipped += 1
            continue
        
        # Validate entity spans
        valid_entities = validate_entity(nlp, text, label_data)
        
        if valid_entities:
            validated_data.append([text, {"entities": valid_entities}])
        else:
            skipped += 1

def train_spacy(data, iterations, model_name=None):
    """
    Train the NER model with improved parameters and monitoring.
    """
    # Load a base model if provided, otherwise use blank model
    if model_name:
        print(f"Loading base model: {model_name}")
        nlp = spacy.load(model_name)
    else:
        print("Initializing blank English model")
        nlp = spacy.blank("en")
    
    # Add NER pipe if not present
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")
    
    # Collect all unique labels
    labels = set()
    for text, annotations in data:
        for _, _, label in annotations.get("entities", []):
            labels.add(label)
    
    # Add labels to the NER pipe
    for label in labels:
        ner.add_label(label)
    
    print(f"Training with labels: {', '.join(labels)}")
    
    # Configure training
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    batch_size = 16  # Optimal for most systems
    
    # Training loop with progress bar
    with nlp.disable_pipes(*other_pipes):
        # Initialize optimizer for blank model or resume training for pre-loaded model
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
                    
                    # Accumulate losses
                    nlp.update(
                        examples,
                        drop=0.3,  # Dropout for better generalization
                        losses=losses
                    )
                    pbar.update(1)
                    pbar.set_postfix(losses=losses)
            
            # Print the losses for this iteration
            print(f"\nLosses at iteration {itn+1}: {losses}")
    
    return nlp

def test_model(nlp, text, verbose=True):
    """
    Test the model with detailed output.
    """
    doc = nlp(text)
    if verbose:
        print("\nText:", text)
        print("\nEntities found:")
        if not doc.ents:
            print("No entities detected")
        for ent in doc.ents:
            print(f"Text: {ent.text:<20} Label: {ent.label_:<10} Position: {ent.start_char}:{ent.end_char}")
    return doc.ents

if __name__ == "__main__":
    # Choose whether to use a pre-trained model for tokenization
    use_pretrained = True  # Set to False for blank model
    model_name = "en_core_web_sm" if use_pretrained else None  # Using smaller model for efficiency
    
    # Initialize the tokenizer
    if use_pretrained:
        print(f"Loading base spaCy model for tokenization: {model_name}")
        base_nlp = spacy.load(model_name, disable=["ner", "parser", "attribute_ruler"])  # Minimal loading
    else:
        print("Using blank model for tokenization")
        base_nlp = spacy.blank("en")
    
    # Load and validate the training data
    print("Loading training data...")
    jsonl_file_path = "nataliecrowell.jsonl"  # Replace with your JSONL file path
    validated_data = load_and_validate_jsonl_data(jsonl_file_path, base_nlp)
    
    if not validated_data:
        print("Error: No valid training data found!")
        exit(1)
    
    # Train the model
    print("\nStarting training...")
    iterations = 100  # Adjust based on dataset size and available time
    nlp = train_spacy(validated_data, iterations, model_name if use_pretrained else None)
    
    # Save the model
    print("\nSaving model...")
    output_dir = "ner_model_optimized"
    nlp.to_disk(output_dir)
    
    # Test cases - using examples from your provided JSONL data
    test_cases = [
        "Who will be going to Warsaw tomorrow morning?",
        "Please tell me if carriers are traveling from Lviv to the Shehyni checkpoint today",
        "I need to get from Kyiv to Odesa this weekend.",
        "Are there any flights from London to Madrid available?"
    ]
    
    print("\nTesting model on multiple examples:")
    for test_text in test_cases:
        test_model(nlp, test_text)

    # Print training summary
    print("\nModel training completed!")
    print(f"Number of training examples: {len(validated_data)}")
    print(f"Model saved to: {output_dir}")