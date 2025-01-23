import json
import os
import ffmpeg
from aiLoader import loadAI

client = loadAI()

# Takes string, returns an AI description of the original language and translation to English.
def translate(TEXT_ENTITIES):
    PROMPT_PART_1 = "You will be given a 2d array between the <start> and <end> tags of message ids corresponding to messages written in langauges including but not limited to Ukrainian, Russian, and Polish. Your goal is to translate these messages into English. <start>" 
    PROMPT_PART_2 = " <end>. You need to determine two things. The first is your translation to English of text that was between the <start> and <end> tags. The second is a one word description of the language of text that was between the <start> and <end> tags. If the text between the <start> and <end> tags is only whitespace, escape characters, or non-alphanumeric characters, as in not real words, return an empty string for both the translation and the description."
    PROMPT_PART_3 = "Add these two things to the given array. The output of each row of the array should be structured like the example between the <ex> tags. <ex>" 
    
    PROMPT_PART_4 = '{"id" : 1234, "text": "Есть возможность иногда можно получать продовольственную помощь.", "language" : "Russian", "translation" : "It is possible to occasionally receive food assistance."}'

    PROMPT_PART_5 = "<ex> Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters."

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": PROMPT_PART_1 + str(TEXT_ENTITIES) + PROMPT_PART_2 + PROMPT_PART_3 + PROMPT_PART_4 + PROMPT_PART_5}
            ]
        )
        print(completion.choices[0].message.content)
        return json.loads(completion.choices[0].message.content)

    except Exception as e:
        print(f"Error translating text.", e)
        return None
    
def convertToMP4(file):
        stem = os.path.splitext(file)[0]
        convertedFile = (f"{stem}.mp4")

        try:
            # Convert MOV to MP4
            ffmpeg.input(file).output(convertedFile, vcodec="h264", acodec="aac").run()
            print(f"Conversion complete: {convertedFile}")
            return convertedFile

        except Exception as e:
                print("Error converting file to .mp4", e)

def transcribe(file):
    # Convert to mp4 if necessary. Potential TODO: refactor to handle other file types
    fExtension = os.path.splitext(file)[1]
    if fExtension == ".MOV" or fExtension == ".mov":
        file = convertToMP4(file)

    # Transcribe
    try:
        audio_file= open(file, "rb")
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            response_format="text"
        )
        return transcription

    except Exception as e:
        print("Error transcribing audio", e)
        return None