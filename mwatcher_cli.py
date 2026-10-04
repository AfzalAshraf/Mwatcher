#!/usr/bin/env python3
"""
Mwatcher CLI - Entry point for pip installation
"""

import sys
import os

# Add the script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Import and run the main module
from mwatcher import main

if __name__ == "__main__":
    main()
