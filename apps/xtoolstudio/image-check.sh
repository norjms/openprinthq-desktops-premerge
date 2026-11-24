#!/usr/bin/env bash
# Inside a built openprinthq-xtoolstudio image (tests/run.sh): Wine and the launcher are there, the desktop starts
# xTool Studio through the launcher, and the image holds no part of xTool Studio itself.
set -euo pipefail
/opt/wine-stable/bin/wine --version | grep -q '^wine-11\.'
test -x /usr/local/bin/ahi-wine-app
bash -n /usr/local/bin/ahi-wine-app
command -v zenity > /dev/null
command -v 7z > /dev/null
grep -q "^/usr/local/bin/ahi-wine-app$" /defaults/autostart /defaults/autostart_wayland
test "$TITLE" = "xTool Studio"
( . /etc/ahi/app.env; test "$WINE_APP_ID" = xtoolstudio; test -n "$WINE_APP_URL"; test "$APP_RUN" = /usr/local/bin/ahi-wine-app )
test -x /usr/bin/firefox
if find / -xdev -iname "xTool Studio.exe" 2> /dev/null | grep -q .; then echo "the image holds xTool Studio.exe" >&2; exit 1; fi
test -x /etc/ahi/wine-before-start
python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())" /usr/local/lib/ahi/xtool_consent.py
