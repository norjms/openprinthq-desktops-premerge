#!/usr/bin/env bash
# Inside a built image (tests/run.sh): every shared change is in place.
set -euo pipefail
test "$DASHBOARD" = artisanhub-dashboard
d=/usr/share/selkies/artisanhub-dashboard
grep -q "ahi/ahi-dashboard.css" $d/index.html
for f in manrope-latin-400-normal manrope-latin-600-normal sora-latin-500-normal jetbrains-mono-latin-400-normal; do
  test -s $d/ahi/fonts/$f.woff2
done
grep -q "<name>ArtisanHub</name>" /defaults/labwc.xml
test -s /usr/share/themes/ArtisanHub/labwc/themerc
test -s /usr/share/themes/ArtisanHub/gtk-3.0/gtk.css
grep -q "^gtk-theme-name=ArtisanHub$" /etc/gtk-3.0/settings.ini
test "$(grep -c '^gtk-theme-name=' /etc/gtk-3.0/settings.ini)" = 1
fc-list : family | grep -i manrope > /dev/null
fc-list : family | grep -i "jetbrains mono" > /dev/null
for s in init-ahi-app init-ahi-files init-ahi-browser svc-ahi-bus svc-ahi-inbox; do
  test -x /etc/s6-overlay/s6-rc.d/$s/run
  test -e /etc/s6-overlay/s6-rc.d/user/contents.d/$s
done
test -e /etc/s6-overlay/s6-rc.d/svc-de/dependencies.d/svc-ahi-bus
test -s /etc/ahi/app.env
( . /etc/ahi/app.env; test -n "$APP_TITLE" )
grep -q "openprinthq-ui.s glass-dark values" /lsiopy/lib/python3.*/site-packages/selkies/stream_server.py
test -s /usr/share/doc/openprinthq-$APP/NOTICE
test -x /usr/local/bin/ahi-open-url
test -x /usr/local/bin/xdg-open
test "$BROWSER" = /usr/local/bin/ahi-open-url
grep -q "x-scheme-handler/https=ahi-browser.desktop" /etc/xdg/mimeapps.list
grep -q "file:///" /usr/lib/firefox*/distribution/policies.json
test -x /usr/bin/firefox
if /usr/local/bin/ahi-open-url file:///etc/passwd 2> /dev/null; then echo "the opener opened a file" >&2; exit 1; fi
# Firefox shares sign-ins across desktops (OPHQ-163): the opener and the desktop's menu use the wrapper.
test -x /usr/local/bin/ahi-firefox
python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())" /usr/local/lib/ahi/ahi_signins.py
grep -q "^exec /usr/local/bin/ahi-firefox " /usr/local/bin/ahi-open-url
if grep -qs "<command>/usr/bin/firefox</command>" /defaults/menu.xml /defaults/menu_wayland.xml; then
  echo "a menu still starts Firefox without the shared sign-ins" >&2; exit 1
fi
