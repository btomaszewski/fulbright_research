import os
import sys

# Fix Python framework handling on macOS
if sys.platform == 'darwin':
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        bundle_dir = sys._MEIPASS
        os.environ['DYLD_FRAMEWORK_PATH'] = bundle_dir