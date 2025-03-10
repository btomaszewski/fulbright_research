"""
Build utilities for packaging Python application with PyInstaller
"""
import os
import sys
import json
import shutil
import tarfile
import tempfile
import subprocess
import importlib.util
from pathlib import Path


def check_environment():
    """Check Python environment and installed packages"""
    print("Python environment information:")
    print(f"Python version: {sys.version}")
    
    # Check required packages
    required_packages = [
        "certifi", 
        "sentence-transformers", 
        "contractions", 
        "spacy", 
        "geopy",
        "pyinstaller"
    ]
    
    missing_packages = []
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        
        # Install missing packages
        for package in missing_packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("✅ Installed missing packages")
    else:
        print("✅ All required packages are installed")
    
    # Check spaCy model
    try:
        import spacy
        print(f"spaCy version: {spacy.__version__}")
        
        try:
            import en_core_web_sm
            print(f"Model path: {en_core_web_sm.__path__[0]}")
        except ImportError:
            print("❌ spaCy model 'en_core_web_sm' not installed. Installing now...")
            subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
            print("✅ Installed spaCy model 'en_core_web_sm'")
    except ImportError:
        print("❌ Failed to import spaCy")
        sys.exit(1)
    
    # Verify contractions package
    try:
        import contractions
        import pkgutil
        
        data = pkgutil.get_data('contractions', 'data/contractions_dict.json')
        if data:
            print(f'✅ Successfully loaded contractions data file')
            # Parse the JSON to ensure it's valid
            json_data = json.loads(data)
            print(f'✅ Loaded contractions dictionary with {len(json_data)} items')
        else:
            print('❌ Could not load contractions data file')
            print("Reinstalling contractions package...")
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "contractions"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "contractions"])
    except ImportError:
        print("❌ Failed to import contractions package")
        sys.exit(1)


