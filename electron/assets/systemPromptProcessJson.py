import os
import sys
import json
import shutil
from pathlib import Path
from frameExtraction import extractFrames
from videoAnalysis import logFrames
from imageAnalysis import analyzePhoto
from aiLoader import loadAI
from helpers import translate, transcribe
from cleanJson import cleanJson

client = loadAI()

def processText(texts, textIds, messageData):
    try:
        # Define the static system prompt
        systemPrompt = {
            "role": "system",
            "content": "You are a translator. Translate the given text to English. Return back two things. The first is your translation to English of text. The second is a one word description of the language of text. Put the two items you return into a JSON structure. Your translation to English of text placed inside a JSON tag named translation. Your one word description of the language of inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters. Do not include excape characters or new lines"
        }
        prompts = [systemPrompt]
        responses = [None]

        for text in texts:
            i = texts.index(text)
            # Add the new user query
            userPrompt = {"role": "user", "content": f"{text}"}
            prompts.append(userPrompt)
            
            # Call the OpenAI API
            completion = client.chat.completions.create(
                    model="gpt-4o",
                    store=True,
                    messages=prompts
            )

            response = (completion.choices[0].message.content)
            responses.append(response)

        for message in messageData:
            id = message.get('id')
            if id in textIds:
                i = textIds.index(id)
                translation = responses[i]

                message['TRANSLATION'] = json.loads(translation)
                print(f"{message['id']} translation appended")

        print("translations complete")
    except Exception as e:
        print(f"Error translating file: {e}")

def processVideos(videos, videoIds, messageData, processedDirPath):
    summaryPrompt = {
        "role": "system",
        "content": "You will be given a string containing paragraphs. Each paragraph is a description of an image. Each image is a frame from a single video. Use the descriptions of each frame to generate a summary of what the video is depicting. Return back 1 item: the summary of the video in string format. Do not provide any other explanations. Do not refer to the frames in your summary, treat it as a summary of the video as a whole. If there are specific quotes from the frames in the paragraphs, amke sure they are included in the summary."
    }
    summaryPrompts = [summaryPrompt]
    summaryResponses = [None]


    for video in videos:
        video = os.path.join(processedDirPath, video)

        # VIDEO SUMMARY LOGIC
        framesDir = video + "Frames"
        extractFrames(video, framesDir)
        framesLog = logFrames(framesDir)
        framesPrompt = {"role": "user", "content": f"{framesLog}"}
        summaryPrompts.append(framesPrompt)
        
        completion = client.chat.completions.create(
                model="gpt-4o",
                store=True,
                messages=summaryPrompts
        )
        summaryResponse = (completion.choices[0].message.content)
        summaryResponses.append(summaryResponse)
        print(f"{summaryResponse}")


        for message in messageData:
            id = message.get('id')
            if id in videoIds:
                i = videoIds.index(id)
                summary = summaryResponses[i]

                message['VIDEO_SUMMARY'] = summary
                print(f"{message['id']} + video summary appended")

    print("videos complete")

def process_json_files(raw_json_path, processed_json_path):
    if not os.path.exists(processed_json_path):
        os.makedirs(processed_json_path)

    for dir_name in os.listdir(raw_json_path):
        dir_path = os.path.join(raw_json_path, dir_name)

        if os.path.isdir(dir_path):  # Ensure it's a directory
            dest_dir = os.path.join(processed_json_path, dir_name)

            # Copy the directory structure first
            shutil.copytree(dir_path, dest_dir, dirs_exist_ok=True)
            print(f"Copied directory: {dir_name}")

            # Process each JSON file inside the copied directory
            for filename in os.listdir(dest_dir):
                file_path = os.path.join(dest_dir, filename)

                if filename.endswith('.json') and os.path.isfile(file_path):
                    process_single_json(file_path, processed_json_path)

def process_single_json(file_path, processed_json_path):
    #Reads a JSON file, processes it, and writes back the modified data.
    try:
        try:
            cleanJson(file_path)
            print(f"{file_path} cleaned successfully")
        except Exception as e:
            print(f"Could not clean {file_path}", e)

        
        print(f"Processing file: {file_path}")

        textIds = [None]
        texts = []
        videoIds = [None]
        videos = []

        with open(file_path, 'r', encoding='utf-8') as f:
            jsonData = json.load(f)
            messageData = jsonData.get("messages", [])

        for message in messageData:
            if message.get('text'):
                texts.append(message['text'])
                textIds.append(message['id'])

            if message.get('file'):
                videos.append(message['file'])
                videoIds.append(message['id'])

                video = os.path.join(processed_json_path, (message['file']))
                transcription = transcribe(video)
                message['VIDEO_TRANSCRIPTION'] = transcription
                transcriptionTranslation = translate(transcription)
                message['TRANSCRIPTION_TRANSLATION'] = transcriptionTranslation

            if message.get('photo'):
                photo = os.path.join(processed_json_path, (message['photo']))
                analysis = analyzePhoto(photo)
                message['PHOTO_ANALYSIS'] = analysis

            processText(texts, textIds, messageData)
            processVideos(videos, videoIds, messageData, processed_json_path)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(jsonData, f, ensure_ascii=False, indent=4)

        print(f"Processed: {file_path}")
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")



if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: processJson.py <input_dir> <output_dir>")
        sys.exit(1)

    raw_json_path = sys.argv[1]
    processed_json_path = sys.argv[2]

    process_json_files(raw_json_path, processed_json_path)