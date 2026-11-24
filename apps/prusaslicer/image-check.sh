#!/usr/bin/env bash
# Inside a built openprinthq-prusaslicer image (tests/run.sh): PrusaSlicer is there and starts with the desktop.
set -euo pipefail
test -x /usr/bin/prusa-slicer
grep -q "^/usr/bin/prusa-slicer$" /defaults/autostart /defaults/autostart_wayland
test "$TITLE" = "PrusaSlicer"
test -x /usr/bin/firefox