def package_spacy_model():
    """Package spaCy model files as a tarball"""
    print("Packaging spaCy model files...")
    
    try:
        import en_core_web_sm
        
        model_path = en_core_web_sm.__path__[0]
        target_dir = 'spacy_model'
        os.makedirs(target_dir, exist_ok=True)
        tarball_path = os.path.join(target_dir, 'en_core_web_sm.tar.gz')
        
        # Print the model path and files for debugging
        print(f'Original model path: {model_path}')
        print('Files in original model directory:')
        for root, dirs, files in os.walk(model_path):
            for file in files:
                relative_path = os.path.join(os.path.relpath(root, model_path), file)
                print(f'  {relative_path}')
        
        # Create tarball without changing directories (safer for Windows)
        print(f'Creating tarball at: {tarball_path}')
        with tarfile.open(tarball_path, 'w:gz') as tar:
            # Add all files from the model directory with proper arcnames
            for root, dirs, files in os.walk(model_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Calculate relative path for arcname
                    rel_path = os.path.relpath(file_path, model_path)
                    print(f'Adding to tarball: {rel_path}')
                    tar.add(file_path, arcname=rel_path)
        
        print(f'Created spaCy model tarball at {tarball_path}')
        print(f'Tarball size: {os.path.getsize(tarball_path) / 1024 / 1024:.2f} MB')
        
        # For debugging, list the contents of the tarball
        print('Contents of the spaCy model tarball:')
        with tarfile.open(tarball_path, 'r:gz') as tar:
            for member in tar.getmembers():
                print(f'  {member.name} ({member.size} bytes)')
        
        return tarball_path
    except Exception as e:
        print(f"❌ Failed to package spaCy model files: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def check_vector_model(vector_model_package):
    """Check vector model package and compress if needed"""
    print(f"Checking vector model package in {vector_model_package}...")
    
    if not os.path.exists(vector_model_package):
        print(f"❌ Vector model package directory '{vector_model_package}' not found")
        sys.exit(1)
    
    if os.path.exists(os.path.join(vector_model_package, "sentence_transformer.tar.gz")):
        print("✅ Vector model is already compressed")
    else:
        # Check if uncompressed model exists
        sentence_transformer_dir = os.path.join(vector_model_package, "sentence_transformer")
        if os.path.exists(sentence_transformer_dir):
            print("Compressing sentence transformer model...")
            
            try:
                # Create a backup copy of the original directory
                temp_dir = tempfile.mkdtemp()
                print(f"Created temporary directory at: {temp_dir}")
                
                backup_dir = os.path.join(temp_dir, "sentence_transformer_backup")
                print(f"Creating backup at: {backup_dir}")
                
                shutil.copytree(sentence_transformer_dir, backup_dir)
                
                # Create tarball without changing directories
                tarball_path = os.path.join(vector_model_package, "sentence_transformer.tar.gz")
                print(f"Creating tarball at: {tarball_path}")
                
                with tarfile.open(tarball_path, "w:gz") as tar:
                    # Add with arcname to get the right structure
                    tar.add(sentence_transformer_dir, arcname="sentence_transformer")
                
                print("✅ Compressed sentence transformer model")
                
                # We don't need to remove the original directory in Windows version
                # Just keep both the directory and the tarball
                
                # Clean up temp directory
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary directory: {temp_dir}")
                
            except Exception as e:
                print(f"❌ Failed to compress sentence transformer model: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
        else:
            print(f"⚠️ Neither compressed nor uncompressed model found in {vector_model_package}")
            print("Checking contents of vector model package directory:")
            for item in os.listdir(vector_model_package):
                print(f"  {item}")
    
    # Verify required files
    required_files_found = True
    
    if not os.path.exists(os.path.join(vector_model_package, "category_embeddings.json")):
        print("⚠️ Warning: category_embeddings.json not found in vector model package")
        required_files_found = False
    
    if (not os.path.exists(os.path.join(vector_model_package, "sentence_transformer.tar.gz")) and 
        not os.path.exists(os.path.join(vector_model_package, "sentence_transformer"))):
        print("⚠️ Warning: Neither sentence_transformer directory nor compressed archive found")
        required_files_found = False
    
    if not required_files_found:
        print("⚠️ Some required files are missing from vector model package")
        if input("Continue anyway? (y/n): ").lower() != "y":
            print("Aborting build process.")
            sys.exit(1)
        print("Continuing build process despite missing files...")


def check_ner_model(ner_model_package):
    """Check NER model package and prepare for packaging"""
    print(f"Checking NER model package in {ner_model_package}...")
    
    if not os.path.exists(ner_model_package):
        print(f"⚠️ NER model package directory '{ner_model_package}' not found")
        if input("Continue without the NER model? (y/n): ").lower() != "y":
            print("Aborting build process.")
            sys.exit(1)
        print("Continuing build process without NER model...")
        return
    
    # Check if model structure is correct
    print("Checking NER model structure...")
    for item in os.listdir(ner_model_package):
        print(f"  {item}")
    
    # Check if meta.json exists - this is critical for spaCy models
    if os.path.exists(os.path.join(ner_model_package, "meta.json")):
        print("✅ Found meta.json in NER model package")
        
        try:
            # Create a proper compressed model tarball
            print("Creating NER model tarball...")
            
            # First, create a clean temporary directory with just the model files
            temp_ner_dir = tempfile.mkdtemp()
            print(f"Created temporary directory at: {temp_ner_dir}")
            
            # Copy required files to temp directory
            for file in ["meta.json", "config.cfg", "tokenizer", "vocab"]:
                src_path = os.path.join(ner_model_package, file)
                dst_path = os.path.join(temp_ner_dir, file)
                
                if os.path.exists(src_path):
                    print(f"Copying {file} from {src_path} to {dst_path}")
                    if os.path.isfile(src_path):
                        shutil.copy2(src_path, dst_path)
                    elif os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                        
            # Copy ner directory if it exists
            ner_dir = os.path.join(ner_model_package, "ner")
            if os.path.exists(ner_dir):
                print(f"Copying ner directory from {ner_dir} to {os.path.join(temp_ner_dir, 'ner')}")
                shutil.copytree(ner_dir, os.path.join(temp_ner_dir, "ner"))
            
            # Create tarball from temp directory
            original_dir = os.getcwd()
            print(f"Current directory before changing: {original_dir}")
            
            tarball_path = os.path.join(temp_ner_dir, "ner_model.tar.gz")
            print(f"Creating tarball at: {tarball_path}")
            
            # Create tarball without changing directory
            with tarfile.open(tarball_path, "w:gz") as tar:
                print(f"Adding files to tarball from: {temp_ner_dir}")
                for item in os.listdir(temp_ner_dir):
                    if item != "ner_model.tar.gz":  # Skip the tarball itself
                        item_path = os.path.join(temp_ner_dir, item)
                        print(f"Adding to tarball: {item_path}")
                        # Add with arcname to avoid full path in archive
                        tar.add(item_path, arcname=item)
            
            # Copy the tarball to the final location
            final_tarball_path = os.path.join(ner_model_package, "ner_model.tar.gz")
            print(f"Copying tarball to final location: {final_tarball_path}")
            shutil.copy2(tarball_path, final_tarball_path)
            
            # Clean up
            print(f"Cleaning up temporary directory: {temp_ner_dir}")
            shutil.rmtree(temp_ner_dir)
            
            print(f"✅ Created NER model tarball at {final_tarball_path}")
        except Exception as e:
            print(f"❌ Failed to create NER model tarball: {e}")
            import traceback
            traceback.print_exc()
            if input("Continue anyway? (y/n): ").lower() != "y":
                print("Aborting build process.")
                sys.exit(1)
    else:
        print("⚠️ No meta.json found in NER model package. This will likely cause loading errors.")
        if input("Continue anyway? (y/n): ").lower() != "y":
            print("Aborting build process.")
            sys.exit(1)


def create_pyinstaller_files(src_dir, main_script, output_name, vector_model_package, ner_model_package):
    """Create PyInstaller spec and hook files"""
    print("Creating PyInstaller spec and hook files...")
    
    # Create temp directory for build
    os.makedirs("temp_build/src", exist_ok=True)
    
    # Copy all Python scripts to temp_build/src
    for py_file in os.listdir(src_dir):
        if py_file.endswith(".py"):
            shutil.copy2(os.path.join(src_dir, py_file), os.path.join("temp_build/src", py_file))
    
    # Create the hook files
    hooks = {
        "hook-certifi.py": """
from PyInstaller.utils.hooks import collect_data_files
import certifi
import os

# This will collect all certifi's data files
datas = collect_data_files('certifi')

# Add the CA bundle specifically
datas.append((certifi.where(), 'certifi'))
""",
        "hook-sentence_transformers.py": """
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('sentence_transformers')

# Add specific modules that might be missed
hiddenimports.extend([
    'sentence_transformers.models',
    'torch',
    'transformers',
    'numpy',
])
""",
        "hook-contractions.py": """
from PyInstaller.utils.hooks import collect_data_files, collect_all

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
        "hook-geopy.py": """
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('geopy')

# Add specific modules that might be missed
hiddenimports.extend([
    'geopy.geocoders',
    'geopy.geocoders.nominatim',
])
""",
        "hook-src.py": """
from PyInstaller.utils.hooks import collect_all, collect_submodules

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
    
    for hook_name, hook_content in hooks.items():
        with open(os.path.join("temp_build", hook_name), "w") as f:
            f.write(hook_content.strip())
    
    # Create spec file
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import certifi  # Import certifi for SSL certificate path
import os
import contractions
import inspect

block_cipher = None

# Get contractions package path and data files
contractions_path = os.path.dirname(inspect.getfile(contractions))
contractions_data_path = os.path.join(contractions_path, 'data')
contractions_dict_path = os.path.join(contractions_data_path, 'contractions_dict.json')
contractions_slang_path = os.path.join(contractions_data_path, 'slang_dict.json')

# Path to this spec file's directory
spec_dir = os.path.dirname(os.path.abspath(SPEC))

# Define paths relative to spec file
vector_model_path = os.path.join(spec_dir, '..', '{vector_model_package}')
ner_model_path = os.path.join(spec_dir, '..', '{ner_model_package}')
spacy_model_tarball = os.path.join(spec_dir, '..', 'spacy_model/en_core_web_sm.tar.gz')

a = Analysis(
    ['src/wrapper.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/processJson.py', '.'),  # Explicitly include processJson.py in the root
        (spacy_model_tarball, '.'),  # Include spaCy model as a tarball in the root
        (vector_model_path, '{vector_model_package}'),
        (ner_model_path, '{ner_model_package}'),
        (certifi.where(), 'certifi'),  # Include SSL certificates
        (contractions_dict_path, os.path.join('contractions', 'data')),  # Include contractions dictionary
        (contractions_slang_path, os.path.join('contractions', 'data')),  # Include slang dictionary
    ],
    hiddenimports=[
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
        'openai',
        'spacy',
        'geopy',
        'geopy.geocoders',
        'geopy.geocoders.nominatim',
        'sentence_transformers',
        'certifi',
        'tarfile',
        'contractions',
        'contractions.contractions',
        'contractions.data',
        'logging',
    ],
    hookspath=['.'],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='{output_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
)
"""
    
    with open(os.path.join("temp_build", "process.spec"), "w") as f:
        f.write(spec_content)
    
    return os.path.join("temp_build", "process.spec")


def run_pyinstaller(platform_id, target_dir, output_name):
    """Run PyInstaller with the spec file"""
    print("Running PyInstaller...")
    
    # Store original directory
    original_dir = os.getcwd()
    temp_build_dir = os.path.join(original_dir, "temp_build")
    
    try:
        # Run PyInstaller with the spec file
        print(f"Changing to directory: {temp_build_dir}")
        os.chdir(temp_build_dir)
        
        print("Executing PyInstaller...")
        pyinstaller_cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--log-level=INFO", "process.spec"]
        print(f"Command: {' '.join(pyinstaller_cmd)}")
        
        subprocess.check_call(pyinstaller_cmd)
        
        # Determine executable name based on platform
        exe_name = output_name
        if platform_id == "win32":
            exe_name = f"{output_name}.exe"
        
        dist_exe_path = os.path.join(temp_build_dir, "dist", exe_name)
        
        # Verify build success
        if os.path.exists(dist_exe_path):
            print(f"✅ Build successful! Executable found at: {dist_exe_path}")
            
            # Create absolute path for target directory
            target_path = os.path.normpath(os.path.join(original_dir, target_dir))
            print(f"Creating target directory: {target_path}")
            os.makedirs(target_path, exist_ok=True)
            
            # Move executable to final location
            final_exe_path = os.path.join(target_path, exe_name)
            print(f"Copying executable to: {final_exe_path}")
            shutil.copy2(dist_exe_path, final_exe_path)
            
            # Make executable (not needed on Windows)
            if platform_id != "win32":
                print("Setting executable permissions")
                os.chmod(final_exe_path, 0o755)
            
            print(f"Final executable: {final_exe_path}")
            
            # Create a file listing all required files/directories for Electron packaging
            # Use forward slashes in paths for consistency across platforms
            exec_path = f"{target_dir}/{exe_name}".replace("\\", "/")
            
            electron_assets = {
                "pyInstaller": {
                    "executablePath": exec_path,
                    "platform": platform_id
                }
            }
            
            # Write electron-assets.json in the current directory
            assets_path = os.path.join(original_dir, "electron-assets.json")
            print(f"Creating electron-assets.json at: {assets_path}")
            with open(assets_path, "w") as f:
                json.dump(electron_assets, f, indent=2)
            
            # Also create a copy in the project root (parent directory)
            parent_assets_path = os.path.normpath(os.path.join(original_dir, "..", "electron-assets.json"))
            print(f"Creating electron-assets.json copy at: {parent_assets_path}")
            with open(parent_assets_path, "w") as f:
                json.dump(electron_assets, f, indent=2)
            
            # Return to original directory
            os.chdir(original_dir)
            return True
        else:
            print(f"❌ Build failed! Executable not found at: {dist_exe_path}")
            # Check if dist directory exists
            dist_dir = os.path.join(temp_build_dir, "dist")
            if os.path.exists(dist_dir):
                print(f"Contents of dist directory:")
                for item in os.listdir(dist_dir):
                    print(f"  {item}")
            else:
                print(f"Dist directory not found at: {dist_dir}")
            
            os.chdir(original_dir)
            return False
    except Exception as e:
        print(f"❌ PyInstaller failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Always make sure we return to the original directory
        os.chdir(original_dir)
        return False


def clean_up():
    """Clean up temporary build files"""
    print("Cleaning up...")
    
    for path in ["temp_build", "build", "dist"]:
        if os.path.exists(path):
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)


def main():
    """Main build function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python build.py [options]")
        print("Options:")
        print("  --clean-only: Only clean up previous builds without rebuilding")
        return
    
    # Configuration
    src_dir = "python"
    main_script = f"{src_dir}/wrapper.py"
    output_name = "processJson"
    venv_dir = ".venv"
    vector_model_package = "vector_model_package"
    ner_model_package = "ner_model_package"
    
    # Platform detection
    if sys.platform.startswith("win"):
        platform_id = "win32"
    elif sys.platform.startswith("darwin"):
        platform_id = "darwin"
    elif sys.platform.startswith("linux"):
        platform_id = "linux"
    else:
        platform_id = sys.platform
    
    # Fix path with correct separators for the platform
    # Use relative paths that start from the current directory, not parent
    target_dir = f"dist-{platform_id}"
    
    print(f"Starting build process from {os.getcwd()} for platform: {platform_id}")
    
    # Clean previous builds
    print("Cleaning up previous builds...")
    for path in ["build", "dist", target_dir, "spacy_model", "temp_build"]:
        if os.path.exists(path):
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clean-only":
        print("Clean-up complete.")
        return
    
    # Verify vector model package exists
    if not os.path.exists(vector_model_package):
        print(f"❌ Vector model package directory '{vector_model_package}' not found in {os.getcwd()}")
        print("Please ensure the vector model package is in the same directory as this script.")
        sys.exit(1)
    
    # Ensure the target directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    # Activate virtual environment if available
    if os.path.exists(venv_dir):
        print("Virtual environment detected. Note: Python scripts don't automatically activate venvs.")
        print("Make sure to run this script from an activated virtual environment if needed.")
    
    # Check Python and dependencies
    check_environment()
    
    # Package spaCy model
    package_spacy_model()
    
    # Check and prepare vector model
    check_vector_model(vector_model_package)
    
    # Check and prepare NER model
    check_ner_model(ner_model_package)
    
    # Create PyInstaller files
    create_pyinstaller_files(src_dir, main_script, output_name, vector_model_package, ner_model_package)
    
    # Run PyInstaller
    if run_pyinstaller(platform_id, target_dir, output_name):
        # Clean up
        clean_up()
        print("Build process completed successfully.")
    else:
        print("Build process failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()