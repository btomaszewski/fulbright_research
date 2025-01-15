import os
import subprocess
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
video_path = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/output.mp4"
images_dir = os.path.join(current_dir, "frames")

# Ensure the frames directory exists
os.makedirs(images_dir, exist_ok=True)

# Step 1: Extract frames (1 frame per second) using FFmpeg
def extract_frames(video_path, images_dir):
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", "fps=1",
        f"{images_dir}/frame_%04d.png"
    ]
    subprocess.run(command, check=True)

if __name__ == "__main__":

    # Step 1: Extract frames
    extract_frames(video_path, images_dir)
    print("Frames extracted successfully.")
