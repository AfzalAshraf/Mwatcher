#!/bin/bash

# Mwatcher - Universal Movie Watcher Shell Wrapper
# Usage: ./mwatcher.sh "Movie Name" [options]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/mwatcher.py"

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python is not installed. Please install Python 3."
    exit 1
fi

# Check if pip is available for dependencies
if ! $PYTHON_CMD -c "import yt_dlp, requests, bs4" &> /dev/null; then
    echo "Installing required dependencies..."
    pip install yt-dlp requests beautifulsoup4 || {
        echo "Failed to install dependencies. Please install manually:"
        echo "  pip install yt-dlp requests beautifulsoup4"
        exit 1
    }
fi

# Run the Python script with all arguments
exec $PYTHON_CMD "$PYTHON_SCRIPT" "$@"
