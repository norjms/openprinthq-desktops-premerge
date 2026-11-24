# openprinthq-eufymakestudio: Wine on linuxserver.io's Selkies base, restyled for OpenPrintHQ by apps/eufymakestudio/convert.py
# and common/restyle.py, to run eufyMake's eufyMake Studio for Windows. Built from the repository's root:
#
#   docker build -f apps/eufymakestudio/Dockerfile .
#
# The base comes from apps/eufymakestudio/upstream.env (the release build passes it as build arguments): its tag and the
# digest that tag must be. Wine is WineHQ's package at the version upstream.env names, from WineHQ's repository,
# whose signing key is checked against its published fingerprint. The image holds no part of eufyMake Studio:
# common/wine/ahi-wine-app downloads eufyMake's own installer when the desktop first starts (apps/eufymakestudio/app.env).

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

# The base with Wine, Firefox and the fonts installed: what the conversion is applied to, and what the tests take
# the files it edits from (tests/run.sh builds this stage).
FROM ${UPSTREAM_IMAGE}:${UPSTREAM_VERSION}@${UPSTREAM_DIGEST} AS prepared
ARG APP_PACKAGE_VERSION=11.0.0.0~trixie-1
# The fingerprint of WineHQ's repository signing key, as WineHQ publishes it.
ARG WINEHQ_SIGNER=D43F640145369C51D786DDEA76F1A20FF987672F
RUN dpkg --add-architecture i386 \
 && mkdir -p /etc/apt/keyrings \
 && curl -fsSL -o /tmp/winehq.key https://dl.winehq.org/wine-builds/winehq.key \
 && gpg --show-keys --with-colons /tmp/winehq.key | grep -q "^fpr:::::::::${WINEHQ_SIGNER}:$" \
 && gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key /tmp/winehq.key \
 && printf 'Types: deb\nURIs: https://dl.winehq.org/wine-builds/debian\nSuites: trixie\nComponents: main\nArchitectures: amd64 i386\nSigned-By: /etc/apt/keyrings/winehq-archive.key\n' \
      > /etc/apt/sources.list.d/winehq.sources \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install --install-recommends -y \
      "winehq-stable=${APP_PACKAGE_VERSION}" "wine-stable=${APP_PACKAGE_VERSION}" \
      "wine-stable-amd64=${APP_PACKAGE_VERSION}" "wine-stable-i386=${APP_PACKAGE_VERSION}" \
 && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
      zenity winbind p7zip-full firefox-esr fonts-manrope fonts-jetbrains-mono \
 && fc-cache -f \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/*
COPY common/wine/ahi-wine-app /usr/local/bin/ahi-wine-app
COPY apps/eufymakestudio/root /

FROM prepared
ARG APP_VERSION=5.1.3
COPY common /tmp/ahi/common
COPY apps/eufymakestudio /tmp/ahi/apps/eufymakestudio
COPY --from=fonts /fonts /tmp/ahi/common/files/dashboard/fonts
RUN python3 /tmp/ahi/apps/eufymakestudio/convert.py / && rm -rf /tmp/ahi
COPY LICENSE LICENSES apps/eufymakestudio/NOTICE /usr/share/doc/openprinthq-eufymakestudio/
ENV DASHBOARD=artisanhub-dashboard \
    TITLE="eufyMake Studio" \
    NO_GAMEPAD=true \
    PIXELFLUX_WAYLAND=true \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    BROWSER=/usr/local/bin/ahi-open-url
EXPOSE 3001
VOLUME /config
LABEL org.opencontainers.image.title="openprinthq-eufymakestudio" \
      org.opencontainers.image.source="https://github.com/norjms/openprinthq-desktops" \
      org.opencontainers.image.description="A web desktop in the OpenPrintHQ look that installs and runs eufyMake's eufyMake Studio 5.1.3 under Wine, on linuxserver.io's baseimage-selkies" \
      org.opencontainers.image.licenses="GPL-3.0-only" \
      org.opencontainers.image.version="${APP_VERSION}"
