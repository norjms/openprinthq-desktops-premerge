#!/usr/bin/env bash
# Inside a built openprinthq-crealityprint image (tests/run.sh): Creality Print is there and starts with the desktop.
set -euo pipefail
test -x /opt/crealityprint/AppRun
grep -q "^/opt/crealityprint/AppRun$" /defaults/autostart /defaults/autostart_wayland
test "$TITLE" = "Creality Print"
