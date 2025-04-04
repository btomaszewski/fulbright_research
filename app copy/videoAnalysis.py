import os
import sys
from pathlib import Path
import logging

# Set up logging
logger = logging.getLogger("json-processor-api")

# Import dependencies at module level
from aiLoader import loadAI
from imageAnalysis import analyzePhoto

# Constants
PROMPT_PART_1 = "Each of the paragraphs in this string between the <start> and <end> tags are descriptions of an image. Each image is a frame from a single video. Use the descriptions of each frame to generate a summary of what the video is depicting. <start>"
PROMPT_PART_2 = "<end> Return back 1 item: the summary of the video in string format. Do not provide any other explanations. Do not refer to the frames in your summary, treat it as a summary of the video as a whole."

# Loop through frames in the folder
def logFrames(framesDir):
    """Process video frames and collect analysis results"""
    framesDir = Path(framesDir)
    frameNum = 0
    responseLog = ""
    
    # Get client once for all frames
    client = loadAI()
    
    logger.info(f"Processing frames in directory: {framesDir}")
    
    # List all frames in the directory
    frame_files = sorted([f for f in framesDir.iterdir() if f.name.startswith("frame_") and f.name.endswith(".png")])
    
    if not frame_files:
        logger.warning(f"No frame files found in {framesDir}")
        return None
    
    logger.info(f"Found {len(frame_files)} frames to process")
    
    # Process each frame
    for frame_file in frame_files:
        try:            
            # Call the API to analyze the frame
            responseOutput = analyzePhoto(str(frame_file), client)
            if responseOutput:
                responseLog += f"Frame {frame_file.name}:\n{responseOutput}\n\n"
                logger.info(f"Processed frame: {frame_file.name}")
            else:
                logger.warning(f"No analysis result for frame: {frame_file.name}")

        except Exception as e:
            logger.error(f"Error processing frame {frame_file.name}: {e}")
    
    if responseLog:
        logger.info(f"Completed processing {len(frame_files)} frames")
        return responseLog
    else:
        logger.warning("No frame analysis data collected")
        return None

# Function to summarize text using OpenAI
def summarize(framesDir, client=None):
    """Generate a summary of video frames"""
    # Get client if not provided
    if client is None:
        client = loadAI()
    
    logger.info(f"Generating summary for frames in: {framesDir}")
    
    # Get frame analysis log
    responseLog = logFrames(framesDir)
    
    if not responseLog:
        logger.warning("No frame data to summarize")
        return None
    
    # Generate summary
    try:
        logger.info("Sending frame descriptions for summarization")
        completion = client.chat.completions.create(
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": PROMPT_PART_1 + responseLog + PROMPT_PART_2}
            ]
        )
        
        summary = completion.choices[0].message.content.strip()
        logger.info(f"Summary generated: {summary[:50]}...")
        return summary
    except Exception as e:
        logger.error(f"Error summarizing video: {e}")
        return None
