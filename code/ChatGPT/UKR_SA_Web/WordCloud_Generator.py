#steps

#https://matplotlib.org/stable/users/installing/index.html

from wordcloud import WordCloud
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import os

THEMATIC_ANALYSIS_OUTPUT_FIELDS = ['MESSAGE_ID', 'THEMES', 'TOPICS'] 

ANALYSIS_TYPE = "TOPICS"
FIELD_TO_USE = 0 
TITLE_TO_USE = ANALYSIS_TYPE

if (ANALYSIS_TYPE == "THEMES"):
    FIELD_TO_USE = 1    
elif(ANALYSIS_TYPE == "TOPICS"):
    FIELD_TO_USE = 2

# Get the current directory of the Python script
current_directory = os.path.dirname(os.path.abspath(__file__))

# Construct the relative path to the CSV file
wc_file_path = os.path.join(current_directory, 'img', "wordcloud.png")

#plug in the documents
#remove the words of the actual prompt , userprompt
def GenerateWordClouds (InputDocuments, userPrompt ):

     # Extract items (messages) from the specified key
    items_to_process = InputDocuments['analysis_results']

    #keep lowercase
    words_to_remove = {
        "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
        "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
        "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was",
        "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and",
        "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between",
        "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off",
        "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any",
        "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now", "poland", "option", "options", ".","related", ",","-", "theme", 
        "themes", "text","Ukrainians", "Ukrainian", "questions","question" "opinions", "opinion", "personal", "narratives" "stories", "legal", "advice", "/"
    }

    #add the user query to the words to remove
    # Split the string into individual words and convert to lowercase
    extra_words_to_remove = userPrompt.split()
    lowercase_extra_words_to_remove = [word.lower() for word in extra_words_to_remove]

    # Add lowercase words to words_to_remove set
    words_to_remove.update(lowercase_extra_words_to_remove)


    # Initialize an empty list to store filtered documents
    filtered_documents = []

    # Loop through each document in InputDocuments
    for document in items_to_process:
        # Tokenize the document
        tokens = word_tokenize(document)
    
        # Remove words in the list of words to be removed
        #filtered_tokens = [word for word in tokens if word.lower() not in words_to_remove]
        
        # Filter tokens based on words_to_remove (case-insensitive)
        filtered_tokens = [word for word in tokens if word.lower() not in words_to_remove]


        # Join the filtered tokens back into a single string
        filtered_text = ' '.join(filtered_tokens)
        
        # Append the filtered document to the list of filtered documents
        filtered_documents.append(filtered_text)

    # Join the filtered documents into a single string
    cloud_text = ' '.join(filtered_documents)

    # Generate word cloud
    wordcloud = WordCloud(width = 800, height = 800, 
                background_color ='white', 
                stopwords = stopwords.words('english'), 
                min_font_size = 10).generate(cloud_text)


    # Save the word cloud to an image file
    wordcloud.to_file(wc_file_path)  
