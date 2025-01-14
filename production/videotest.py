import os
from openai import OpenAI
import ffmpeg
import subprocess 
from dotenv import load_dotenv

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

# Step 2: Analyze the frame using OpenAI's GPT model (text-based analysis)
def analyze_frame_with_openai(frame_path):
    # Open the image and convert it to a byte array
    with open(frame_path, "rb") as image_file:
        image_data = image_file.read()

    # Send the image data to OpenAI for analysis
    response = client.chat.completions.create(
        model="gpt-4",  # Use GPT-4 or the appropriate model for your use case
        messages=[
            {
                "role": "user",
                "content": "Describe the content of this image in detail."
            }
        ],
        max_tokens=150  # Limit the output size
    )

    description = response.choices[0].message['content'].strip()
    return description

# Step 3: Generate a summary description of the video by analyzing all frames
def analyze_video_frames(frames_dir):
    descriptions = []
    # List all frame images in the directory
    frame_files = sorted(os.listdir(frames_dir))  # Sort to maintain chronological order

    # Analyze each frame
    for frame in frame_files:
        frame_path = os.path.join(frames_dir, frame)
        print(f"Analyzing frame: {frame_path}")
        
        # Get description of the frame from OpenAI
        frame_description = analyze_frame_with_openai(frame_path)
        descriptions.append(frame_description)

    # Combine all frame descriptions into a single summary
    video_summary = "The video contains the following scenes:\n" + "\n".join(descriptions)
    return video_summary

# Main function to execute the script
if __name__ == "__main__":
    # Step 1: Extract frames
    extract_frames(video_path, frames_dir)

    # Step 2: Analyze all frames and generate a video summary
    video_description = analyze_video_frames(frames_dir)

    # Step 3: Save the transcription to a text file
    with open(output_transcription, "w") as transcription_file:
        transcription_file.write(video_description)

    print("Video description and transcription complete.")
