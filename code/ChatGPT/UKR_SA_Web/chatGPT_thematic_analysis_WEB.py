'''
use ChatGPT to conduct thematic and topic analysis  
'''

#C:\Users\BrianT\AppData\Local\Programs\Python\Python310\openai-env\Scripts
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime
import csv
from csv import DictWriter
import pandas as pd
import google_access


#JSON Indexes and Keys
JSON_MESSAGES = "messages"
TEXT_ENTITIES = "text_entities"
TYPE_MESSAGE = "type" #check what kind if message it is - service vs. message



#TODO - move this to a seperate module
#MESSAGE_ID,MESSAGE_FULL_DATE,MESSAGE_DATE_MONTH_DAY_YEAR,MESSAGE_DATE_HOUR_SEC,MESSAGE_FILE_NAME,MESSAGE_SOURCE_LANGUAGE,MESSAGE_DETECTED_LANGUAGE,MESSAGE_TRANSLATED_ENG
MESSAGE_DOCUMENTATION_FIELDS =  ['MESSAGE_ID', 'MESSAGE_FULL_DATE', 'MESSAGE_DATE_MONTH_DAY_YEAR',	'MESSAGE_DATE_HOUR_SEC', 'MESSAGE_FILE_NAME','MESSAGE_SOURCE_LANGUAGE','MESSAGE_DETECTED_LANGUAGE','MESSAGE_TRANSLATED_ENG']
MESSAGE_ID_FIELD = "MESSAGE_ID"
MACHINE_ENG_FIELD = "MESSAGE_TRANSLATED_ENG"



#Error logging for large data processing
ERROR_LOG_FILEPATH = "C:/Users/BrianT/RIT/RESEARCH/Fullbright_Poland/datasets/TG_Help_for_Ukrainians_in_Poland_Full/indiv_messages/error_log.csv"
ERROR_LOG_FIELDS =  ['MESSAGE_ID','ERROR']



MOTIVATION_MESSAGE = "You are a skilled humanitarian analyst who is an expert in conducting thematic analysis of English language texts."

#result JSON tags
RESULT_theme = "theme"
RESULT_topic = "result"

#format for working with Flask, leave off .html
#MESSAGE_URL = "\"http://127.0.0.1:5000/message?num="
MESSAGE_URL = "\"data/message.html?num="


client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key='TODO - get updated',
)

def remove_option_prefix(text, prefix):
    # Check if the text starts with the specified prefix
    if text.startswith(prefix):
        # Remove the prefix from the text
        cleaned_text = text[len(prefix):]  # Use slicing to remove the prefix
        return cleaned_text.strip()  # Strip any leading/trailing whitespace
    else:
        # If the prefix does not exist, return the original text
        return text


def LogError(MessageID, Error):
   with open(ERROR_LOG_FILEPATH, 'a',newline='', encoding="utf-8") as f_object:

      print("logging error") 
      dictwriter_object = DictWriter(f_object, fieldnames=ERROR_LOG_FIELDS)
      ERROR_LOG_dict = {ERROR_LOG_FIELDS[0]:MessageID, ERROR_LOG_FIELDS[1]:Error}

      # Pass the dictionary as an argument to the Writerow()
      dictwriter_object.writerow(ERROR_LOG_dict)

      # Close the file object
      f_object.close()

def constructPrompt (userPrompt, textToAnalyse):
  
    PROMPT_PART_1 = f"Conduct an analysis of this text <start>  {textToAnalyse}. <end> where you are looking for topics related to {userPrompt} in your analysis of the text that was between the <start> and <end> tags."
    PROMPT_PART_2 = f"Return back one of two options. Option 1: A brief 10 word maximum analysis of themes you found directly related to {userPrompt} from the text that was between the <start> and <end> tags." 

    PROMPT_PART_2a = f"If you choose option 1, at the end of your 10 word analysis of the themes, indicate the category of the message in terms of  the purpose of the as per these categories: questions, opinions, personal narratives/stories, legal advice, or other. If you choose the other category for the message indicate what category you would place the message in.  Structure your response to the category of message using this format: (selected category)."
    
    PROMPT_PART_3 = f"Option 2: if you do not find any themes directly related to {userPrompt} in the text that was between the <start> and <end> tags, return the single word 'none'. You must return only one of the two options specified. Do not include the text of the option you selected. Do not return any additional text, descriptions of your process, or information beyond one of the two  options specified."

    # Combine the prompt parts using f-strings
    return f"{PROMPT_PART_1}\n{PROMPT_PART_2}\n{PROMPT_PART_2a}\n{PROMPT_PART_3}"

