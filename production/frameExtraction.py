import os
import subprocess

# Step 1: Extract frames (1 frame per second) using FFmpeg
def extractFrames(videoPath, currentDir):
    imagesDir = os.path.join(currentDir, "frames")

    if not os.path.isfile(videoPath):
        raise FileNotFoundError(f"Video file not found: {videoPath}")

    command = [
        "ffmpeg",
        "-i", videoPath,
        "-vf", "fps=1",
        f"{imagesDir}/frame_%04d.png"
    ]
    subprocess.run(command, check=True)