import base64
from aiLoader import loadAI

client = loadAI()

# Function to encode the frame
def encodeFrame(framePath):
    with open(framePath, "rb") as frameFile:
        return base64.b64encode(frameFile.read()).decode("utf-8")

def analyzeImage(framePath):
    # Encode the frame
    base64Frame = encodeFrame(framePath)

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
                        "image_url": {"url": f"data:image/jpeg;base64,{base64Frame}"},
                    },
                ],
            }
        ],
    )
    
    return response.choices[0].message.content.strip()
