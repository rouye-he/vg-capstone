#!/bin/bash
# Install role workspaces, shared skills and synthetic data onto this Mac, then apply the role config.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p ~/.openclaw/skills ~/.openclaw/workspace/data
for s in meeting-scheduler expense-ledger; do rm -rf ~/.openclaw/skills/$s; cp -R "$HERE/skills/$s" ~/.openclaw/skills/; done
rm -rf ~/.openclaw/workspace/skills/meeting-scheduler      # now lives in the shared root
cp "$HERE"/data/*.json ~/.openclaw/workspace/data/
cp "$HERE/workspaces/main/SOUL.md" ~/.openclaw/workspace/SOUL.md
for w in eng finance ops guest; do mkdir -p ~/.openclaw/workspace-$w; cp "$HERE/workspaces/$w/"*.md ~/.openclaw/workspace-$w/; done
OUT=$(python3 "$HERE/roles/gen_config.py" | tee /dev/stderr | sed -n "s/^OUT=//p")
openclaw config patch --file "$OUT"
openclaw config validate
openclaw agents list --bindings
