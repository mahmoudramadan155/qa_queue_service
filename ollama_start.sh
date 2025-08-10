#!/bin/bash
set -e  # Exit on error
echo "Starting Ollama server..."
ollama serve &
SERVER_PID=$!
sleep 10  # Give server time to start
if ! ollama pull ${OLLAMA_MODEL}; then
    echo "Failed to pull model ${OLLAMA_MODEL}"
    exit 1
fi
wait $SERVER_PID