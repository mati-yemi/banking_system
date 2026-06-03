"""
Root launcher for the NeoBank application.

This script lets you run the banking system from the workspace root:

    python app.py

It changes the working directory into banking_system and starts the app.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(ROOT_DIR, 'banking_system')

# Ensure the banking_system package is importable
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

os.chdir(APP_DIR)

from run import app

if __name__ == '__main__':
    app.run()
