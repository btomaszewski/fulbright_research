import spacy
from spacy.tokens import DocBin
from spacy.training import Example
import json
import random
from tqdm import tqdm

def load_and_validate_data(file_path):
    """
    Loads JSON data and validates entity alignments with improved error handling.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    validated_data = []
    skipped = 0
    
    for text, annotations in data:
        entities = annotations.get("entities", [])
        if not entities:
            skipped += 1
            continue
            
        # Validate entity spans
        valid_entities = []
        for start, end, label in entities:
            if start >= 0 and end <= len(text) and start < end:
                if text[start:end].strip():  # Ensure the entity text isn't empty
                    valid_entities.append([start, end, label])
        
        if valid_entities:
            validated_data.append([text, {"entities": valid_entities}])
    
    print(f"Loaded {len(validated_data)} valid training examples")
    print(f"Skipped {skipped} examples due to missing or invalid entities")
    return validated_data

def train_spacy(data, iterations):
    """
    Train the NER model with improved parameters and monitoring.
    """
    # Initialize blank English model
    nlp = spacy.blank("en")
    
    # Add NER pipe
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
    batch_size = 8
    
    # Training loop with progress bar
    with nlp.disable_pipes(*other_pipes):
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
                        drop=0.3,  # Increased dropout
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
    # Load and validate the training data
    print("Loading training data...")
    validated_data = load_and_validate_data("Poland_Test.JSON")
    
    if not validated_data:
        print("Error: No valid training data found!")
        exit(1)
    
    # Train the model with more iterations
    print("\nStarting training...")
    nlp = train_spacy(validated_data, iterations=100)  # Increased iterations
    
    # Save the model
    print("\nSaving model...")
    nlp.to_disk("ner_model")
    
    # Test cases
    test_cases = [
        "I am traveling to Poland and I want to see the Bieszczady Mountains.",
        "Warsaw is the capital of Poland.",
        "The Wawel Castle in Krakow is beautiful.",
        "I visited the Old Town in Gdansk last summer."
    ]
    
    print("\nTesting model on multiple examples:")
    print("\nInitial model performance:")
    for test_text in test_cases:
        test_model(nlp, test_text)

    # Print training summary
    print("\nModel training completed!")
    print(f"Number of training examples: {len(validated_data)}")
    print("Model saved to: ner_model")
    
    # Verify the saved model
    print("\nVerifying saved model:")
    #loaded_nlp = spacy.load("ner_model")
    #for test_text in test_cases:
        #print("\nTesting saved model:")
        #test_model(loaded_nlp, test_text)

