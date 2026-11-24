# openprinthq-prusaslicer: Debian's PrusaSlicer on linuxserver.io's Selkies base, restyled for OpenPrintHQ by
# apps/prusaslicer/convert.py and common/restyle.py. Built from the repository's root:
#
#   docker build -f apps/prusaslicer/Dockerfile .
#
# The base comes from apps/prusaslicer/upstream.env (the release build passes it as build arguments): its tag and
# the digest that tag must be. PrusaSlicer and Firefox ESR are Debian trixie's packages; PrusaSlicer at the
# version upstream.env names. PrusaSlicer itself is not rebuilt or changed.

# The defaults are upstream.env's values, so a plain build builds the pinned image; the tests check they agree.
ARG UPSTREAM_IMAGE=ghcr.io/linuxserver/baseimage-selkies
ARG UPSTREAM_VERSION=debiantrixie
ARG UPSTREAM_DIGEST=sha256:793fc3628ad6e089aecfd9f862de3ad5d9df05f1db783363c812f77d6541ccc3

# The web fonts for the desktop's page (Manrope, Sora, JetBrains Mono), from the fontsource packages.
FROM node:22-alpine AS fonts
ARG FONTSOURCE_VERSION=5.3.0
WORKDIR /pack
RUN npm pack --silent "@fontsource/manrope@${FONTSOURCE_VERSION}" "@fontsource/sora@${FONTSOURCE_VERSION}" \
      "@fontsource/jetbrains-mono@${FONTSOURCE_VERSION}" \
 && mkdir -p /fonts \
 && for f in *.tgz; do mkdir -p "x/$f" && tar -xzf "$f" -C "x/$f"; done \
 && cp x/*manrope*/package/files/manrope-latin-400-normal.woff2 x/*manrope*/package/files/manrope-latin-500-normal.woff2 \
       x/*manrope*/package/files/manrope-latin-600-normal.woff2 x/*manrope*/package/files/manrope-latin-700-normal.woff2 \
       x/*sora*/package/files/sora-latin-500-normal.woff2 \
       x/*jetbrains*/package/files/jetbrains-mono-latin-400-normal.woff2 /fonts/ \
 && cp x/*manrope*/package/LICENSE /fonts/OFL-Manrope.txt \
 && cp x/*sora*/package/LICENSE /fonts/OFL-Sora.txt \
 && cp x/*jetbrains*/package/LICENSE /fonts/OFL-JetBrainsMono.txt

# The base with PrusaSlicer, Firefox and the fonts installed: what the conversion is applied to, and what the
# tests take the files it edits from (tests/run.sh builds this stage).
FROM ${UPSTREAM_IMAGE}:${UPSTREAM_VERSION}@${UPSTREAM_DIGEST} AS prepared
ARG APP_PACKAGE_VERSION=2.9.2+dfsg-1
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
      "prusa-slicer=${APP_PACKAGE_VERSION}" firefox-esr fonts-manrope fonts-jetbrains-mono \
 && fc-cache -f \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/*
COPY apps/prusaslicer/root /

FROM prepared
ARG APP_VERSION=2.9.2
COPY common /tmp/ahi/common
COPY apps/prusaslicer /tmp/ahi/apps/prusaslicer
COPY --from=fonts /fonts /tmp/ahi/common/files/dashboard/fonts
RUN python3 /tmp/ahi/apps/prusaslicer/convert.py / && rm -rf /tmp/ahi
COPY LICENSE LICENSES apps/prusaslicer/NOTICE /usr/share/doc/openprinthq-prusaslicer/
ENV DASHBOARD=artisanhub-dashboard \
    TITLE=PrusaSlicer \
    NO_GAMEPAD=true \
    PIXELFLUX_WAYLAND=true \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    BROWSER=/usr/local/bin/ahi-open-url
EXPOSE 3001
VOLUME /config
LABEL org.opencontainers.image.title="openprinthq-prusaslicer" \
      org.opencontainers.image.source="https://github.com/norjms/openprinthq-desktops" \
      org.opencontainers.image.description="PrusaSlicer ${APP_VERSION} in a web desktop, in the OpenPrintHQ look, on linuxserver.io's baseimage-selkies" \
      org.opencontainers.image.licenses="GPL-3.0-only AND AGPL-3.0-only" \
      org.opencontainers.image.version="${APP_VERSION}"
