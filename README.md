# bin — personal backup helper scripts

A public mirror of two shell scripts from the owner's `~/bin` that mirror `~/Downloads` and a few
archive folders to Dropbox and Google Drive with `rclone`, plus the one-time Google Drive OAuth
setup notes they depend on. For anyone wanting a minimal dual-cloud backup recipe on macOS. The
scripts produce no artefacts beyond rotating log files under `~/.local/var/log/`.

> Status: maintained, partial mirror (2 scripts + 1 setup note; the owner's full `~/bin` is not
> published). Scripts are specific to the owner's remote names and folder layout — adapt before use.

<!-- how-to-use-with-ai -->
> **New here?** See [How to use this repo with AI (Claude, Gemini, ChatGPT)](HOW_TO_USE_WITH_AI.md) — clone it, paste it into an AI tool, and ask in plain English.

## What it does
- `backup_downloads.sh` — `rclone sync ~/Downloads` to `dropbox:Downloads` and `googledrive:Downloads`
  (excluding `.DS_Store`, `.tmp*`, `*.tmp`), appending to `~/.local/var/log/downloads_backup.log`
  and trimming it to the last 100 lines.
- `align_cloud_backups.sh` — for `Downloads` and four `archive/*` folders, syncs Dropbox → Google
  Drive then Google Drive → Dropbox, then logs `rclone du` totals and a recursive file-count
  comparison to `~/.local/var/log/cloud_alignment.log` (kept to 50 lines).
- `GDRIVE_SETUP_COMMANDS.txt` — step-by-step notes for creating your own Google Cloud OAuth client
  and registering it with `rclone config create googledrive drive …` so the Drive remote does not
  depend on rclone's shared client ID.

## Quick start
```bash
git clone https://github.com/herrrickshaw/bin.git
cd bin
brew install rclone                      # or your package manager
rclone config                            # create remotes named "dropbox" and "googledrive"
bash backup_downloads.sh                 # one-way mirror of ~/Downloads to both clouds
```
Follow `GDRIVE_SETUP_COMMANDS.txt` first if you want the Drive remote on your own OAuth client.

## How it works
| Stage | Script | Output |
|---|---|---|
| Mirror `~/Downloads` to both remotes (`rclone sync`, 2 calls) | `backup_downloads.sh` | `~/.local/var/log/downloads_backup.log` |
| Two-pass Dropbox ⇄ Google Drive sync per folder, `--transfers 2 --checkers 2` | `align_cloud_backups.sh` | `~/.local/var/log/cloud_alignment.log` |
| Size totals and file-count match check | `align_cloud_backups.sh` | last lines of the same log |

Both scripts wrap their work in a `{ … } >> "$LOG_FILE" 2>&1` block and rotate the log with
`tail -N > tmp && mv`, so they are safe to run from cron/launchd. They run with `set -eu`; rclone
exit codes are masked by the trailing `| tail`, so a failed sync is visible only in the log.

## Repository layout
| Path | Purpose |
|---|---|
| `backup_downloads.sh` | daily Downloads → Dropbox + Google Drive |
| `align_cloud_backups.sh` | make Dropbox and Google Drive identical for selected folders |
| `GDRIVE_SETUP_COMMANDS.txt` | Google Drive OAuth / rclone remote setup notes |
| `CLAUDE.md` | guidance for AI coding sessions (source-fetching rules) |
| `HOW_TO_USE_WITH_AI.md` | non-programmer guide |
| `graphify-out/` | generated knowledge-graph output |
| `.github/workflows/quality-gates.yml` | gitleaks secret scan on push/PR |

## Configuration
No environment variables. Hard-coded in the scripts:

| Setting | Value | Where |
|---|---|---|
| rclone remote names | `dropbox`, `googledrive` | both scripts |
| Folders aligned | `Downloads`, `archive/masaladeutsch-archive`, `archive/blog-consistency-check`, `archive/Documents`, `archive/website-configs` | `align_cloud_backups.sh` `FOLDERS` |
| Log directory | `~/.local/var/log/` | both scripts |

Secrets: the rclone remotes hold OAuth tokens in rclone's own config (`~/.config/rclone/rclone.conf`),
never in this repo. `GDRIVE_SETUP_COMMANDS.txt` contains only `PASTE_YOUR_…` placeholders and an
obviously fake example (`GOCSPX-abc123xyz`). Do not commit a real client ID/secret.

## Testing
```bash
bash -n backup_downloads.sh align_cloud_backups.sh
```
No automated tests; CI runs only a gitleaks secret scan.

## Limitations and known issues
- **`rclone sync` is destructive**: files deleted (or moved) locally are deleted on the remote on the
  next run, and `align_cloud_backups.sh` propagates deletions in both directions. Never archive or
  evict files into a path that one of these jobs syncs.
- `align_cloud_backups.sh` runs two full syncs per folder; the second pass only matters if the first
  left the clouds unequal (a mismatch asks you to rerun).
- The file-count comparison counts the whole of each remote (`rclone ls -R` on `/`), not just the
  aligned folders, so it can report a mismatch for unrelated content.
- The CI gitleaks job currently fails on the fake example secret in `GDRIVE_SETUP_COMMANDS.txt`
  (line 57, rule `generic-api-key`). It is a placeholder, not a credential; add a gitleaks allowlist
  or reword the example to clear the gate.
- The owner's former `gdrive-backup` script was retired in favour of these rclone scripts
  (commit `fbdd34d`).

## Licence
No licence file yet — all rights reserved.
