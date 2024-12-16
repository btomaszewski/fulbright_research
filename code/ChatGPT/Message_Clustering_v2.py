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
import numpy as np
import csv
from csv import DictWriter
from wordcloud import WordCloud

ROOT_DIRECOTRY =  "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/analysis_March_2024/" 
THEMATIC_ANALYSIS_OUTPUT = "thematic_analysis_Oct_2023.csv"
THEMATIC_ANALYSIS_OUTPUT_FIELDS = ['MESSAGE_ID', 'THEMES', 'TOPICS'] 

ANALYSIS_TYPE = "TOPICS"
FIELD_TO_USE = 0 
TITLE_TO_USE = ANALYSIS_TYPE

if (ANALYSIS_TYPE == "THEMES"):
    FIELD_TO_USE = 1    
elif(ANALYSIS_TYPE == "TOPICS"):
    FIELD_TO_USE = 2


#plug in the documents
#open messages stored in CSV  file
documents = []
with open(ROOT_DIRECOTRY + THEMATIC_ANALYSIS_OUTPUT,'r',newline='',encoding="utf-8-sig") as csvfile:

  reader = csv.DictReader(csvfile)
  #loop through the contents
  for row in reader:
    documents.append(row[THEMATIC_ANALYSIS_OUTPUT_FIELDS[FIELD_TO_USE]])

# Close the file object
csvfile.close()

cloud_text = ' '.join(documents)

""" # Example text data
documents = [
    "This is the first document.",
    "This document is the second document.",
    "And this is the third one.",
    "Is this the first document?",
] """

# Convert text data to TF-IDF features
# Define common English stopwords
stopwords = [
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
    "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and",
    "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between",
    "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off",
    "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"
]



vectorizer = TfidfVectorizer(stop_words=stopwords)
#vectorizer = TfidfVectorizer(stop_words='english')
X = vectorizer.fit_transform(documents)

# Get the feature names (terms) from the vectorizer
terms = vectorizer.get_feature_names_out()


# Determine the optimal number of clusters using silhouette score
silhouette_scores = []
for k in range(2, min(11, X.shape[0] + 1)):  # try different numbers of clusters from 2 to min(10, n_samples)
    kmeans = KMeans(n_clusters=k)
    kmeans.fit(X)
    
    silhouette_scores.append(silhouette_score(X, kmeans.labels_))
    

# Determine the optimal number of clusters
optimal_num_clusters = np.argmax(silhouette_scores) + 2  # Add 2 because range starts from 2

# Perform K-means clustering with optimal number of clusters
kmeans = KMeans(n_clusters=min(optimal_num_clusters, X.shape[0]))
kmeans.fit(X)

# Reduce dimensionality using PCA
#PCA reduces the dimensionality of your data by projecting it onto a lower-dimensional space while preserving the maximum variance. This can be helpful when dealing with high-dimensional data, as it allows you to visualize the data in two or three dimensions.
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X.toarray())

# Calculate the range of X and Y axes
x_min, x_max = X_pca[:, 0].min(), X_pca[:, 0].max()
y_min, y_max = X_pca[:, 1].min(), X_pca[:, 1].max()


# Visualize clusters
plt.figure(figsize=(8, 6))
# Set axis limits automatically
plt.xlim(x_min, x_max)
plt.ylim(y_min, y_max)

for i in range(optimal_num_clusters):
    cluster_texts = np.array(documents)[kmeans.labels_ == i]

    # Calculate the centroid of the feature vectors for the current cluster
    #when you calculate the centroid vector (centroid_vector), you should be using the original feature vectors (X) rather than the reduced feature vectors (X_pca). This is because the centroid vectors represent the mean feature vectors of the documents in each cluster in the original feature space.
    centroid_vector = np.mean(X[kmeans.labels_ == i], axis=0)
    
    # Find the term with the highest TF-IDF score in the centroid vector
    centroid_term_index = np.argmax(centroid_vector)
    centroid_term = terms[centroid_term_index]

    #used the mean coordinates of the data points in the PCA-reduced space (X_pca) for plotting the centroid term:    
    plt.text(X_pca[kmeans.labels_ == i, 0].mean(), 
                X_pca[kmeans.labels_ == i, 1].mean(), 
                centroid_term, 
                horizontalalignment='center', 
                verticalalignment='center', 
                bbox=dict(facecolor='white',   alpha=0.5))
    
# Generate a word cloud object
wordcloud = WordCloud(width=800, height=400, background_color='white').generate(cloud_text)

#f-strings (available in Python 3.6 and later):
plt.title(f"{TITLE_TO_USE} Word Cloud")

plt.figure(figsize=(10, 5))
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis('on')
plt.show()




""" plt.title(f"{TITLE_TO_USE} K Means Clusters")
plt.xlabel('Principal Component 1')
plt.ylabel('Principal Component 2')
plt.grid(True)
plt.show()
 """





input("Press Enter to close the plot window...")


