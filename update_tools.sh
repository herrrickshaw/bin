#!/usr/bin/env bash
# update_tools.sh — report (default) or apply updates for plugins, global npm, brew, graphify.
#   update_tools.sh              dry run: only reports what is outdated
#   update_tools.sh --apply      plugins + minor/patch global npm + graphifyy (+ restart its service)
#   --npm-major   also allow major npm bumps (incl. npm itself)
#   --brew        also run `brew upgrade` (touches other tools — off by default)
#   --allow-re2   run the npm install with --allow-scripts=re2
set -uo pipefail

APPLY=0; NPM_MAJOR=0; BREW=0; RE2=0
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;; --npm-major) NPM_MAJOR=1 ;; --brew) BREW=1 ;; --allow-re2) RE2=1 ;;
    -h|--help) sed -n 2,9p "$0"; exit 0 ;;
    *) echo "unknown flag: $a" >&2; exit 2 ;;
  esac
done
run() { if [ "$APPLY" = 1 ]; then echo "+ $*"; "$@"; else echo "[dry-run] $*"; fi; }
hdr() { printf '\n== %s ==\n' "$1"; }

hdr "Claude Code plugins (restart Claude Code to apply)"
if command -v claude >/dev/null; then
  run claude plugin marketplace update
  python3 - <<'EOF' | while read -r p; do run claude plugin update "$p"; done
import json, os
d = json.load(open(os.path.expanduser("~/.claude/plugins/installed_plugins.json")))
for name in d.get("plugins", {}):
    print(name)
EOF
else echo "claude CLI not on PATH — skipped"; fi

hdr "Global npm packages"
npm outdated -g --json 2>/dev/null | python3 -c '
import json, sys
major = sys.argv[1] == "1"
try: d = json.load(sys.stdin)
except Exception: d = {}
for n, v in d.items():
    cur, lat = v.get("current", "?"), v.get("latest", "?")
    is_major = cur.split(".")[0] != lat.split(".")[0]
    tag = "MAJOR" if is_major else "ok"
    if is_major and not major: print(f"# skip {n} {cur} -> {lat} (major)", file=sys.stderr); continue
    print(f"{n}@{lat}")
' "$NPM_MAJOR" > /tmp/npm_upd.$$ 2>/tmp/npm_skip.$$
cat /tmp/npm_skip.$$
if [ -s /tmp/npm_upd.$$ ]; then
  flags=(); [ "$RE2" = 1 ] && flags+=(--allow-scripts=re2)
  # shellcheck disable=SC2046
  run npm install -g "${flags[@]}" $(cat /tmp/npm_upd.$$)
else echo "nothing to update"; fi
rm -f /tmp/npm_upd.$$ /tmp/npm_skip.$$

hdr "graphifyy (pip) + MCP service"
GPIP="$HOME/.venvs/graphifyy/bin/pip"
if [ -x "$GPIP" ]; then
  if "$GPIP" list --outdated 2>/dev/null | grep -i '^graphifyy'; then
    run "$GPIP" install -U graphifyy
    run "$HOME/.venvs/graphifyy/bin/graphify" install --platform claude
    run launchctl kickstart -k "gui/$(id -u)/com.graphify.mcp"
    [ "$APPLY" = 1 ] && echo "note: MCP needs ~20s to load the graph before port 8765 listens"
  else echo "up to date"; fi
else echo "graphify venv not found — skipped"; fi

hdr "Homebrew"
brew outdated 2>/dev/null | head -40
if [ "$BREW" = 1 ]; then run brew upgrade; else echo "(not upgrading — pass --brew to do so)"; fi

hdr "gstack"
if [ -d "$HOME/.claude/skills/gstack/.git" ]; then
  run git -C "$HOME/.claude/skills/gstack" pull --ff-only
  [ "$APPLY" = 1 ] && (cd "$HOME/.claude/skills/gstack" && ./setup --no-team </dev/null 2>&1 | tail -3)
fi

echo; [ "$APPLY" = 1 ] || echo "Dry run only. Re-run with --apply to make changes."
