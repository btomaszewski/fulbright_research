from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all submodules from your source directory
hiddenimports = [
    'frameExtraction', 
    'videoAnalysis',
    'imageAnalysis',
    'aiLoader',
    'helpers',
    'cleanJson',
    'vectorImplementation',
    'nerImplementation',
    'openai',
    'python-dotenv',
    'numpy',
    'pandas',
    'spacy',
    'en_core_web_sm',
    'sentence_transformers'
]

# If any modules have data files
datas = [] 