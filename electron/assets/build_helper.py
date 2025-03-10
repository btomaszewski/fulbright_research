"""
Helper script for Windows build process to handle operations that are difficult in batch.
"""
import os
import tarfile
import shutil
import sys
import json
import argparse

def create_tarball(source_dir, output_file):
    """Create a tarball from a directory."""
    print(f"Creating tarball from {source_dir} to {output_file}")
    with tarfile.open(output_file, 'w:gz') as tar:
        # Change to the source directory to create a tarball with the right structure
        original_dir = os.getcwd()
        try:
            os.chdir(source_dir)
            for root, dirs, files in os.walk('.'):
                for file in files:
                    file_path = os.path.join(root, file)
                    print(f'Adding to tarball: {file_path}')
                    tar.add(file_path)
        finally:
            os.chdir(original_dir)
    
    print(f"Created tarball at {output_file}")
    print(f"Tarball size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")
    
    # For debugging, list the contents of the tarball
    print('Contents of the tarball:')
    with tarfile.open(output_file, 'r:gz') as tar:
        for member in tar.getmembers():
            print(f'  {member.name} ({member.size} bytes)')

def package_spacy_model():
    """Package the spaCy model as a tarball."""
    import en_core_web_sm
    
    model_path = en_core_web_sm.__path__[0]
    target_dir = 'spacy_model'
    os.makedirs(target_dir, exist_ok=True)
    tarball_path = os.path.join(target_dir, 'en_core_web_sm.tar.gz')
    
    print(f'Original model path: {model_path}')
    print('Files in original model directory:')
    for root, dirs, files in os.walk(model_path):
        for file in files:
            relative_path = os.path.join(os.path.relpath(root, model_path), file)
            print(f'  {relative_path}')
    
    create_tarball(model_path, tarball_path)
    return tarball_path

def compress_vector_model(vector_model_dir):
    """Compress the sentence transformer model."""
    model_path = os.path.join(vector_model_dir, 'sentence_transformer')
    output_path = os.path.join(vector_model_dir, 'sentence_transformer.tar.gz')
    
    if not os.path.exists(model_path):
        print(f"Error: Sentence transformer model not found at {model_path}")
        return False
    
    # Make a backup first
    temp_dir = os.path.join(os.environ.get('TEMP', os.getcwd()), f'temp_model_{os.getpid()}')
    os.makedirs(temp_dir, exist_ok=True)
    shutil.copytree(model_path, os.path.join(temp_dir, 'sentence_transformer'))
    
    # Create the tarball
    create_tarball(model_path, output_path)
    
    # Move backup back to original location for continued use outside of packaging
    if os.path.exists(os.path.join(vector_model_dir, 'sentence_transformer')):
        shutil.rmtree(os.path.join(vector_model_dir, 'sentence_transformer'))
    shutil.copytree(os.path.join(temp_dir, 'sentence_transformer'), os.path.join(vector_model_dir, 'sentence_transformer'))
    
    return True

def package_ner_model(ner_model_dir):
    """Package the NER model as a tarball."""
    output_path = os.path.join(ner_model_dir, 'ner_model.tar.gz')
    
    # Create a clean temporary directory with just the model files
    temp_dir = os.path.join(os.environ.get('TEMP', os.getcwd()), f'ner_model_{os.getpid()}')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Copy required files to temp directory
    for item in ['meta.json', 'config.cfg', 'tokenizer', 'vocab', 'ner']:
        item_path = os.path.join(ner_model_dir, item)
        if os.path.isfile(item_path):
            shutil.copy2(item_path, os.path.join(temp_dir, os.path.basename(item_path)))
        elif os.path.isdir(item_path):
            shutil.copytree(item_path, os.path.join(temp_dir, os.path.basename(item_path)))
    
    # Create tarball from temp directory
    create_tarball(temp_dir, output_path)
    
    # Clean up
    shutil.rmtree(temp_dir)
    
    return output_path

def verify_contractions_package():
    """Verify that the contractions package is installed correctly."""
    import pkgutil
    import json
    try:
        import contractions
        data = pkgutil.get_data('contractions', 'data/contractions_dict.json')
        if data:
            print('✅ Successfully loaded contractions data file')
            # Parse the JSON to ensure it's valid
            json_data = json.loads(data)
            print(f'✅ Loaded contractions dictionary with {len(json_data)} items')
            return True
        else:
            print('❌ Could not load contractions data file')
            return False
    except Exception as e:
        print(f'❌ Error verifying contractions package: {e}')
        return False

