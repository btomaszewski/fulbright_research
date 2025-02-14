import json
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import random
from typing import List, Dict
import itertools

def load_data(file: str) -> List[Dict]:
    """Load and validate training data from a JSON file."""
    try:
        with open(file, "r", encoding="utf-8") as f:
            file_content = f.read()
            print("Loading data file...")  # Debug print
            data = json.loads(file_content)
        return data
    except FileNotFoundError:
        raise Exception(f"Training data file {file} not found")
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON format in {file}")

def save_model(model: SentenceTransformer, path: str) -> None:
    """Save the trained model to disk."""
    try:
        model.save(path)
        print(f"Model successfully saved to {path}")
    except Exception as e:
        print(f"Error saving model: {str(e)}")

def prepare_training_data(data: List[Dict]) -> tuple:
    """Prepare multi-label training data."""
    # Get unique categories by flattening the label lists
    unique_labels = set()
    for entry in data:
        unique_labels.update(entry["label"])
    labels = sorted(list(unique_labels))
    print(f"Found {len(labels)} labels: {labels}")
    
    # Organize data by category
    category_data = {cat: [] for cat in labels}
    for entry in data:
        for label in entry["label"]:
            category_data[label].append(entry["text"])

    train_samples = []
    
    # Create pairs of texts with all combinations of labels
    for entry in data:
        # Generate positive pairs (same label)
        for label in entry["label"]:
            similar_texts = category_data[label]
            if len(similar_texts) > 1:  # Ensure we have at least 2 texts
                other_text = random.choice([t for t in similar_texts if t != entry["text"]])
                train_samples.append(InputExample(
                    texts=[entry["text"], other_text],
                    label=1.0  # Similar texts (same label)
                ))

        # Generate negative pairs (different labels)
        different_labels = [l for l in labels if l not in entry["label"]]
        if different_labels:
            neg_label = random.choice(different_labels)
            neg_text = random.choice(category_data[neg_label])
            train_samples.append(InputExample(
                texts=[entry["text"], neg_text],
                label=0.0  # Different texts (different labels)
            ))

    random.shuffle(train_samples)
    print(f"Created {len(train_samples)} training pairs")
    return train_samples, labels

def train_vector_model(data: List[Dict], epochs: int = 3, batch_size: int = 16, model_name: str = "all-mpnet-base-v2") -> SentenceTransformer:
    """Train a sentence transformer model for vector embeddings."""
    # Initialize base model
    model = SentenceTransformer(model_name)
    
    # Prepare training data
    train_samples, labels = prepare_training_data(data)
    
    # Debug print of samples
    print("\nSample training pairs:")
    for i, sample in enumerate(random.sample(train_samples, min(3, len(train_samples)))):
        print(f"Sample {i + 1}:")
        print(f"Text 1: {sample.texts[0][:100]}...")
        print(f"Text 2: {sample.texts[1][:100]}...")
        print(f"Label: {sample.label} (1.0 = similar, 0.0 = different)\n")
    
    # Create DataLoader
    train_dataloader = DataLoader(train_samples, shuffle=True, batch_size=batch_size)
    
    # Use ContrastiveLoss for multi-label classification
    train_loss = losses.ContrastiveLoss(model)
    
    # Training loop with progress tracking
    print(f"\nStarting training for {epochs} epochs...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=100,
        show_progress_bar=True,
        checkpoint_path="checkpoints",
        checkpoint_save_steps=500
    )
    
    return model

def main():
    try:
        # Configuration
        DATA_FILE = "formatted_clean_export.json"
        MODEL_OUTPUT = "fine_tuned_model3"
        EPOCHS = 5  # Increased epochs for better category separation
        
        # Load and train
        print("Starting vector embedding model training process...")
        training_data = load_data(DATA_FILE)
        model = train_vector_model(training_data, epochs=EPOCHS)
        save_model(model, MODEL_OUTPUT)
        
    except Exception as e:
        print(f"Error during training process: {str(e)}")
        raise

if __name__ == "__main__":
    main()