def ConnectToChatGPT (motivation_message, inputprompt):
   
  completion = client.chat.completions.create(
    model="gpt-3.5-turbo-0613",
    messages=[
      {"role": "system", "content": motivation_message},
      {"role": "user", "content": inputprompt}
      ]
    )
  
  return completion

#send the indentified themes back for a final summary report
#final_message_analysis.setdefault('message_id', []).append(message_id)
#final_message_analysis.setdefault('analysis_results', []).append(final_result)
def GenerateSummaryReport (inputResults, len_inputMessages,user_selected_prompt, len_message_id_topic_not_found,start_date,end_date):

  # Retrieve the length of items associated with the key 'analysis_results'
  length_of_results = len(inputResults['analysis_results'])

  summary_stats = f"<h2>Analysis Summary Report:</h2><p>{len_inputMessages} messages were retrieved from the selected date range of {start_date} to {end_date}. </p> <p>{length_of_results} messages were found to match the <i>\"{user_selected_prompt}\"</i> prompt. </p><p> \n {len_message_id_topic_not_found} messages did not match the prompt."     

  print (summary_stats)

 
  #loop through the results and form a number and results
  # Ensure both lists are of the same length
  if len(inputResults['message_id']) != len(inputResults['analysis_results']):
    raise ValueError("Length of 'message_id' and 'analysis_results' lists must be the same.")


  # Step 1: Split input into smaller chunks
  summaries = []
  output = ""
  html_output = ""
  MAX_CHARACTERS = 1900
  
  motivation = "You are a skilled analyst with particular skills enabled to generate concise summaries of meta-analysis of text that highlight key points that decision makers should know about."

  for i in range(len(inputResults['message_id'])):
    message_id = inputResults['message_id'][i]
    analysis_result = inputResults['analysis_results'][i]
    new_output = f"{message_id}: {analysis_result}\n"
    
    # Check if adding new_output will exceed the character limit
    if len(output) + len(new_output) > MAX_CHARACTERS:
        # Create the prompt for the current chunk and get summary
        prompt = create_summary_prompt(output)
        completion = ConnectToChatGPT(motivation, prompt)
        summaries.append(completion.choices[0].message.content)
        
        # Reset output for next chunk
        output = ""
    
    output += new_output
    html_output += f"<li><a href=\"{MESSAGE_URL}{message_id}\" target=\"_blank\">{message_id}</a>: {analysis_result}</li>\n"

  # Process any remaining output
  if output:
    prompt = create_summary_prompt (output)
    completion = ConnectToChatGPT(motivation, prompt)
    summaries.append(completion.choices[0].message.content)

  # Step 2: Combine summaries and create a final summary prompt
  final_summary_output = "\n".join(summaries)

  final_prompt = (
    f"Please analyze the provided summaries and synthesize them into a single, cohesive meta-analysis. "
    f"Reference the summary sections in your analysis.\n"
    f"{final_summary_output}\n"
    f"Do not just repeat the summaries, but synthesize the key points and common themes. "
    f"You will be creating an HTML report of your findings where you will return two things: "
    f"(1) a no longer than 25 word short summary of the meta-analysis and no other additional information such as descriptions of what you are providing and "
    f"(2) a list with a meta-analysis summary of no more than five common themes and topics that you identify from the summaries. "
    f"The 25-word short summary should be in a basic HTML <p> format, be the first item in your report, and have a title of Executive Summary formatted with an <h2> tag. "
    f"The second item in your report will be an HTML list with no more than five list items that represent your meta-analysis summary of the content you were given to analyze and synthesize. "
    f"You must include a reference to every summary section you think was part of your meta-analysis as well as the specific text of your meta-analysis provided in each list item. "
    f"Each list item should contain the text of the synthesis that you found, supported by references to the summaries. "
    f"Provide the title Common Themes formatted with an <h2> tag to your list. "
    f"Only return the HTML code as your response, focusing on the analysis results and not on providing a coding lesson."
)

  #final_prompt = create_summary_prompt(final_output)

  # Step 3: Run the final summary
  if len(final_prompt) <= 4096:
    final_completion = ConnectToChatGPT(motivation, final_prompt)
    final_result = final_completion.choices[0].message.content
    print(final_result)
  else:
    final_result = f"<b>Prompt too big - meta-summary of results not processed, showing indivudal summary chunks</b><br>{final_summary_output}"
    print(final_result)

  

  #add summary_stats
  final_report = f"{summary_stats} <BR> {final_result} <p><b>Full Results</b></p><ol>{html_output}</ol>"

  file_path = r'C:\Users\BrianT\RIT\RESEARCH\Fullbright_Poland\code\ChatGPT\deployment\output.html'

  with open(file_path, 'w',encoding="utf-8") as file:
    # Write the content string to the file
    file.write(final_report)


