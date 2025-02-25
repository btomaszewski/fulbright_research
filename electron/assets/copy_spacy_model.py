import sys
import os
import shutil
from pathlib import Path

def copy_spacy_model():
    """Copy spaCy model files to a location for PyInstaller to include."""
    print("Copying spaCy model files...")
    
    try:
        import en_core_web_sm
        source_path = Path(en_core_web_sm.__file__).parent
        print(f"Found model at: {source_path}")
        
        # List the contents to debug
        print("Model directory contents:")
        for item in source_path.glob('*'):
            print(f"  - {item.name} ({'dir' if item.is_dir() else 'file'}) {os.path.getsize(item) if item.is_file() else ''} bytes")
            
            # If this is a directory, check its contents too
            if item.is_dir():
                print(f"    Contents of {item.name}:")
                for subitem in item.glob('*'):
                    print(f"    - {subitem.name} ({'dir' if subitem.is_dir() else 'file'}) {os.path.getsize(subitem) if subitem.is_file() else ''} bytes")
        
        # Look for config.cfg in all subdirectories
        config_paths = list(source_path.glob('**/config.cfg'))
        if config_paths:
            config_path = config_paths[0]
            print(f"Found config.cfg at: {config_path}")
            # Get the actual model directory (parent of config.cfg)
            actual_model_dir = config_path.parent
            print(f"Actual model directory: {actual_model_dir}")
        else:
            print("ERROR: config.cfg not found in any subdirectory")
            return False
        
        # Create target directory
        target_path = Path("spacy_model/en_core_web_sm")
        if target_path.exists():
            shutil.rmtree(target_path)
        target_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Copy the model directory with the config.cfg
        print(f"Copying from {actual_model_dir} to {target_path}")
        shutil.copytree(actual_model_dir, target_path)
        
        # Verify the copy worked
        if (target_path / "config.cfg").exists():
            print(f"Successfully copied model to {target_path}")
            print(f"config.cfg is present: {os.path.getsize(target_path / 'config.cfg')} bytes")
            return True
        else:
            print(f"ERROR: config.cfg not found in copied model")
            return False
            
    except ImportError:
        print("ERROR: en_core_web_sm not installed")
        return False
    except Exception as e:
        print(f"ERROR copying model: {e}")
        return False

if __name__ == "__main__":
    success = copy_spacy_model()
    sys.exit(0 if success else 1)
