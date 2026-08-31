#!/bin/bash
# Daily Downloads backup to Dropbox and Google Drive
# Syncs all files from ~/Downloads to remote storage

set -e

LOG_FILE="$HOME/.local/var/log/downloads_backup.log"
mkdir -p "$(dirname "$LOG_FILE")"

{
  echo "=== Downloads backup started at $(date) ==="

  # Sync to Dropbox
  echo "Syncing to Dropbox..."
  rclone sync ~/Downloads dropbox:Downloads \
    --exclude=".DS_Store" \
    --exclude=".tmp*" \
    --exclude="*.tmp" \
    --log-level INFO \
    --stats-one-line \
    2>&1 | tail -3

  # Sync to Google Drive
  echo "Syncing to Google Drive..."
  rclone sync ~/Downloads googledrive:Downloads \
    --exclude=".DS_Store" \
    --exclude=".tmp*" \
    --exclude="*.tmp" \
    --log-level INFO \
    --stats-one-line \
    2>&1 | tail -3

  echo "✓ Backup completed at $(date)"
  echo "Files backed up to: dropbox:Downloads and googledrive:Downloads"

} >> "$LOG_FILE" 2>&1

# Keep log to last 100 lines
tail -100 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
