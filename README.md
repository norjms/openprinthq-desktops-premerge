# openprinthq-desktops

Desktop apps for OpenPrintHQ: each one runs in a web desktop that opens in the hub, in the OpenPrintHQ look.
The installer offers them as a catalogue grouped by craft (3D printing, laser crafting, graphic art), installs
the ones you pick, and gives each person their own desktop.

This repository holds the steps that build those images. It holds no copy of any app: each image is built from
a published upstream image at a pinned digest, and only colours, fonts and the desktop around the app change.

Windows-only apps run under Wine, and their images hold Wine but no part of the app. The desktop's first start
downloads the vendor's own installer from the vendor (`WINE_APP_URL` in the app's `app.env`, checked against
`WINE_APP_SHA256` when the vendor publishes a fixed address), installs it into that desktop's storage, and starts
it (`common/wine/ahi-wine-app`). The person accepts the vendor's terms in the app's own windows. xTool Studio's
first-run windows open blank under Wine, so its desktop asks the same questions itself, showing xTool's own terms
from the installed app, and records only the person's answers, where xTool's windows would
(`apps/xtoolstudio/root/usr/local/lib/ahi/xtool_consent.py`).

| App | Craft | Built from | Folder |
| --- | --- | --- | --- |
| Bambu Studio | 3D printing | linuxserver.io `bambustudio` | `apps/bambustudio` |
| PrusaSlicer | 3D printing | Debian's `prusa-slicer` on linuxserver.io `baseimage-selkies` | `apps/prusaslicer` |
| Creality Print | 3D printing | Creality's Linux build on linuxserver.io `baseimage-selkies` | `apps/crealityprint` |
| Bambu Suite | Laser crafting | Wine on linuxserver.io `baseimage-selkies`; Bambu Lab's installer at first start | `apps/bambusuite` |
| xTool Studio | Laser crafting | Wine on linuxserver.io `baseimage-selkies`; xTool's installer at first start, and its first-run questions asked by the desktop | `apps/xtoolstudio` |
| eufyMake Studio | Graphic art | Wine on linuxserver.io `baseimage-selkies`; eufyMake's installer at first start | `apps/eufymakestudio` |

OrcaSlicer has its own repository, openprinthq-orcaslicer, built the same way.

## How it is laid out

```
common/restyle.py        the OpenPrintHQ restyle every app shares
common/wine/ahi-wine-app  installs and starts a Windows app under Wine (the Wine apps)
common/files/            what it adds: the web desktop's stylesheet, window and GTK themes, the browser
                         opener, and the start-up steps (s6) every desktop runs
apps/<app>/upstream.env  the upstream image, its version tag, the digest that tag must be, and the
                         architectures it is published for (PLATFORMS)
apps/<app>/app.env       the app's settings for the shared start-up steps
apps/<app>/convert.py    the shared restyle, then the app's own changes
apps/<app>/Dockerfile    builds the image (from the repository's root)
apps/<app>/NOTICE        the works in the image and their licences
apps/<app>/image-check.sh  checks a built image has the app's own changes
tests/                   the tests for all of it
```

## What every desktop gets

- The web desktop's page in the OpenPrintHQ colours and fonts, titled with the app's name.
- The window manager and GTK in the OpenPrintHQ theme, Manrope as the font.
- Files: the folder the web desktop's file panel serves, with the hub's library, "Send to hub", "From the
  farm", Exports and shared folders, bookmarked in every file dialog.
- Web addresses the app opens (sign-in pages, help) go to the desktop's Firefox, http and https only.
- Files the farm sends open in the app, joining its window when it is running.

## app.env

Read by the start-up steps, as shell:

| Key | Meaning |
| --- | --- |
| `APP_TITLE` | The app's name, in logs. |
| `APP_CONF` | The app's settings file, under /config. |
| `APP_CONF_NEW` | What a new settings file starts as (printf escapes), so the app starts dark. |
| `APP_SINGLE_INSTANCE` | `json` or `ini`: turn on the app's single-instance setting, so sent files join its window. |
| `APP_FILES_DEFAULTS` | `json` or `ini`: open from Files and export to Exports until the person picks elsewhere. |
| `APP_PROCESS` | What the app's running process is called, to tell whether it is open. |
| `APP_RUN` | How to start it with a file. Empty: the app cannot open a file it is given. |

An app with a setup step of its own (a Wine app installing the vendor's build into /config) adds an
executable `/etc/ahi/app-init`, which runs after these.

## Adding an app

1. Make `apps/<app>/` with the files above. `convert.py` calls `restyle.apply(root, title, app_env)` and then
   changes only what is the app's own, each edit naming text that must be found, so an upstream change stops
   the build instead of being guessed at.
2. Add `changes_<app>` to `tests/test_desktops.py` for the app's own changes.
3. `APPS=<app> tests/run.sh`, then build and `APPS=<app> IMAGE=<image> tests/run.sh`.

An app linuxserver.io publishes no image for is installed on their `baseimage-selkies` in a stage named
`prepared` (base and packages, and its `root/defaults` with the autostart that starts the app), which the tests
take their files from, then converted in the last stage (`apps/prusaslicer`).

CI runs the same for every folder under `apps/`. The OpenPrintHQ release build publishes an app as
`ghcr.io/norjms/openprinthq-<app>` with its `desktop-<app>` target.

## Tests

```
tests/run.sh                                                  every app
APPS=bambustudio tests/run.sh                                 one app
docker build -f apps/bambustudio/Dockerfile -t openprinthq-bambustudio:local .
APPS=bambustudio IMAGE=openprinthq-bambustudio:local tests/run.sh   and its built image
```

## Licence

The repository's own files are GPL-3.0 (LICENSE), the licence of the linuxserver.io images they build on. Each
image's NOTICE lists the works it contains and their licences.