#recieves the block of messages selected based on the date range and processes
#inputMessages: Data frame of messages 
#promptID: ID of user selected prompt
#start_date: user selected start date for summary report
#end_date:  user selected end date for summary report
def ProcessSelectedMessages (inputMessages, promptID, start_date,end_date):

  final_message_analysis = {}
  
  message_id_topic_not_found = []



  #print (user_selected_prompt) 

  #convert the entire DataFrame into a dictionary with column names as keys
  dictionary = inputMessages.to_dict(orient='records')

  #loop through the individual messages
  for row in dictionary:
    #print(row[MESSAGE_ID_FIELD],row[MACHINE_ENG_FIELD])

    #get the ChatGPT-translated message from the CSV
    message_id = row[MESSAGE_ID_FIELD]
    message_text = row[MACHINE_ENG_FIELD]

    #get the text of the selected prompt
    user_selected_prompt =  google_access.GetPromptFromID(promptID) 
    full_prompt = constructPrompt(user_selected_prompt, message_text)

    #print (full_prompt)

    completion = ConnectToChatGPT(MOTIVATION_MESSAGE,full_prompt)
    
    final_result = completion.choices[0].message.content
    #print (final_result)
    try:

        #look for any instances of NONE found
        if check_gpt_results (final_result.lower()):
        #if not "none" in final_result.lower():

          #clean out option
          # Define the prefix to be removed
          prefix_to_remove = "Option 1: "
          # Remove the prefix from the input string
          clean_final_result = remove_option_prefix(final_result, prefix_to_remove)       

          #TODO - parse out message category


          final_message_analysis.setdefault('message_id', []).append(message_id)
          final_message_analysis.setdefault('analysis_results', []).append(clean_final_result)
          final_message_analysis.setdefault('orginal_message', []).append(message_text)

        else:
           message_id_topic_not_found.append(message_id)

    #json.decoder.JSONDecodeError
    except Exception as inst:
      LogError(message_id,inst)
      print("error")
     
      continue

 #summary report generation


  GenerateSummaryReport(final_message_analysis,len(inputMessages),user_selected_prompt,len(message_id_topic_not_found),start_date,end_date)

  return (final_message_analysis)

def check_gpt_results(gpt_result):
    # List of phrases indicating no relevant themes found
    no_relevant_substrings = ['none', 'no themes', 'no relevant', 'no direct']

    # Check if any of the no relevant substrings are in the result
    for substring in no_relevant_substrings:
        if substring.lower() in gpt_result.lower():
            print("No relevant themes found")
            return False
    
    # If none of the no relevant substrings were found, assume themes were found
    print("Themes found:", gpt_result)
    return True

def create_summary_prompt(output):


    return (
        f"Please analyze the provided messages and summarize the common themes found among the messages. Reference the message numbers in your analysis.\n"
        f"{output}\n"
        f"Do not just repeat what you have been given, you must review the content and generate a meta-analysis of what you are receiving. Summarize, do not repeat. You will be creating an HTML report of your findings where you will return two things: "
        f"(1) a no longer than 25 word short summary and no other additional information such as descriptions of what you are providing and (2) a list with a meta-analysis summary of no more than five common themes and topics that you identify. "
        f"The 25 short word summary should be in a basic HTML <p> format, be the first item in your report, and have a title of Executive Summary formatted with an <h2> tag. "
        f"The second item in your report will be an HTML list with no more than five list items that represent your meta-analysis summary of the content you were given to do a meta-analysis on and references to every messages that your meta-analysis is based on. "
        f"You must include a reference to every message you think was part of your meta-analysis as well as the specific text of your meta-analysis provided in each list item. "
        f"Each list item should contain the text of the summary that you found. that summary of the text must be supported by message references. "
        f"You must place message references in your list items inside of a HTML anchor tag with the href value set using this specific format: {MESSAGE_URL} followed by the message number that you are referencing and then target=\"_blank\". "
        f"For example, a final list item would like this <li>Several interesting topics <a href={MESSAGE_URL}1234 target=\"_blank\">1234</a>, <a href={MESSAGE_URL}4567 target=\"_blank\">4567</a></li>. "
        f"Provide the title Common Themes formatted with an <h2> tag to your list. You must return both items. Only return the HTML code as your response, I'm looking to get a final result of the analysis not a lesson in coding."
    )





