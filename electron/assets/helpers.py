import json
import os
import ffmpeg
from .aiLoader import loadAI

client = loadAI()

# Takes string, returns an AI description of the original language and translation to English.
def translate(text):
    PROMPT_PART_1 = "Translate this text to English <start> " 
    PROMPT_PART_2 = " <end>. Return back two things. The first is your translation to English of text that was between the <start> and <end> tags. The second is a one word description of the language of text that was between the <start> and <end> tags. If the text between the <start> and <end> tags is only whitespace, escape characters, or non-alphanumeric characters, as in not real words, return an empty string for both the translation and the description."
    PROMPT_PART_3 = "Put the two items you return into a JSON structure. Your translation to English of text that was between the <start> and <end> tags placed inside a JSON tag named translation. Your one word description of the language of text that was between the <start> and <end> tags inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters."

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": PROMPT_PART_1 + text + PROMPT_PART_2 + PROMPT_PART_3}
            ]
        )
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
