import os
from dotenv import load_dotenv
from openai import OpenAI
import ffmpeg

# Input and output file paths
input_file = "C:/Users/Olivia Croteau/Documents/GitHub/fulbright_research/production/IMG_1238(1).MOV"
output_file = "./output.mp4"

# Convert MOV to MP4
ffmpeg.input(input_file).output(output_file, vcodec="h264", acodec="aac").run()

print(f"Conversion complete: {output_file}")
'''

# Load environment variables from the .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
client = OpenAI(api_key=api_key)

audio_file= open("./audioTestFiles/audio.mp4", "rb")
transcription = client.audio.transcriptions.create(
    model="whisper-1", 
    file=audio_file
)

print(transcription.text)
'''