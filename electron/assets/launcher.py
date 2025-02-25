#!/usr/bin/env python
"""
Direct launcher for processJson.py
This script directly executes your main script using execfile-like functionality
"""
import os
import sys
import importlib.util
import runpy

def setup_path():
    """Add necessary directories to the Python path"""
    # Get the directory where the executable is located
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add the base directory and python subdirectory to the path
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    
    python_dir = os.path.join(base_dir, 'python')
    if os.path.exists(python_dir) and python_dir not in sys.path:
        sys.path.insert(0, python_dir)
        print(f"Added {python_dir} to path")
    
    return base_dir, python_dir

def run_main_script():
    """Run the main script directly"""
    base_dir, python_dir = setup_path()
    
    # Path to the main script
    main_script = os.path.join(python_dir, 'processJson.py')
    
    if not os.path.exists(main_script):
        print(f"Error: Main script not found at {main_script}")
        sys.exit(1)
    
    print(f"Running main script: {main_script}")
    
    # Execute the script directly in the current namespace
    try:
        # Method 1: Use runpy
        runpy.run_path(main_script, run_name='__main__')
    except Exception as e:
        print(f"Error running script with runpy: {e}")
        try:
            # Method 2: Import as module and execute
            spec = importlib.util.spec_from_file_location("processJson", main_script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # If the module has a main function, call it
            if hasattr(module, 'main'):
                module.main()
        except Exception as e2:
            print(f"Error running script as module: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    run_main_script()
