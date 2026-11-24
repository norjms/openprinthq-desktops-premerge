#!/usr/bin/env bash
# Inside a built openprinthq-bambusuite image (tests/run.sh): Wine and the launcher are there, the desktop starts
# Bambu Suite through the launcher, and the image holds no part of Bambu Suite itself.
set -euo pipefail
/opt/wine-stable/bin/wine --version | grep -q '^wine-11\.'
test -x /usr/local/bin/ahi-wine-app
bash -n /usr/local/bin/ahi-wine-app
command -v zenity > /dev/null
grep -q "^/usr/local/bin/ahi-wine-app$" /defaults/autostart /defaults/autostart_wayland
test "$TITLE" = "Bambu Suite"
( . /etc/ahi/app.env; test "$WINE_APP_ID" = bambusuite; test -n "$WINE_APP_URL"; test "$APP_RUN" = /usr/local/bin/ahi-wine-app )
test -x /usr/bin/firefox
if find / -xdev -iname "BambuSuite.exe" 2> /dev/null | grep -q .; then echo "the image holds BambuSuite.exe" >&2; exit 1; fi
