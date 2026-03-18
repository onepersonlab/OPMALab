#!/bin/bash
# SciLab-Agents · Data Refresh Loop
# Usage: ./run_loop.sh [interval_seconds]  (default: 15)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTERVAL="${1:-15}"
LOG="/tmp/scilab_refresh.log"
PIDFILE="/tmp/scilab_refresh.pid"
MAX_LOG_SIZE=$((10 * 1024 * 1024))  # 10MB

# Single instance protection
if [[ -f "$PIDFILE" ]]; then
  OLD_PID=$(cat "$PIDFILE" 2>/dev/null)
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "❌ Instance already running (PID=$OLD_PID), exiting"
    exit 1
  fi
  rm -f "$PIDFILE"
fi
echo $$ > "$PIDFILE"

# Graceful exit
cleanup() {
  echo "$(date '+%H:%M:%S') [loop] Received exit signal, cleaning up..." >> "$LOG"
  rm -f "$PIDFILE"
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Log rotation
rotate_log() {
  if [[ -f "$LOG" ]] && (( $(stat -f%z "$LOG" 2>/dev/null || stat -c%s "$LOG" 2>/dev/null || echo 0) > MAX_LOG_SIZE )); then
    mv "$LOG" "${LOG}.1"
    echo "$(date '+%H:%M:%S') [loop] Log rotated" > "$LOG"
  fi
}

echo "🧪 SciLab-Agents Data Refresh Loop (PID=$$)"
echo "   Script Dir: $SCRIPT_DIR"
echo "   Interval: ${INTERVAL}s"
echo "   Log: $LOG"
echo "   PID File: $PIDFILE"
echo "   Press Ctrl+C to stop"

while true; do
  rotate_log
  python3 "$SCRIPT_DIR/sync_from_openclaw_runtime.py" >> "$LOG" 2>&1 || true
  python3 "$SCRIPT_DIR/sync_agent_config.py"          >> "$LOG" 2>&1 || true
  python3 "$SCRIPT_DIR/apply_model_changes.py"        >> "$LOG" 2>&1 || true
  python3 "$SCRIPT_DIR/sync_officials_stats.py"       >> "$LOG" 2>&1 || true
  python3 "$SCRIPT_DIR/refresh_live_data.py"          >> "$LOG" 2>&1 || true
  sleep "$INTERVAL"
done
