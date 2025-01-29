import json
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

# Load the base model
model = SentenceTransformer("all-mpnet-base-v2")

# Load and preprocess training data
train_samples = []
with open("trainvector.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract unique categories for num_labels
categories = list(set(entry["category"] for entry in data))  # Get unique categories

# Convert data into InputExample format
for entry in data:
    train_samples.append(InputExample(texts=[entry["description"], entry["category"]]))

# Create a DataLoader
train_dataloader = DataLoader(train_samples, shuffle=True, batch_size=16)

# Define a loss function
train_loss = losses.SoftmaxLoss(
    model=model,
    sentence_embedding_dimension=model.get_sentence_embedding_dimension(),
    num_labels=len(categories)  # Number of unique categories
)

# Train the model
model.fit(train_objectives=[(train_dataloader, train_loss)], epochs=3, warmup_steps=100)

# Save the fine-tuned model
model.save("fine_tuned_model")

