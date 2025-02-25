import os
import sys

if sys.platform == 'darwin':
    if getattr(sys, 'frozen', False):
        os.environ['DYLD_LIBRARY_PATH'] = os._MEIPASS
