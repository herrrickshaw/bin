#!/usr/bin/env python3
"""Insert or refresh the source-fetch toolkit section in each repo's CLAUDE.md.

Idempotent: the section lives between `<!-- source-fetch-toolkit:v1 ...-->` and `<!-- /source-fetch-toolkit -->`
markers; re-running replaces it in place. Repos without a CLAUDE.md get a new one containing just the section.
Never commits. Usage: add_source_fetch_section.py [--dry-run] <repo_dir> [<repo_dir> ...]
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SECTION = open(os.path.join(HERE, "source_fetch_section.md")).read().strip() + "\n"
BLOCK = re.compile(r"<!-- source-fetch-toolkit:v\d[^>]*-->.*?<!-- /source-fetch-toolkit -->\n?", re.S)


def apply(repo, dry):
    path = os.path.join(repo, "CLAUDE.md")
    if not os.path.isdir(os.path.join(repo, ".git")):
        return "skip (not a git repo)"
    if os.path.exists(path):
        old = open(path).read()
        new = BLOCK.sub(SECTION, old, count=1) if BLOCK.search(old) else old.rstrip("\n") + "\n\n" + SECTION
        action = "unchanged" if new == old else ("updated" if BLOCK.search(old) else "appended")
    else:
        new = "# CLAUDE.md\n\nGuidance for Claude Code sessions working in this repository.\n\n" + SECTION
        action = "created"
    if not dry and action != "unchanged":
        with open(path, "w") as f:
            f.write(new)
    return action


if __name__ == "__main__":
    args = sys.argv[1:]
    dry = "--dry-run" in args
    for repo in [a for a in args if a != "--dry-run"]:
        print(f"{apply(os.path.abspath(os.path.expanduser(repo)), dry):10} {repo}")
