#!/usr/bin/env bash
# Inside a built openprinthq-bambustudio image (tests/run.sh): Bambu Studio's own changes are in place.
set -euo pipefail
w=/opt/bambustudio/resources/web
grep -q "#172028" $w/guide/css/dark.css
grep -q "#172028" $w/homepage3/css/dark.css
if grep -qi "#3E3E45" $w/guide/css/dark.css $w/homepage3/css/dark.css; then echo "old grey left in dark.css" >&2; exit 1; fi
grep -q 'font-family: Manrope, "system-ui",' $w/guide/css/common.css
test "$TITLE" = "Bambu Studio"
test -x /opt/bambustudio/AppRun
test -x /opt/bambustudio/bin/bambu-studio
