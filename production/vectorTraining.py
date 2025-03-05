import json
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import random
from typing import List, Dict, Tuple
import os
import numpy as np
import random
import torch

# Import our consistent text cleaning function
from cleanText import clean_text

# Define category hierarchy
CATEGORY_HIERARCHY = {
    "Intentions and Mobility": ["Border Crossings"],
    "Accountability to Affected Populations": ["Information Needs", "Aid Received", "Feedback and Reporting"],
    "Health and Mental Health": ["Access to Health Care", "Mental Health Support", "Physical Health Support", "Persons with disabilities"],
    "Education": ["School Enrollment", "Remote Learning", "Barriers to Education"],
    "Accommodation and Housing": ["Living Arrangements and conditions", "Pressure to leave accommodation"],
    "Socio-Economic Inclusion & Livelihoods": ["Employment", "Polish Language Proficiency", "Livelihood and Coping Strategies", "Community Support" ],
    "Protection": ["Legal Status and Documentation", "Safety and Security", "Insurance", "Family Support"],
    "Social Cohesion and Discrimination": [],
    "Null": []
}

# Create a lookup dictionary for child->parent relationships
CHILD_TO_PARENT = {}
for parent, children in CATEGORY_HIERARCHY.items():
    for child in children:
        CHILD_TO_PARENT[child] = parent

def load_data(file: str) -> List[Dict]:
    """Load and validate training data from a JSON file."""
    try:
        with open(file, "r", encoding="utf-8") as f:
            file_content = f.read()
            print("Loading data file...")
            data = json.loads(file_content)
        return data
    except FileNotFoundError:
        raise Exception(f"Training data file {file} not found")
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON format in {file}")

