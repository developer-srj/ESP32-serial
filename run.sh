#!/bin/bash
PORT=8765

pids=$(sudo lsof -i :$PORT | awk '{print $2}' | grep -E '^[0-9]+$' | uniq)

for pid in $pids; do
    sudo kill -9 $pid
    echo "Terminated process $pid"
done


FILE_PATH="src/index.html"
SERVER_SCRIPT="src/Server.py"

# Start the Python server in the background
echo "Starting Python server..."
python3 "$SERVER_SCRIPT" &

# List of possible browsers in order of preference
BROWSERS=("brave-browser" "google-chrome" "firefox" "chromium-browser" "opera" "lynx")

# Try opening the file with each browser until one succeeds
for BROWSER in "${BROWSERS[@]}"; do
    if command -v "$BROWSER" &> /dev/null; then
        echo "Opening $FILE_PATH with $BROWSER..."
        "$BROWSER" "$FILE_PATH" &> /dev/null &
        exit 0
    fi
done

# If no browser found, use xdg-open
echo "No preferred browser found. Using xdg-open..."
xdg-open "$FILE_PATH" &> /dev/null &
