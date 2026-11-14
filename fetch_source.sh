#!/bin/bash
# Fixed wrapper for fetch_source.py so scheduled (unattended) tasks can allowlist exactly one command:
#   Bash(bash /Users/umashankar/bin/fetch_source.sh *)
# Output always goes under /Users/Shared/source_fetch/<YYYY-MM-DD>/ unless --out is given.
# Deliberately NOT inside /Users/Shared/lit_review: its sync_mirror.sh runs `git add -A` and pushes, and
# fetched PDFs/pages are third-party copyrighted material that must not be republished.
# --out is refused here so the allowlisted command can only ever write to that one folder;
# interactive use that needs another folder calls fetch_source.py directly.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for a in "$@"; do case "$a" in --out|--out=*) echo "fetch_source.sh: --out is not allowed; call fetch_source.py directly" >&2; exit 1 ;; esac; done
exec /usr/bin/python3 -I "$here/fetch_source.py" "$@" --out "/Users/Shared/source_fetch/$(date +%F)"
