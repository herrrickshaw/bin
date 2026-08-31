#!/bin/bash
# Align files between Google Drive and Dropbox
# Ensures both cloud providers have identical content

set -e

LOG_FILE="$HOME/.local/var/log/cloud_alignment.log"
mkdir -p "$(dirname "$LOG_FILE")"

{
  echo "=== Cloud Backup Alignment Started at $(date) ==="

  # Sync folders to align
  FOLDERS=("Downloads" "archive/masaladeutsch-archive" "archive/blog-consistency-check" "archive/Documents" "archive/website-configs")

  for folder in "${FOLDERS[@]}"; do
    echo "Aligning: $folder"

    # Dropbox → Google Drive
    echo "  Step 1: Sync Dropbox → Google Drive"
    rclone sync "dropbox:$folder" "googledrive:$folder" \
      --transfers 2 --checkers 2 --log-level INFO 2>&1 | tail -2

    sleep 1

    # Google Drive → Dropbox (verify bidirectional)
    echo "  Step 2: Verify Google Drive → Dropbox"
    rclone sync "googledrive:$folder" "dropbox:$folder" \
      --transfers 2 --checkers 2 --log-level INFO 2>&1 | tail -2

    echo "  ✓ $folder aligned"
    echo ""
  done

  echo "=== Generating Alignment Report ==="
  echo ""

  echo "Dropbox contents:"
  rclone du -h dropbox:/ 2>/dev/null | tail -1 | awk '{print "  Total: " $0}'
  echo ""

  echo "Google Drive contents:"
  rclone du -h googledrive:/ 2>/dev/null | tail -1 | awk '{print "  Total: " $0}'
  echo ""

  # File count comparison
  echo "File inventory:"
  db_count=$(rclone ls dropbox:/ -R 2>/dev/null | wc -l)
  gd_count=$(rclone ls googledrive:/ -R 2>/dev/null | wc -l)
  echo "  Dropbox files: $db_count"
  echo "  Google Drive files: $gd_count"

  if [ "$db_count" -eq "$gd_count" ]; then
    echo "  ✓ File counts match!"
  else
    echo "  ⚠️  Mismatch detected (rerun to complete)"
  fi

  echo ""
  echo "✓ Alignment completed at $(date)"

} >> "$LOG_FILE" 2>&1

# Keep log to last 50 lines
tail -50 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"

echo "✓ Done. Log: $LOG_FILE"
