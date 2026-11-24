# openprinthq-crealityprint: Creality Print's Linux build on linuxserver.io's Selkies base, restyled for
# OpenPrintHQ by apps/crealityprint/convert.py and common/restyle.py. Built from the repository's root:
#
#   docker build -f apps/crealityprint/Dockerfile .
#
# The base and Creality Print's build come from apps/crealityprint/upstream.env (the release build passes them as
# build arguments): the base by tag and digest, Creality Print's AppImage by address and the hash its release
# publishes. The packages are those linuxserver.io's own Bambu Studio image installs on the same base. Creality
# Print itself is not rebuilt or changed.

# The defaults are upstream.env's values, so a plain build builds the pinned image; the tests check they agree.
ARG UPSTREAM_IMAGE=ghcr.io/linuxserver/baseimage-selkies
ARG UPSTREAM_VERSION=ubunturesolute
ARG UPSTREAM_DIGEST=sha256:c4973383c264703f5e4f96508b661065df4d32986b37b3ebb3ed25b8660eae67

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

# The base with Creality Print, Firefox and the fonts installed: what the conversion is applied to, and what the
# tests take the files it edits from (tests/run.sh builds this stage).
FROM ${UPSTREAM_IMAGE}:${UPSTREAM_VERSION}@${UPSTREAM_DIGEST} AS prepared
ARG APP_URL=https://github.com/CrealityOfficial/CrealityPrint/releases/download/v7.3.2/CrealityPrint-V7.3.2.6412-x86_64-Release.AppImage
ARG APP_SHA256=8bb5dc45a8dc5a3cbc8def89cfb8e36fcd19c839b77e9e8b622d97624b0ff05a
RUN add-apt-repository ppa:xtradeb/apps \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
      firefox fonts-dejavu fonts-dejavu-extra fonts-manrope fonts-jetbrains-mono \
      gir1.2-gst-plugins-bad-1.0 gir1.2-gstreamer-1.0 gstreamer1.0-nice gstreamer1.0-plugins-base \
      gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-pulseaudio \
      libosmesa6 libwebkit2gtk-4.1-0 libwx-perl \
 && curl -fsSL -o /tmp/crealityprint.AppImage "${APP_URL}" \
 && echo "${APP_SHA256}  /tmp/crealityprint.AppImage" | sha256sum -c - \
 && cd /tmp && chmod +x crealityprint.AppImage && ./crealityprint.AppImage --appimage-extract > /dev/null \
 && mv squashfs-root /opt/crealityprint \
 && find /opt/crealityprint -type d -exec chmod 755 {} + \
 && fc-cache -f \
 && localedef -i en_GB -f UTF-8 en_GB.UTF-8 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/*
COPY apps/crealityprint/root /

FROM prepared
ARG APP_VERSION=7.3.2
COPY common /tmp/ahi/common
COPY apps/crealityprint /tmp/ahi/apps/crealityprint
COPY --from=fonts /fonts /tmp/ahi/common/files/dashboard/fonts
RUN python3 /tmp/ahi/apps/crealityprint/convert.py / && rm -rf /tmp/ahi
COPY LICENSE LICENSES apps/crealityprint/NOTICE /usr/share/doc/openprinthq-crealityprint/
ENV DASHBOARD=artisanhub-dashboard \
    TITLE="Creality Print" \
    NO_GAMEPAD=true \
    PIXELFLUX_WAYLAND=true \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    BROWSER=/usr/local/bin/ahi-open-url
EXPOSE 3001
VOLUME /config
LABEL org.opencontainers.image.title="openprinthq-crealityprint" \
      org.opencontainers.image.source="https://github.com/norjms/openprinthq-desktops" \
      org.opencontainers.image.description="Creality Print ${APP_VERSION} in a web desktop, in the OpenPrintHQ look, on linuxserver.io's baseimage-selkies" \
      org.opencontainers.image.licenses="GPL-3.0-only AND AGPL-3.0-only" \
      org.opencontainers.image.version="${APP_VERSION}"
