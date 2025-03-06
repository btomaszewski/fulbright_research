#!/usr/bin/env python
import os

# Create the hook-src.py file for PyInstaller
hook_py_content = '''from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all for important packages
datas, binaries, hiddenimports = collect_all('spacy')
datas2, binaries2, hiddenimports2 = collect_all('openai')
datas3, binaries3, hiddenimports3 = collect_all('sentence_transformers')

# Combine all collected items
datas.extend(datas2)
datas.extend(datas3)
binaries.extend(binaries2)
binaries.extend(binaries3)
hiddenimports.extend(hiddenimports2)
hiddenimports.extend(hiddenimports3)

# Add more specific hidden imports
hiddenimports.extend([
    'en_core_web_sm',
    'src.frameExtraction',
    'src.videoAnalysis',
    'src.imageAnalysis',
    'src.aiLoader',
    'src.helpers',
    'src.cleanJson',
    'src.vectorImplementation',
    'dotenv',
    'numpy',
    'pandas',
    'json',
    'pathlib',
    'shutil',
    'torch',
    'transformers',
    'PIL',
    'cv2',
    'contractions',
])
'''

# Create the directory if it doesn't exist
os.makedirs("temp_build", exist_ok=True)

# Write the hook-src.py file
with open("temp_build/hook-src.py", "w") as f:
    f.write(hook_py_content)

print("hook-src.py created successfully")