def create_pyinstaller_hooks(output_dir):
    """Create PyInstaller hook files in the specified directory."""
    hooks = {
        'hook-certifi.py': """from PyInstaller.utils.hooks import collect_data_files
import certifi
import os

# This will collect all certifi's data files
datas = collect_data_files('certifi')

# Add the CA bundle specifically
datas.append((certifi.where(), 'certifi'))
""",
        'hook-sentence_transformers.py': """from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('sentence_transformers')

# Add specific modules that might be missed
hiddenimports.extend([
    'sentence_transformers.models',
    'torch',
    'transformers',
    'numpy',
])
""",
        'hook-contractions.py': """from PyInstaller.utils.hooks import collect_data_files, collect_all

# Collect all data files for contractions package
datas, binaries, hiddenimports = collect_all('contractions')

# Add explicit data file
import os
import contractions
import inspect

package_path = os.path.dirname(inspect.getfile(contractions))
data_path = os.path.join(package_path, 'data')

if os.path.exists(data_path):
    # Add all files in the data directory
    for file in os.listdir(data_path):
        full_path = os.path.join(data_path, file)
        if os.path.isfile(full_path):
            datas.append((full_path, os.path.join('contractions', 'data')))
            print(f"Added data file: {full_path}")
else:
    print(f"Warning: Contractions data directory not found at {data_path}")
""",
        'hook-geopy.py': """from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('geopy')

# Add specific modules that might be missed
hiddenimports.extend([
    'geopy.geocoders',
    'geopy.geocoders.nominatim',
])
""",
        'hook-src.py': """from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all for important packages
datas, binaries, hiddenimports = collect_all('spacy')
datas2, binaries2, hiddenimports2 = collect_all('openai')
datas3, binaries3, hiddenimports3 = collect_all('sentence_transformers')
datas4, binaries4, hiddenimports4 = collect_all('certifi')
datas5, binaries5, hiddenimports5 = collect_all('contractions')
datas6, binaries6, hiddenimports6 = collect_all('geopy')

# Combine all collected items
datas.extend(datas2)
datas.extend(datas3)
datas.extend(datas4)
datas.extend(datas5)
datas.extend(datas6)
binaries.extend(binaries2)
binaries.extend(binaries3)
binaries.extend(binaries4)
binaries.extend(binaries5)
binaries.extend(binaries6)
hiddenimports.extend(hiddenimports2)
hiddenimports.extend(hiddenimports3)
hiddenimports.extend(hiddenimports4)
hiddenimports.extend(hiddenimports5)
hiddenimports.extend(hiddenimports6)

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
    'src.nerImplementation',
    'src.processJson',
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
    'tempfile',
    'subprocess',
    'certifi',
    'tarfile',
    'sentence_transformers.models',
    'contractions',
    'contractions.contractions',
    'geopy',
    'geopy.geocoders',
    'geopy.geocoders.nominatim',
    'logging',
])
"""
    }
    
    for filename, content in hooks.items():
        with open(os.path.join(output_dir, filename), 'w') as f:
            f.write(content)
    
    print(f"Created PyInstaller hooks in {output_dir}")

def main():
    """Main function to run the build helper."""
    parser = argparse.ArgumentParser(description='Helper script for Windows build process')
    parser.add_argument('--action', choices=['package_spacy', 'compress_vector', 'package_ner', 'verify_contractions', 'create_hooks'], 
                        help='Action to perform')
    parser.add_argument('--dir', help='Directory to operate on (for vector or NER model)')
    parser.add_argument('--output', help='Output directory for hooks')
    
    args = parser.parse_args()
    
    if args.action == 'package_spacy':
        package_spacy_model()
    elif args.action == 'compress_vector':
        if not args.dir:
            print("Error: --dir argument is required for compress_vector action")
            return 1
        compress_vector_model(args.dir)
    elif args.action == 'package_ner':
        if not args.dir:
            print("Error: --dir argument is required for package_ner action")
            return 1
        package_ner_model(args.dir)
    elif args.action == 'verify_contractions':
        verify_contractions_package()
    elif args.action == 'create_hooks':
        if not args.output:
            print("Error: --output argument is required for create_hooks action")
            return 1
        create_pyinstaller_hooks(args.output)
    else:
        print("Error: Please specify an action")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())