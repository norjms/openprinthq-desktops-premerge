#!/usr/bin/env bash
# Run the tests: take the files each app's conversion edits out of its pinned upstream image, test the
# conversions on them, and, with IMAGE set, check a built image has every change in place.
#
#   tests/run.sh                                                 every app's conversion tests
#   APPS=bambustudio tests/run.sh                                one app
#   APPS=bambustudio IMAGE=openprinthq-bambustudio:local tests/run.sh   and its built image
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
docker="${DOCKER:-docker}"
apps="${APPS:-$(cd "$here/apps" && for d in */; do [ -f "$d/convert.py" ] && printf '%s ' "${d%/}"; done)}"

for app in $apps; do
  if grep -q '^FROM .* AS prepared$' "$here/apps/$app/Dockerfile"; then
    # An app installed on a base image: its files come from the base with the app installed.
    $docker build -q --target prepared -f "$here/apps/$app/Dockerfile" -t "openprinthq-$app:prepared" "$here" > /dev/null
    DOCKER="$docker" bash "$here/tests/extract-upstream.sh" "$app" "openprinthq-$app:prepared"
  else
    DOCKER="$docker" bash "$here/tests/extract-upstream.sh" "$app"
  fi
done
APPS="$apps" python3 -m unittest discover -s "$here/tests" -v

if [ -n "${IMAGE:-}" ]; then
  set -- $apps
  [ "$#" -eq 1 ] || { echo "IMAGE needs one app in APPS" >&2; exit 2; }
  echo "checking $IMAGE ($1)"
  $docker run --rm --entrypoint /bin/bash -e APP="$1" -v "$here/apps/$1/image-check.sh:/ahi-app-check.sh:ro" \
    -v "$here/tests/image-check.sh:/ahi-check.sh:ro" "$IMAGE" -c 'bash /ahi-check.sh && bash /ahi-app-check.sh'
  echo "image: every change in place"
fi