'''
import json
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import random
from typing import List, Dict
import itertools

def load_data(file: str) -> List[Dict]:
    """Load and validate training data from a JSON file."""
    try:
        with open(file, "r", encoding="utf-8") as f:
            file_content = f.read()
            print("Loading data file...") # Debug print
            data = json.loads(file_content)
        return data
    except FileNotFoundError:
        raise Exception(f"Training data file {file} not found")
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON format in {file}")

def save_model(model: SentenceTransformer, path: str) -> None:
    """Save the trained model to disk."""
    try:
        model.save(path)
        print(f"Model successfully saved to {path}")
    except Exception as e:
        print(f"Error saving model: {str(e)}")

def prepare_training_data(data: List[Dict]) -> tuple:
    """Prepare training data and categories with balanced sampling."""
    # Get unique categories by flattening the label lists
    unique_labels = set()
    for entry in data:
        unique_labels.update(entry["label"])
    labels = sorted(list(unique_labels))
    print(f"Found {len(labels)} labels: {labels}")
    
    # Organize data by category
    category_data = {cat: [] for cat in labels}
    for entry in data:
        # Use the first label for each entry (assuming single-label classification)
        category_data[entry["label"][0]].append(entry["text"])
    
    train_samples = []
    
    # Create positive pairs (same category)
    for label, descriptions in category_data.items():
        print(f"Creating positive pairs for category: {label}")
        for desc1, desc2 in itertools.combinations(descriptions, 2):
            train_samples.append(InputExample(
                texts=[desc1, desc2],
                label=1.0
            ))
    
    # Create negative pairs (different categories)
    for cat1, cat2 in itertools.combinations(labels, 2):
        print(f"Creating negative pairs between {cat1} and {cat2}")
        # Sample equal number of negative pairs as positive pairs per category
        for desc1 in category_data[cat1]:
            desc2 = random.choice(category_data[cat2])
            train_samples.append(InputExample(
                texts=[desc1, desc2],
                label=0.0
            ))
    
    print(f"Created {len(train_samples)} training pairs")
    return train_samples, labels

def train_vector_model(data: List[Dict], epochs: int = 3, batch_size: int = 16, model_name: str = "all-mpnet-base-v2") -> SentenceTransformer:
    """Train a sentence transformer model for vector embeddings."""
    # Initialize base model
    model = SentenceTransformer(model_name)
    
    # Prepare training data
    train_samples, labels = prepare_training_data(data)
    
    # Debug print of samples
    print("\nSample training pairs:")
    for i, sample in enumerate(random.sample(train_samples, min(3, len(train_samples)))):
        print(f"Sample {i + 1}:")
        print(f"Text 1: {sample.texts[0][:100]}...")
        print(f"Text 2: {sample.texts[1][:100]}...")
        print(f"Label: {sample.label} (1.0 = same category, 0.0 = different category)\n")
    
    # Create DataLoader
    train_dataloader = DataLoader(train_samples, shuffle=True, batch_size=batch_size)
    
    # Define loss function
    train_loss = losses.CosineSimilarityLoss(model)
    
    # Training loop with progress tracking
    print(f"\nStarting training for {epochs} epochs...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=100,
        show_progress_bar=True,
        checkpoint_path="checkpoints",
        checkpoint_save_steps=500
    )
    
    return model

def main():
    try:
        # Configuration
        DATA_FILE = "formatted_clean_export.json"
        MODEL_OUTPUT = "fine_tuned_model3"
        EPOCHS = 5  # Increased epochs for better category separation
        
        # Load and train
        print("Starting vector embedding model training process...")
        training_data = load_data(DATA_FILE)
        model = train_vector_model(training_data, epochs=EPOCHS)
        save_model(model, MODEL_OUTPUT)
        
    except Exception as e:
        print(f"Error during training process: {str(e)}")
        raise

if __name__ == "__main__":
    main()


import json
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import random
from typing import List, Dict
import itertools

def load_data(file: str) -> List[Dict]:
    """Load and validate training data from a JSON file."""
    try:
        with open(file, "r", encoding="utf-8") as f:
            file_content = f.read()
            print("Loading data file...") # Debug print
            data = json.loads(file_content)
        return data
    except FileNotFoundError:
        raise Exception(f"Training data file {file} not found")
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON format in {file}")

def save_model(model: SentenceTransformer, path: str) -> None:
    """Save the trained model to disk."""
    try:
        model.save(path)
        print(f"Model successfully saved to {path}")
    except Exception as e:
        print(f"Error saving model: {str(e)}")

def prepare_training_data(data: List[Dict]) -> tuple:
    """Prepare training data and categories with balanced sampling."""
    # Get unique categories
    labels = list(set(entry["label"] for entry in data))
    print(f"Found {len(labels)} labels: {labels}")
    
    # Organize data by category
    category_data = {cat: [] for cat in labels}
    for entry in data:
        category_data[entry["label"]].append(entry["text"])
    
    train_samples = []
    
    # Create positive pairs (same category)
    for labels, descriptions in category_data.items():
        print(f"Creating positive pairs for category: {labels}")
        for desc1, desc2 in itertools.combinations(descriptions, 2):
            train_samples.append(InputExample(
                texts=[desc1, desc2],
                label=1.0
            ))
    
    # Create negative pairs (different categories)
    for cat1, cat2 in itertools.combinations(labels, 2):
        print(f"Creating negative pairs between {cat1} and {cat2}")
        # Sample equal number of negative pairs as positive pairs per category
        for desc1 in category_data[cat1]:
            desc2 = random.choice(category_data[cat2])
            train_samples.append(InputExample(
                texts=[desc1, desc2],
                label=0.0
            ))
    
    print(f"Created {len(train_samples)} training pairs")
    return train_samples, labels

def train_vector_model(data: List[Dict], epochs: int = 3, batch_size: int = 16, model_name: str = "all-mpnet-base-v2") -> SentenceTransformer:
    """Train a sentence transformer model for vector embeddings."""
    # Initialize base model
    model = SentenceTransformer(model_name)
    
    # Prepare training data
    train_samples, labels = prepare_training_data(data)
    
    # Debug print of samples
    print("\nSample training pairs:")
    for i, sample in enumerate(random.sample(train_samples, min(3, len(train_samples)))):
        print(f"Sample {i + 1}:")
        print(f"Text 1: {sample.texts[0][:100]}...")
        print(f"Text 2: {sample.texts[1][:100]}...")
        print(f"Label: {sample.label} (1.0 = same category, 0.0 = different category)\n")
    
    # Create DataLoader
    train_dataloader = DataLoader(train_samples, shuffle=True, batch_size=batch_size)
    
    # Define loss function
    train_loss = losses.CosineSimilarityLoss(model)
    
    # Training loop with progress tracking
    print(f"\nStarting training for {epochs} epochs...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=100,
        show_progress_bar=True,
        checkpoint_path="checkpoints",
        checkpoint_save_steps=500
    )
    
    return model

def main():
    try:
        # Configuration
        DATA_FILE = "formatted_clean_export.json"
        MODEL_OUTPUT = "fine_tuned_model3"
        EPOCHS = 5  # Increased epochs for better category separation
        
        # Load and train
        print("Starting vector embedding model training process...")
        training_data = load_data(DATA_FILE)
        model = train_vector_model(training_data, epochs=EPOCHS)
        save_model(model, MODEL_OUTPUT)
        
    except Exception as e:
        print(f"Error during training process: {str(e)}")
        raise

if __name__ == "__main__":
    main()
'''

