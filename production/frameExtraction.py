import os
import subprocess

# Extract frames (1 frame per second) using FFmpeg
def extractFrames(videoPath, framesDir):
    os.makedirs(framesDir, exist_ok=True)

    if not os.path.isfile(videoPath):
        raise FileNotFoundError(f"Video file not found: {videoPath}")

    command = [
        "ffmpeg",
        "-i", videoPath,
        "-vf", "fps=1",
        f"{framesDir}/frame_%04d.png"
    ]
    subprocess.run(command, check=True)