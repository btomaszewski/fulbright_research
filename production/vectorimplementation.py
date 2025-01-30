from sentence_transformers import SentenceTransformer
import json
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load your trained embedding model (replace with your actual model path)
embedder = SentenceTransformer('fine_tuned_model')

# Load data from JSON file
with open('testVectorModel.json', 'r') as f:
    data = json.load(f)

# Assuming the JSON file has a list of sentences like:
# [{"sentence": "Barriers to Education"}, {"sentence": "Access to Healthcare"}, ...]

message = [item['sentence'] for item in data]
queries = ["Barriers to Education", "Access to Healthcare", "Employment"]

# Embed all sentences in the corpus using your trained model
message_embeddings = embedder.encode(message, convert_to_tensor=True)

# Embed query sentences using your trained model
queries_embeddings = embedder.encode(queries, convert_to_tensor=True)

# Find the closest 5 sentences for each query based on cosine similarity
top_k = 5
for query, query_embedding in zip(queries, queries_embeddings):
    # Compute cosine similarity between the query and all sentences in the corpus
    similarity_scores = cosine_similarity(query_embedding.cpu().numpy().reshape(1, -1), message_embeddings.cpu().numpy()).flatten()
    
    # Get the top 5 most similar sentences
    top_k_indices = np.argsort(similarity_scores)[::-1][:top_k]
    
    print("\nQuery:", query)
    print("Top 5 most similar sentences in corpus:")
    for idx in top_k_indices:
        print(f"{message[idx]} (Score: {similarity_scores[idx]:.4f})")
