import os
import base64
from dotenv import load_dotenv
from openai import OpenAI

PROMPT_PART_1 = "Summarize this String " 

# Load environment variables from the .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
client = OpenAI(api_key=api_key)


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Path to the folder containing the images
image_folder = "frames"  # Path to your image folder

# Function to summarize text using OpenAI
def summary(text):
    try:
        completion = OpenAI.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": PROMPT_PART_1 + text}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return None

# Open a string to store outputs
response_log = ""

# Loop through images in the folder
image_number = 1
while True:
    # Generate the image path
    image_path = os.path.join(image_folder, f"frame_{image_number:04d}.png")
    
    # Check if the image exists
    if not os.path.exists(image_path):
        break

    try:
        # Encode the image
        base64_image = encode_image(image_path)
        
        # Call the API (add your OpenAI logic here)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What is in this image?",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
        )
        response_output = response.choices[0].message.content.strip()
        response_log += f"Image {image_number:04d}:\n{response_output}\n\n"

    except Exception as e:
        print(f"Error processing image {image_number:04d}: {e}")

    # Increment image number
    image_number += 1

# Summarize the collected responses
summary_text = summary(response_log)

# Print the summary
if summary_text:
    print("Summary of the processed images:")
    print(summary_text)
else:
    print("Failed to generate a summary.")
