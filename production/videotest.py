import os
from openai import OpenAI
import ffmpeg
import subprocess 
from dotenv import load_dotenv
import whisper 

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
client = OpenAI(api_key=api_key) 

# Configuration
video_path = "output.mp4"  # Path to your video file
frames_dir = "frames"  # Directory to save frames
output_transcription = "transcription.txt"  # Transcription file path


# Ensure the frames directory exists
os.makedirs(frames_dir, exist_ok=True)

# Step 1: Extract frames (1 frame per second) using FFmpeg
def extract_frames(video_path, frames_dir):
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", "fps=1",
        f"{frames_dir}/frame_%04d.png"
    ]
    subprocess.run(command, check=True)
    print("Frames extracted successfully.")

# Step 2: Analyze frames using OpenAI
def analyze_frames(frames_dir):
    api_key = api_key
    descriptions = []
    for frame_file in sorted(os.listdir(frames_dir)):
        frame_path = os.path.join(frames_dir, frame_file)
        # Assuming you have access to OpenAI's image processing capabilities
        with open(frame_path, "rb") as image_file:
            response = OpenAI.Image.create(file=image_file, purpose="analyze")
            description = response.get("description", "No description available.")
            descriptions.append(f"{frame_file}: {description}")
    return descriptions

# Step 3: Transcribe audio using Whisper
def transcribe_audio(video_path):
    model = whisper.load_model("base")
    result = model.transcribe(video_path)
    return result["text"]

# Main script
try:
    print("Extracting frames...")
    extract_frames(video_path, frames_dir)

    print("Analyzing frames...")
    frame_descriptions = analyze_frames(frames_dir)
    with open("frame_descriptions.txt", "w") as f:
        f.write("\n".join(frame_descriptions))
    print("Frame descriptions saved to frame_descriptions.txt.")

    print("Transcribing audio...")
    transcription = transcribe_audio(video_path)
    with open(output_transcription, "w") as f:
        f.write(transcription)
    print(f"Audio transcription saved to {output_transcription}.")

except Exception as e:
    print(f"An error occurred: {e}") 