#!/usr/bin/env bash
# Runs the weekly paper digest via uv.
# Intended to be called by cron — logs to ~/Documents/papers/digests/logs/

set -euo pipefail

SCRIPT_DIR="$HOME/projects/paper_digest"
LOG_DIR="$HOME/Documents/papers/digest/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/digest-$(date +%Y-%m-%d_%H-%M-%S).log"

echo "=== seshat digest started at $(date) ===" >> "$LOG_FILE"

# Launch Ollama if not already running, then wait for it to be ready
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..." >> "$LOG_FILE"
    ollama serve >> "$LOG_FILE" 2>&1 &
    # Poll until the API is up (max 60s)
    for i in $(seq 1 60); do
        if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "Ollama ready after ${i}s" >> "$LOG_FILE"
            break
        fi
        sleep 1
    done
fi

cd "$SCRIPT_DIR"
"$SCRIPT_DIR/.venv/bin/python" -u -m digest.run >> "$LOG_FILE" 2>&1
echo "=== seshat digest finished at $(date) ===" >> "$LOG_FILE"
