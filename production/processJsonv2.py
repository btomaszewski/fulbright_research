import os
import shutil
import json
from pathlib import Path
from frameExtraction import extractFrames
from videoAnalysis import logFrames, summarize
from imageAnalysis import analyzeImage
from aiLoader import loadAI
from helpers import translate, transcribe
#from thematicAnalysis import writeThemes
from cleanJson import cleanJson

client = loadAI()

# cleanFile = "../testCode&Data/data/cleanJsonTestChat/cleanResult.json"

rawJsonDir = Path("./rawJson")
processedJsonDir = Path("./processedJson")
processedJsonDir.mkdir(exist_ok=True)
currentDir = os.path.dirname(os.path.abspath(__file__)) # currentDir = production


def processText(texts, textIds, messageData):
    # Define the static system prompt
    systemPrompt = {
        "role": "system",
        "content": "You are a translator. Translate the given text to English. Return back two things. The first is your translation to English of text. The second is a one word description of the language of text. Put the two items you return into a JSON structure. Your translation to English of text placed inside a JSON tag named translation. Your one word description of the language of inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters. Do not include excape characters or new lines"
    }
    prompts = [systemPrompt]
    responses = [None]

    for text in texts:
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

def processVideos(videos, videoIds, messageData, processedDirPath):
    summaryPrompt = {
        "role": "system",
        "content": "You will be given a string containing paragraphs. Each paragraph is a description of an image. Each image is a frame from a single video. Use the descriptions of each frame to generate a summary of what the video is depicting. Return back 1 item: the summary of the video in string format. Do not provide any other explanations. Do not refer to the frames in your summary, treat it as a summary of the video as a whole."
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
        # *******************

        # VIDEO TRANSCRIPTION LOGIC
        
        # *******************


        for message in messageData:
            id = message.get('id')
            if id in videoIds:
                i = videoIds.index(id)
                summary = summaryResponses[i]

                message['VIDEO_SUMMARY'] = summary



chatsToProcess = set()

def main():
    for chatExportDir in rawJsonDir.iterdir():
        if chatExportDir.is_dir() and chatExportDir.name not in chatsToProcess:
            chatsToProcess.add(chatExportDir.name)

    # Process files
    for chatDir in chatsToProcess:
        chatDirPath = os.path.join(rawJsonDir, chatDir)
        chatDir = f"{chatDir}Processed"
        processedDirPath = os.path.join(processedJsonDir, chatDir)
        shutil.copytree(chatDirPath, processedDirPath)
        
        resultJson = Path(processedDirPath) / "result.json"  # Construct the path   
        if resultJson.is_file():  # Check if result.json exists
            
            # clean json
            try:
                cleanJson(resultJson)
                print(f"{resultJson} cleaned successfully")
            except Exception as e:
                print(f"Could not clean {resultJson}", e)

            
            print(f"Processing file: {resultJson.name}")

            textIds = [None]
            texts = []
            videoIds = [None]
            videos = []

            with open(resultJson, 'r', encoding='utf-8') as f:
                jsonData = json.load(f)
                messageData = jsonData.get("messages", [])

            for message in messageData:
                if message.get('text'):
                    texts.append(message['text'])
                    textIds.append(message['id'])
                if message.get('file'):
                    videos.append(message['file'])
                    videoIds.append(message['id'])

            #processText(texts, textIds, messageData)

            processVideos(videos, videoIds, messageData, processedDirPath)
            

    # Write messages to destination file
    with open(resultJson, 'w', encoding='utf-8') as f:
        json.dump(jsonData, f, ensure_ascii=False, indent=4)
            

main()