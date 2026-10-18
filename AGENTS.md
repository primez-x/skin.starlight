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

- Run `python3 tools/build_textures.py`. Requires Pillow, system librsvg, and Cairo.
- Run `python3 tools/build_branding.py`. Requires Pillow, system librsvg, and Cairo.
- Run `python3 tools/render_home.py --art /path/to/sample/art --output /tmp/starlight-step2/home.png`.
- Add `--rail-open` for the expanded rail preview.
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
- Native image transforms: `https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/TextureCacheJob.cpp`.
- Library query fields: `https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/interfaces/json-rpc/schema/types.json`.

## Home contracts

- `HubRail` is shared by Home and the temporary Search, Discover, and Settings windows.
- `HomeWidget` chooses Board, Hero, or a row at window load. Reload the skin after a layout change.
- Board containers share one native library source. The feature uses record 1. The grid uses records 2–5.
- The skin's content extension reads Kodi JSON-RPC. No server login or external helper is required.
- Continue watching merges in-progress movies and episodes by last play time.
- The evaluated PKC `browseplex` On Deck route requests Plex server data. Native queries keep widget metadata available without that request.
- Next up selects the first unwatched regular episode from each started, unfinished series.
- Recently added sources use `VideoLibrary.GetRecentlyAddedMovies` and `VideoLibrary.GetRecentlyAddedEpisodes`.
- Widget lists contain at most 20 videos. Next up examines the 50 most recently played unfinished series.
- Playback uses a validated database ID and `Player.Open` with resume enabled.
- Background blur uses Kodi's native image cache at 16×9 pixels, then linear enlargement.
- Library art stays outside the repository. Native episode cards prefer the episode thumbnail.
- The static renderer expands the actual XML with sample records. The renderer does not emulate Kodi timing or navigation.

## Skin settings for step 6

- `Skin.String(Hub.Navigation)`: `rail` (default), `icons`, `top_left`, or `top_centre`.
- `Skin.String(Home.Continue.Layout)`: `board` (default), `hero`, `landscape`, `poster`, or `square`.
- `Skin.String(Home.Movies.Layout)`: `poster` (default), plus the same layout values.
- `Skin.String(Home.Next.Layout)`: `landscape` (default), plus the same layout values.
- `Skin.String(Home.Episodes.Layout)`: `landscape` (default), plus the same layout values.
- `Skin.String(Home.Art.Mode)`: `blurred` (default) or `bound`.
- `bound` adds sharp art at the upper right, with elliptical falloff over the blurred background.
- `Skin.HasSetting(AmbientEffects.Disabled)`: false by default. Present the inverse as “Ambient effects”.
- Disable “Ambient effects” to stop the arrival glint and the three faint background twinkles.
- Progress feedback remains visible when ambient effects are disabled.
- Empty settings select the defaults. No first-run service writes settings.

## Publish

- Follow `https://github.com/primez-x/kodi.addons/blob/main/VERSIONING.md`.
- Change one version component per release. Reset later components to zero.
- Add release news with the new version on the first line.
- Run the configured tests before a publish.
- Preserve the shared publish validator. Run `python3 .githooks/publish_check.py check` against a commit.
- The hook checks committed exports. A working-tree test run does not replace the hook.
