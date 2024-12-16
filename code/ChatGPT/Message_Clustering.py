#steps
#1. pre-process text - tokenization, stop-word removal, stemming/lemmatization
#NLTK (Natural Language Toolkit): NLTK is one of the most widely used libraries for natural language processing and text analysis.
#https://www.nltk.org/howto/tokenize.html

#lemmatization - he process of grouping together the inflected forms of a word so they can be analysed as a single item,
#https://en.wikipedia.org/wiki/Lemmatization

#2. Send to TF-IDF

#3. Run K Menas

import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from nltk.corpus import stopwords
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
nltk.download('punkt')

#https://scikit-learn.org/stable/install.html
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

#https://matplotlib.org/stable/users/installing/index.html
import matplotlib.pyplot as plt

# Example text
text = "This is an example sentence demonstrating stop word removal."

# Tokenize the text into words
words = nltk.word_tokenize(text)

# Get English stop words
stop_words = set(stopwords.words('english'))

# Remove stop words from the text
filtered_words = [word for word in words if word.lower() not in stop_words]





def get_wordnet_pos(word):
    """Map POS tag to first character lemmatize() accepts"""
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {"J": wordnet.ADJ,
                "N": wordnet.NOUN,
                "V": wordnet.VERB,
                "R": wordnet.ADV}
    return tag_dict.get(tag, wordnet.NOUN)

word = "running"
lemmatizer = WordNetLemmatizer()
lemma = lemmatizer.lemmatize(word, get_wordnet_pos(word))
print(lemma)  # Output: 'run'


### clustering ###
# Example text data
documents = [
    "This is the first document.",
    "This document is the second document.",
    "And this is the third one.",
    "Is this the first document?",
]

# Step 1: TF-IDF Vectorization
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(documents)

# Step: Dimensionality Reduction (e.g., PCA or t-SNE)
# Choose either PCA or t-SNE for dimensionality reduction
# pca = PCA(n_components=2)
# reduced_data = pca.fit_transform(tfidf_matrix.toarray())
#Perplexity controls the effective number of neighbors that t-SNE considers when embedding each point, and it should typically be less than the number of samples.
tsne = TSNE(n_components=2, perplexity=2, random_state=42)
reduced_data = tsne.fit_transform(tfidf_matrix.toarray())


# Step 2: K-means Clustering
# Determine the optimal number of clusters using silhouette score
max_clusters = min(len(documents), 10)  # Maximum number of clusters to consider
best_score = -1
best_k = 2

for k in range(2, max_clusters + 1):
    kmeans = KMeans(n_clusters=k, random_state=42)
    kmeans.fit(tfidf_matrix)
    cluster_labels = kmeans.labels_
    silhouette_avg = silhouette_score(tfidf_matrix, cluster_labels)
    if silhouette_avg > best_score:
        best_score = silhouette_avg
        best_k = k

# Fit K-means with the optimal number of clusters
kmeans = KMeans(n_clusters=best_k, random_state=42)
kmeans.fit(tfidf_matrix)

# Extract representative words for each cluster
terms = tfidf_vectorizer.get_feature_names_out()
order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]

# Debugging: Print the shape of order_centroids
print("Shape of order_centroids:", order_centroids.shape)

# Check the actual number of clusters formed
num_clusters = order_centroids.shape[0]
print("Number of clusters formed:", num_clusters)



cluster_representative_words = []
#for i in range(k):
for i in range(num_clusters):
    cluster_words = [terms[ind] for ind in order_centroids[i, :10]]  # Select top 10 words
    cluster_representative_words.append(cluster_words)

#cluster_labels = kmeans.labels_
# Assign labels to clusters based on representative words
cluster_labels = [' '.join(words) for words in cluster_representative_words]





# Output cluster labels for each document
""" for i, doc in enumerate(documents):
    print(f"Document '{doc}' belongs to cluster {cluster_labels[i]}") """


# Step 4: Visualize Clusters
plt.figure(figsize=(10, 8))

for i in range(k):
    plt.scatter(best_k[kmeans.labels_ == i, 0], best_k[kmeans.labels_ == i, 1], label=cluster_labels[i])

""" 
for cluster in range(2):
    cluster_points = reduced_data[cluster_labels == cluster]
    plt.scatter(cluster_points[:, 0], cluster_points[:, 1], label=f'Cluster {cluster}')
 """
plt.title('K-means Clustering of Text Data')
plt.xlabel('Dimension 1')
plt.ylabel('Dimension 2')
plt.legend()
plt.grid(True)
plt.show()