def save_model_package(model: SentenceTransformer, labels: List[str], output_dir: str) -> None:
    """
    Save the complete model package including embeddings and metadata.
    
    Args:
        model: Trained SentenceTransformer model
        labels: List of category labels
        output_dir: Directory to save the model package
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Save the base model
        model_path = os.path.join(output_dir, "sentence_transformer")
        model.save(model_path)
        
        # 2. Generate and save category embeddings
        category_embeddings = {}
        for label in labels:
            # Generate embedding for each category label
            embedding = model.encode(label)
            category_embeddings[label] = embedding.tolist()
        
        embeddings_path = os.path.join(output_dir, "category_embeddings.json")
        with open(embeddings_path, 'w') as f:
            json.dump(category_embeddings, f)
        
        # 3. Save metadata with hierarchy information
        metadata = {
            "model_type": "sentence_transformer",
            "categories": labels,
            "embedding_dimension": model.get_sentence_embedding_dimension(),
            "base_model_name": model.tokenizer.name_or_path,
            "multi_label": True,  # Indicate this is a multi-label model
            "category_hierarchy": CATEGORY_HIERARCHY,  # Add hierarchy information
            "child_to_parent": CHILD_TO_PARENT  # Add child->parent mapping
        }
        
        metadata_path = os.path.join(output_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
            
        print(f"Model package successfully saved to {output_dir}")
        print(f"Package contains:")
        print(f"- Trained model")
        print(f"- Category embeddings for {len(labels)} categories")
        print(f"- Model metadata with hierarchy information")
        
    except Exception as e:
        print(f"Error saving model package: {str(e)}")
        raise

def prepare_training_data(data: List[Dict], max_positives=6, max_negatives=6) -> Tuple[List[InputExample], List[str]]:
    """
    Prepare multi-label training data with enhanced sampling strategies.
    
    Args:
        data: List of training examples
        max_positives: Maximum number of positive pairs per entry-label
        max_negatives: Maximum number of negative pairs per entry
    """
    # Add parent categories to labels if they're not explicitly included
    for entry in data:
        parent_labels = set()
        for label in entry["label"]:
            if label in CHILD_TO_PARENT:
                parent_labels.add(CHILD_TO_PARENT[label])
        entry["label"].extend(list(parent_labels))
    
    # Get unique categories by flattening the label lists
    unique_labels = set()
    for entry in data:
        unique_labels.update(entry["label"])
    labels = sorted(list(unique_labels))
    print(f"Found {len(labels)} labels: {labels}")
    
    # Clean text data
    for entry in data:
        entry["text"] = clean_text(entry["text"])
    
    # Organize data by category
    category_data = {cat: [] for cat in labels}
    for entry in data:
        for label in entry["label"]:
            category_data[label].append(entry["text"])

    train_samples = []
    
    # Create pairs of texts with enhanced sampling
    for entry in data:
        entry_text = entry["text"]
        
        # 1. Generate multiple positive pairs (same label)
        for label in entry["label"]:
            similar_texts = [t for t in category_data[label] if t != entry_text]
            if similar_texts:
                # Select up to max_positives examples per label
                num_positives = min(max_positives, len(similar_texts))
                other_texts = random.sample(similar_texts, num_positives)
                
                for other_text in other_texts:
                    train_samples.append(InputExample(
                        texts=[entry_text, other_text],
                        label=1.0  # Similar texts (same label)
                    ))

        # 2. Generate multiple negative pairs (different labels)
        different_labels = [l for l in labels if l not in entry["label"]]
        if different_labels:
            # Select up to max_negatives different labels
            num_neg_labels = min(max_negatives, len(different_labels))
            neg_labels = random.sample(different_labels, num_neg_labels)
            
            for neg_label in neg_labels:
                if category_data[neg_label]:  # Ensure the category has examples
                    neg_text = random.choice(category_data[neg_label])
                    train_samples.append(InputExample(
                        texts=[entry_text, neg_text],
                        label=0.0  # Different texts (different labels)
                    ))

    random.shuffle(train_samples)
    print(f"Created {len(train_samples)} training pairs")
    print(f"- Using up to {max_positives} positive pairs per entry-label")
    print(f"- Using up to {max_negatives} negative pairs per entry")
    
    return train_samples, labels

def train_multi_stage(
    data: List[Dict], 
    epochs_stage1: int = 5,
    epochs_stage2: int = 2,
    batch_size: int = 16, 
    model_name: str = "all-mpnet-base-v2",
    learning_rate: float = 2e-5,
    output_dir: str = "vector_model_package"
) -> None:
    """
    Train a sentence transformer model using a multi-stage approach.
    
    Args:
        data: List of training examples
        epochs_stage1: Number of training epochs for first stage
        epochs_stage2: Number of training epochs for second stage
        batch_size: Training batch size
        model_name: Base model to use
        learning_rate: Learning rate for the optimizer
        output_dir: Directory to save the final model
    """
    print(f"Starting multi-stage training process with {model_name}")
    print(f"Stage 1: {epochs_stage1} epochs with MultipleNegativesRankingLoss")
    print(f"Stage 2: {epochs_stage2} epochs with ContrastiveLoss")
    
    # Initialize base model
    model = SentenceTransformer(model_name)
    
    # Prepare enhanced training data
    train_samples, labels = prepare_training_data(data, max_positives=6, max_negatives=6)
    
    # Debug print of samples
    print("\nSample training pairs:")
    for i, sample in enumerate(random.sample(train_samples, min(3, len(train_samples)))):
        print(f"Sample {i + 1}:")
        print(f"Text 1: {sample.texts[0][:100]}...")
        print(f"Text 2: {sample.texts[1][:100]}...")
        print(f"Label: {sample.label} (1.0 = similar, 0.0 = different)\n")
    
    # Create DataLoader
    train_dataloader = DataLoader(train_samples, shuffle=True, batch_size=batch_size)
    
    # STAGE 1: Multiple Negatives Ranking Loss
    if epochs_stage1 > 0:
        print("\n=== STAGE 1: Training with MultipleNegativesRankingLoss ===")
        stage1_loss = losses.MultipleNegativesRankingLoss(model)
        
        warmup_steps = int(len(train_dataloader) * epochs_stage1 * 0.1)
        
        model.fit(
            train_objectives=[(train_dataloader, stage1_loss)],
            epochs=epochs_stage1,
            warmup_steps=warmup_steps,
            optimizer_params={'lr': learning_rate},
            scheduler="warmupcosine",
            show_progress_bar=True,
            checkpoint_path="checkpoints_stage1",
            checkpoint_save_steps=500
        )
        
        print("Stage 1 training complete.")
    
    # STAGE 2: Contrastive Loss for Fine-Tuning
    if epochs_stage2 > 0:
        print("\n=== STAGE 2: Fine-tuning with ContrastiveLoss ===")
        # Use a slightly lower learning rate for fine-tuning
        lr_stage2 = learning_rate * 0.5
        print(f"Using reduced learning rate: {lr_stage2}")
        
        stage2_loss = losses.ContrastiveLoss(model)
        
        warmup_steps = int(len(train_dataloader) * epochs_stage2 * 0.1)
        
        model.fit(
            train_objectives=[(train_dataloader, stage2_loss)],
            epochs=epochs_stage2,
            warmup_steps=warmup_steps,
            optimizer_params={'lr': lr_stage2},
            scheduler="warmupcosine",
            show_progress_bar=True,
            checkpoint_path="checkpoints_stage2",
            checkpoint_save_steps=500
        )
        
        print("Stage 2 training complete.")
    
    # Save the final model package
    save_model_package(model, labels, output_dir)
    print(f"Multi-stage training completed and model saved to {output_dir}")

def evaluate_model(model, data, labels):
    """
    Evaluate the model on training data to get an idea of performance.
    """
    print("\nEvaluating model on training data...")
    
    # Create text and category embeddings
    texts = [entry["text"] for entry in data]
    text_embeddings = model.encode(texts)
    
    category_embeddings = {}
    for label in labels:
        category_embeddings[label] = model.encode(label)
    
    # Add parent categories to the ground truth for evaluation
    for entry in data:
        parent_labels = set()
        for label in entry["label"]:
            if label in CHILD_TO_PARENT:
                parent_labels.add(CHILD_TO_PARENT[label])
        entry["label"] = list(set(entry["label"]).union(parent_labels))
    
    # Evaluate on training data
    correct_predictions = 0
    total_true_labels = 0
    total_predicted_labels = 0
    
    # Track hierarchical evaluation metrics
    parent_correct = 0
    parent_total_true = 0
    parent_total_predicted = 0
    
    child_correct = 0
    child_total_true = 0
    child_total_predicted = 0
    
    for i, entry in enumerate(data):
        true_labels = set(entry["label"])
        total_true_labels += len(true_labels)
        
        # Get similarity to all categories
        similarities = {}
        for label in labels:
            similarity = np.dot(text_embeddings[i], category_embeddings[label])
            similarities[label] = similarity
        
        # Predict labels (those with similarity > threshold)
        threshold = 0.5  # Can be tuned
        predicted_labels = {label for label, sim in similarities.items() if sim > threshold}
        total_predicted_labels += len(predicted_labels)
        
        # Count correctly predicted labels
        correct_predictions += len(true_labels.intersection(predicted_labels))
        
        # Count parent and child metrics separately
        true_parents = {label for label in true_labels if label in CATEGORY_HIERARCHY}
        true_children = {label for label in true_labels if label in CHILD_TO_PARENT}
        
        pred_parents = {label for label in predicted_labels if label in CATEGORY_HIERARCHY}
        pred_children = {label for label in predicted_labels if label in CHILD_TO_PARENT}
        
        parent_total_true += len(true_parents)
        parent_total_predicted += len(pred_parents)
        parent_correct += len(true_parents.intersection(pred_parents))
        
        child_total_true += len(true_children)
        child_total_predicted += len(pred_children)
        child_correct += len(true_children.intersection(pred_children))
    
    # Calculate precision, recall, F1
    precision = correct_predictions / max(total_predicted_labels, 1)
    recall = correct_predictions / max(total_true_labels, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-10)
    
    # Calculate parent category metrics
    parent_precision = parent_correct / max(parent_total_predicted, 1)
    parent_recall = parent_correct / max(parent_total_true, 1)
    parent_f1 = 2 * parent_precision * parent_recall / max(parent_precision + parent_recall, 1e-10)
    
    # Calculate child category metrics
    child_precision = child_correct / max(child_total_predicted, 1)
    child_recall = child_correct / max(child_total_true, 1)
    child_f1 = 2 * child_precision * child_recall / max(child_precision + child_recall, 1e-10)
    
    print(f"Overall evaluation results:")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")
    
    print(f"\nParent category evaluation results:")
    print(f"Precision: {parent_precision:.4f}")
    print(f"Recall: {parent_recall:.4f}")
    print(f"F1 Score: {parent_f1:.4f}")
    
    print(f"\nChild category evaluation results:")
    print(f"Precision: {child_precision:.4f}")
    print(f"Recall: {child_recall:.4f}")
    print(f"F1 Score: {child_f1:.4f}")

def main():
    try:
        # Configuration
        DATA_FILE = "formatted_clean_export.json"
        MODEL_OUTPUT_DIR = "vector_model_package"
        EPOCHS_STAGE1 = 5  # Increased to 5 for better training
        EPOCHS_STAGE2 = 2  
        BATCH_SIZE = 16
        MODEL_NAME = "all-mpnet-base-v2"  # Can also try other models like "paraphrase-mpnet-base-v2"
        LEARNING_RATE = 2e-5
        
        # Set random seed for reproducibility
        random.seed(42)
        np.random.seed(42)
        torch.manual_seed(42)
        
        # Load training data
        print("Starting multi-stage vector embedding model training process...")
        training_data = load_data(DATA_FILE)
        
        # Train using multi-stage approach
        train_multi_stage(
            data=training_data,
            epochs_stage1=EPOCHS_STAGE1,
            epochs_stage2=EPOCHS_STAGE2,
            batch_size=BATCH_SIZE,
            model_name=MODEL_NAME,
            learning_rate=LEARNING_RATE,
            output_dir=MODEL_OUTPUT_DIR
        )
        
        # Load the trained model for evaluation
        trained_model = SentenceTransformer(os.path.join(MODEL_OUTPUT_DIR, "sentence_transformer"))
        
        # Get unique labels
        unique_labels = set()
        for entry in training_data:
            unique_labels.update(entry["label"])
        labels = sorted(list(unique_labels))
        
        # Evaluate the model
        evaluate_model(trained_model, training_data, labels)
        
        print("\nTraining and evaluation complete!")
        print(f"Model package saved to: {MODEL_OUTPUT_DIR}")
        print("You can now use this model with PyInstaller for your deployment.")
        
    except Exception as e:
        print(f"Error during training process: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()

