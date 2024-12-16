from flask import Flask, render_template, request, send_file, send_from_directory
import openai
from openai import OpenAI
import csv_access
import chatGPT_thematic_analysis_WEB
import chatGPT_message_geocoding_WEB
import WordCloud_Generator
import google_access
import pandas as pd


app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = 'TODO - get updated'

client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key='TODO - get updated',
)




@app.route('/')
def home():

    # prompts loads from  Google Sheets
    #prompt_data = pd.DataFrame(google_access.GetPromptsFromGoogleSheet)
    prompt_data = google_access.GetPromptsFromGoogleSheet()

    # Pass prompt data to the template to populate the selection box
    # Create a list of tuples from multiple columns
    prompt_items = list(zip(prompt_data['ID'], prompt_data['PROMPT_NAME']))
    
    ## Pass the list of tuples to the template, along with the length of the list
    return render_template('index.html', items=prompt_items, len=len)

#The message route responds to requests for http://127.0.0.1:5000/message.html.
#Inside the message route, we use send_from_directory to send the message.html file from the static directory.

@app.route('/message')
def message():
    num = request.args.get('num', default='', type=str)
    return send_from_directory('static', 'message.html')

#run the chat GPT open query
@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    #response = openai.Completion.create(
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0613",
        messages=[
            
          {"role": "user", "content": user_input}
          ],

        max_tokens=50
    )
    
    return  response.choices[0].message.content.strip()
   

#run the chat GPT query
@app.route('/csvqry', methods=['POST'])
def csvqry():
    start_date = request.form['start-date']
    end_date = request.form['end-date']
    requested_prompt = request.form['selected_item']

    selected_dates = csv_access.GetCSVData(start_date,end_date)

    #after data from date range is selected, send on for processsing by ChatGPT
    analysis_results =  chatGPT_thematic_analysis_WEB.ProcessSelectedMessages (selected_dates, requested_prompt,start_date,end_date)

    #geocode the results
    chatGPT_message_geocoding_WEB.GeoCodeMessage(analysis_results)

    #send to word cloud
    #get the text of the selected prompt- could do this better, making an extra web call
    user_selected_prompt =  google_access.GetPromptFromID(requested_prompt)  

    WordCloud_Generator.GenerateWordClouds (analysis_results,user_selected_prompt) 
    return send_file('img/wordcloud.png', mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)

