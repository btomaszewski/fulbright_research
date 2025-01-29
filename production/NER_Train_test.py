import spacy
from spacy.tokens import DocBin
from spacy.training import Example
import json
import random

def load_data(file):
    with open(file, "r", encoding="utf-8") as f:
        file_content = f.read()
        print(file_content)  # Debug print statement
        data = json.loads(file_content)
    return data

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def train_spacy(data, iterations):
    TRAIN_DATA = data
    nlp = spacy.blank("en")
    
    # Add NER to pipeline
    if "ner" not in nlp.pipe_names:
        nlp.add_pipe("ner", last=True)
    
    # Get the NER component
    ner = nlp.get_pipe("ner")
    
    # Add labels
    for sentence, annotations in TRAIN_DATA:
        for ent in annotations.get("entities", []):
            ner.add_label(ent[2])
            
    # Debug print of entities
    for sentence, annotations in TRAIN_DATA:
        for ent in annotations.get("entities", []):
            print(f"Sentence: {sentence}")
            print(f"Entity: {ent[:2]}")  # Prints the start and end indices of the entity
            print(f"Label: {ent[2]}")    # Prints the label of the entity

    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    
    # Training loop
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.begin_training()
        for itn in range(iterations):
            print("Starting iteration " + str(itn))
            random.shuffle(TRAIN_DATA)
            losses = {}
            
            # Create batch of examples
            examples = []
            for text, annotations in TRAIN_DATA:
                doc = nlp.make_doc(text)
                example = Example.from_dict(doc, annotations)
                examples.append(example)
            
            # Update the model
            nlp.update(
                examples,
                drop=0.2,
                sgd=optimizer,
                losses=losses
            )
            print(losses)
    
    return nlp

TRAIN_DATA = load_data("NERTest.json")
nlp = train_spacy(TRAIN_DATA, 30)
nlp.to_disk("hp_ner_model")
