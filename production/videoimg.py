import os
import base64
from dotenv import load_dotenv
from openai import OpenAI

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

# Open a text file in write mode to capture the output
output_file_path = "output_log.txt"
with open(output_file_path, 'w') as file:

    # Loop through images in the folder
    image_number = 1
    while True:
        # Ensure the filename has 4 digits for the image number
        image_path = os.path.join(image_folder, f"frame_{image_number:04d}.png")

        # Check if the image exists
        if not os.path.exists(image_path):
            break
        
        # Correctly call the encode_image function
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

        # Capture the output (what would be printed)
        response_output = str(response.choices[0])  # Assuming the response has this structure

        # Write the response into the output file
        file.write(f"Image {image_number:04d}: {response_output}\n")

        # Increment the image number
        image_number += 1

print(f"Output saved to {output_file_path}")
