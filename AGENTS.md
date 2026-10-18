# Starlight

- `addon.xml`: Kodi 21 manifest and release news.
- `1080i/`: windows, fonts, defaults, and shared controls.
- `1080i/Includes_Constants.xml`: texture radii, borders, and layout spacing.
- `colors/`: semantic palette. `media/`: generated PNG textures.
- `fonts/`: Manrope static TTF weights and the original OFL.
- `language/`: English source strings, IDs 31000 and above.
- `tools/`: procedural texture, brand, and Home preview renderers.
- `tests/`: foundation contract checks.

## Build

- Run `python3 tools/build_textures.py`. Requires Pillow.
- Run `python3 tools/build_branding.py`. Requires Pillow, system librsvg, and Cairo.
- Run `python3 tools/render_home.py --output /tmp/starlight-step1/preview.png`.
- Run `python3 -m unittest discover -s tests`.
- Keep generated assets in Git. Kodi needs no renderer packages.
- Use the border constants in every nine-slice texture reference.
- Supply rounded artwork to `CardWithLift`. Use the generated card mask during image preparation.

## Sources

- Write original skin code from the approved design and official Kodi API references.
- Do not read or copy another skin or third-party skin helpers.
- Do not add helper dependencies for the foundation.
- Manrope source: `https://github.com/google/fonts/tree/b31870aff700ab7a1d74fa0c6887d95beb9e0037/ofl/manrope`.
- The bundled static fonts use weight values 300, 400, 600, and 700 from the official variable font.
- Preserve `fonts/OFL.txt`. The skin license remains a placeholder until the owner chooses the license.
- Kodi 21.3 GUI API: `https://github.com/xbmc/xbmc/blob/21.3-Omega/addons/xbmc.gui/addon.xml`.

## Publish

- Follow `https://github.com/primez-x/kodi.addons/blob/main/VERSIONING.md`.
- Change one version component per release. Reset later components to zero.
- Add release news with the new version on the first line.
- Run the configured tests before a publish.
- Preserve the shared publish validator. Run `python3 .githooks/publish_check.py check` against a commit.
- The hook checks committed exports. A working-tree test run does not replace the hook.
