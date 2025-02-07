import os
from pathlib import Path
from imageAnalysis import analyzePhoto
from aiLoader import loadAI

client = loadAI()

# Constants
PROMPT_PART_1 = "Each of the paragraphs in this string between the <start> and <end> tags are descriptions of an image. Each image is a frame from a single video. Use the descriptions of each frame to generate a summary of what the video is depicting. <start>"
PROMPT_PART_2 = "<end> Return back 1 item: the summary of the video in string format. Do not provide any other explanations. Do not refer to the frames in your summary, treat it as a summary of the video as a whole."

# Path to the folder containing the frames
# frameFolder = Path("frames")  # Path to your frame folder

# Loop through frames in the folder
def logResponses(framesDir):
    print("**************")
    print(framesDir)
    print("**************")

    framesDir = Path(framesDir)
    frameNum = 0
    responseLog = ""

    for frame in framesDir.iterdir():
        # Generate the frame path
        frameNum += 1
        framePath = os.path.join(framesDir, f"frame_{frameNum:04d}.png")
        
        # Check if the frame exists
        if not os.path.exists(framePath):
            break

        try:            
            # Call the API (add your OpenAI logic here)
            responseOutput = analyzePhoto(framePath)
            responseLog += f"Frame {frameNum:04d}:\n{responseOutput}\n\n"

            return responseLog

        except Exception as e:
            print(f"Error processing frame {frameNum:04d}: {e}")

        # Increment frame number
        frameNum += 1

# Function to summarize text using OpenAI
def summarize(framesDir):
    responseLog = logResponses(framesDir)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": PROMPT_PART_1 + responseLog + PROMPT_PART_2}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return None