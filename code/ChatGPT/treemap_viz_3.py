#tree map, word cloud, individual messages
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import plotly.graph_objs as go
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import csv
import numpy as np
from wordcloud import WordCloud
import base64
import io

nltk.download('stopwords')

ROOT_DIRECTORY = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Full/thematic_analysis/"
THEMATIC_ANALYSIS_OUTPUT = "thematic_analysis.csv"
THEMATIC_ANALYSIS_OUTPUT_FIELDS = ['MESSAGE_ID', 'THEMES', 'TOPICS']

MESSAGE_URL = "http://127.0.0.1:5500/ChatGPT/message_retrieval.html?num="

# Load data
documents = []
message_ids = []  # Store message IDs
with open(ROOT_DIRECTORY + THEMATIC_ANALYSIS_OUTPUT, 'r', newline='', encoding="utf-8-sig") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        message_ids.append(row[THEMATIC_ANALYSIS_OUTPUT_FIELDS[0]])  # Store message ID
        documents.append(row[THEMATIC_ANALYSIS_OUTPUT_FIELDS[2]])

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
clusters = pd.DataFrame({'Cluster': kmeans.labels_, 'Text': documents, 'Message_ID': message_ids})  # Include message ID
cluster_terms = clusters.groupby('Cluster').apply(lambda x: terms[np.argmax(np.mean(X[x.index], axis=0))]).reset_index(name='Top Term')

# Initialize Dash app
app = dash.Dash(__name__)

# Define app layout
app.layout = html.Div([
    html.H1("Hierarchical Tree Map Visualization"),
    html.Div(id='display-content'),
    dcc.Graph(id='tree-map'),
    html.Div([
        html.Div(id='word-cloud-container'),
        html.Div(id='message-list-container')
    ]),
    html.Div(id='cluster-info', style={'display': 'none'})
])

# Define callback to update display content
@app.callback(
    Output('display-content', 'children'),
    Input('tree-map', 'clickData')
)
def update_display_content(click_data):
    if click_data is not None:
        selected_term = click_data['points'][0]['label']
        selected_cluster = cluster_terms[cluster_terms['Top Term'] == selected_term]['Cluster'].values[0]
        cluster_texts = clusters[clusters['Cluster'] == selected_cluster]['Text']
        cloud_text = ' '.join(cluster_texts)
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(cloud_text)
        img_stream = io.BytesIO()
        wordcloud.to_image().save(img_stream, format='PNG')
        img_str = "data:image/png;base64," + base64.b64encode(img_stream.getvalue()).decode()
        return html.Img(src=img_str, style={'width': '80%', 'margin': 'auto', 'display': 'block'})

    else:
        return None

# Define callback to update tree map
@app.callback(
    Output('tree-map', 'figure'),
    Input('display-content', 'children')
)
def update_tree_map(_):
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

# Define callback to show message list when clicking on a cluster
@app.callback(
    Output('message-list-container', 'children'),
    Input('tree-map', 'clickData')
)
def show_message_list(click_data):
    if click_data is not None:
        selected_term = click_data['points'][0]['label']
        selected_cluster = cluster_terms[cluster_terms['Top Term'] == selected_term]['Cluster'].values[0]
        cluster_texts = clusters[clusters['Cluster'] == selected_cluster][['Text', 'Message_ID']]  # Include message ID
        message_list = html.Ol([
            html.Li(html.A(f"{row['Text']}", href= MESSAGE_URL + f"{row['Message_ID']}", target="_blank")) for _, row in cluster_texts.iterrows()
        ])
        return message_list
    else:
        return None

if __name__ == '__main__':
    app.run_server(debug=True)
