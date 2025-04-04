import base64
import os
import sys
import logging

# Set up logging
logger = logging.getLogger("json-processor-api")

# Import the AI client at module level
from aiLoader import loadAI

# Function to encode the frame
def encodeFrame(framePath):
    """Encode an image file to base64"""
    try:
        with open(framePath, "rb") as frameFile:
            return base64.b64encode(frameFile.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error opening frame file {framePath}: {e}")
        return None
    
def analyzePhoto(framePath, client=None):
    """Analyze a photo using the OpenAI API"""
    # Get client if not provided
    if client is None:
        client = loadAI()

    # Encode the frame
    base64Frame = encodeFrame(framePath)

    if base64Frame:
        try:
            logger.info(f"Analyzing photo: {framePath}")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image in one sentence.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64Frame}"},
                            },
                        ],
                    }
                ],
            )
            
            analysis = response.choices[0].message.content.strip()
            logger.info(f"Photo analysis complete: {analysis[:50]}...")
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing image {framePath}: {e}")
            return None
    else:
        logger.error(f"Failed to encode image {framePath}")
        return None
