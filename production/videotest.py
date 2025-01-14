import os
from openai import OpenAI
import ffmpeg
import subprocess 
from dotenv import load_dotenv
from PIL import Image
import io
import base64

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
client = OpenAI(api_key=api_key) 

# Configuration
video_path = "/Users/nataliecrowell/Documents/GitHub/fulbright_research/production/output.mp4"  # Path to your video file
images_dir = "frames"  # Update this to your directory containing the images

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
    print("Frames extracted successfully.")


# Helper function to encode an image file to base64
def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Get all image paths from the folder
image_paths = [os.path.join(images_dir, img) for img in os.listdir(images_dir) if img.endswith(('.png', '.jpg', '.jpeg'))]

# Prepare the images as base64 for the API request
image_data = []
for img_path in image_paths:
    base64_image = encode_image_to_base64(img_path)
    image_data.append({
        "type": "image",
        "image_data": base64_image
    })

# Send the request to OpenAI API with the images
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What are in these images? Is there any difference between them?",
                },
            ] + image_data,  # Add the images to the content
        }
    ],
    max_tokens=300,
)

# Print the response

if __name__ == "__main__":

    # Step 1: Extract frames
    extract_frames(video_path, images_dir)
    print(response.choices[0]) 
