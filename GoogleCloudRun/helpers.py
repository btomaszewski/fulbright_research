import json
import os
import sys
import ffmpeg
import logging

# Set up logging
logger = logging.getLogger("json-processor-api")

# Import AI client at module level
from aiLoader import loadAI

def translate(text, client=None):
    """Translate text to English"""
    # Get client if not provided
    if client is None:
        client = loadAI()
        
    PROMPT_PART_1 = "Translate this text to English <start> " 
    PROMPT_PART_2 = " <end>. Return back two things. The first is your translation to English of text that was between the <start> and <end> tags. The second is a one word description of the language of text that was between the <start> and <end> tags. If the text between the <start> and <end> tags is only whitespace, escape characters, or non-alphanumeric characters, as in not real words, return an empty string for both the translation and the description."
    PROMPT_PART_3 = "Put the two items you return into a JSON structure. Your translation to English of text that was between the <start> and <end> tags placed inside a JSON tag named translation. Your one word description of the language of text that was between the <start> and <end> tags inside a JSON tag named language. Do not return any additional text, descriptions of your process or information beyond two items and output format of the tags specified. Do not encapsulate the result in ``` or any other characters."

    try:
        logger.info(f"Translating text: {text[:50]}...")
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": PROMPT_PART_1 + text + PROMPT_PART_2 + PROMPT_PART_3}
            ]
        )
        
        result = json.loads(completion.choices[0].message.content)
        logger.info(f"Translation complete: {result.get('language', 'unknown')}")
        return result

    except Exception as e:
        logger.error(f"Error translating text: {e}")
        return None
    
def convertToMP4(file):
    """Convert video to MP4 format"""
    stem = os.path.splitext(file)[0]
    convertedFile = (f"{stem}.mp4")

    try:
        # Convert MOV to MP4
        logger.info(f"Converting {file} to MP4")
        ffmpeg.input(file).output(convertedFile, vcodec="h264", acodec="aac").run()
        logger.info(f"Conversion complete: {convertedFile}")
        return convertedFile

    except Exception as e:
        logger.error(f"Error converting file to .mp4: {e}")
        return None

def transcribe(file, client=None):
    """Transcribe audio from a file"""
    # Get client if not provided
    if client is None:
        client = loadAI()
        
    # Convert to mp4 if necessary
    fExtension = os.path.splitext(file)[1]
    if fExtension == ".MOV" or fExtension == ".mov":
        logger.info(f"Converting {file} to MP4 for transcription")
        file = convertToMP4(file)
        if not file:
            logger.error("Video conversion failed, cannot transcribe")
            return None

    # Transcribe
    try:
        logger.info(f"Transcribing file: {file}")
        audio_file = open(file, "rb")
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            response_format="text"
        )
        
        logger.info(f"Transcription complete: {transcription[:50]}...")
        return transcription

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return None