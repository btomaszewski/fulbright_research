#word cluds
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from nltk.corpus import stopwords
import plotly.graph_objs as go
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import csv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from wordcloud import WordCloud
import numpy as np

nltk.download('wordnet')
nltk.download('stopwords')
nltk.download('punkt')

ROOT_DIRECTORY = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Full/thematic_analysis/"
THEMATIC_ANALYSIS_OUTPUT = "thematic_analysis.csv"
THEMATIC_ANALYSIS_OUTPUT_FIELDS = ['MESSAGE_ID', 'THEMES', 'TOPICS']

# Load data
documents = []
with open(ROOT_DIRECTORY + THEMATIC_ANALYSIS_OUTPUT, 'r', newline='', encoding="utf-8-sig") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        documents.append(row[THEMATIC_ANALYSIS_OUTPUT_FIELDS[1]])

# TF-IDF Vectorization
stopwords = stopwords.words('english')
vectorizer = TfidfVectorizer(stop_words=stopwords)
X = vectorizer.fit_transform(documents)
terms = vectorizer.get_feature_names_out()

# Determine optimal number of clusters
silhouette_scores = []
for k in range(2, min(11, X.shape[0] + 1)):
    kmeans = KMeans(n_clusters=k)
    kmeans.fit(X)
    silhouette_scores.append(silhouette_score(X, kmeans.labels_))

optimal_num_clusters = np.argmax(silhouette_scores) + 2
kmeans = KMeans(n_clusters=min(optimal_num_clusters, X.shape[0]))
kmeans.fit(X)

# Reduce dimensionality using PCA
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X.toarray())

# Get cluster information
clusters = pd.DataFrame({'Cluster': kmeans.labels_, 'Text': documents})
cluster_terms = clusters.groupby('Cluster').apply(lambda x: terms[np.argmax(np.mean(X[x.index], axis=0))]).reset_index(name='Top Term')

# Initialize Dash app
app = dash.Dash(__name__)

# Define app layout
app.layout = html.Div([
    html.H1("Hierarchical Tree Map Visualization"),
    dcc.Graph(id='tree-map'),
])

# Define callback to update tree map
@app.callback(
    Output('tree-map', 'figure'),
    Input('tree-map', 'clickData')
)
def update_tree_map(click_data):
    if click_data is not None:
        selected_term = click_data['points'][0]['label']
        selected_cluster = cluster_terms[cluster_terms['Top Term'] == selected_term]['Cluster'].values[0]
        cluster_texts = clusters[clusters['Cluster'] == selected_cluster]['Text']
        cloud_text = ' '.join(cluster_texts)
        fig = px.treemap(names=[selected_term], parents=[''], values=[1], title='Cluster Term: ' + selected_term,
                         hover_data={'values': [1]},  # Providing a DataFrame for hover data
                         labels={'color': 'Cluster Term: ' + selected_term},
                         color_discrete_map={'Cluster Term: ' + selected_term: 'blue'})
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(cloud_text)
        fig.add_layout_image(
            dict(
                source=wordcloud.to_image(),
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                sizex=1, sizey=1,
                xanchor="center", yanchor="middle",
                opacity=0.5,
                layer="above")
        )
        fig.update_layout(margin=dict(t=50, b=0, r=0, l=0))
        return fig
    else:
        cluster_sizes = clusters['Cluster'].value_counts().sort_index()
        fig = go.Figure(go.Treemap(
            labels=cluster_terms['Top Term'],
            parents=[''] * len(cluster_terms['Top Term']),
            values=cluster_sizes.values,
            textinfo='label+value',
            hoverinfo='label'
        ))
        fig.update_layout(margin=dict(t=50, b=0, r=0, l=0))
        return fig

if __name__ == '__main__':
    app.run_server(debug=True)
