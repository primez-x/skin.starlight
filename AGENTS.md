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

## Info and dialog contracts

- `DialogVideoInfo.xml` keeps native play 8, resume 9, and plot 4. Restart 408 sends a native click to 8.
- Native cast 50 remains bound offscreen. Provider-backed cast 250 opens the person page instead of Kodi's native actor search.
- Omit optional native toggle 5. Kodi otherwise hides cast while the plot shows.
- Source: `https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/video/dialogs/GUIDialogVideoInfo.cpp#L474-L535`.
- TV and season episode container 550 reads the skin provider. The provider queries `videodb://tvshows/titles/<showid>/<season>/` through `Files.GetDirectory`.
- The provider adds the shared duration, resume, and next-up properties. Kodi's native cast binding cannot supply that row.
- Landing focus chooses the most recently resumed regular episode, then the first unwatched regular episode, then the first regular episode.
- Season 560 changes the database season path. Specials remain selectable. Empty rows show a static horizon and message.
- `Window(home).Property(Starlight.Hub)` records the source hub. The info and person pages preserve that hub.
- Kodi 21 loads `DialogConfirm.xml` for yes/no, OK, and modal progress. Both busy modes load `DialogBusy.xml`.
- Source: `https://github.com/xbmc/xbmc/tree/21.3-Omega/xbmc/dialogs`.
- Confirmation defaults to No, native 10. Native callers can explicitly request a different default.
- Set `Window(home).Property(Starlight.Confirm.Destructive)` to `true` before a destructive confirmation. The dialog clears the flag on close.
- Standard Delete and Remove labels also select red confirmation text. Kodi provides no general destructive-action flag.
- Status order: volume, notification, background progress, busy. Each active predecessor reserves a slot below the hub bar.
- Busy and background progress retain the event horizon and sparkles when Ambient effects are disabled.
- `Starlight.Context.CardRect` on the underlying window accepts `left,top,width,height` in 1920x1080 screen coordinates.
- Supply the rectangle before each native menu. The context adapter consumes and clears the rectangle.
- The context dialog places the popover beside that rectangle. Home and person pages compute focused rectangles from the shared XML and native scroll metrics.
- Without a rectangle, the context dialog uses the centred options sheet. Later library views must supply the actual focused card rectangle.
- Home scrollbar 5500 exposes the widget scroll offset. Hidden buttons 5501 and 5502 expose native offset and cursor labels.
- `resources/lib/skin_xml.py` shares include expansion between the native context adapter and both preview renderers.
- Native metric sources: `GUIControlGroupList.cpp:62`, `GUIScrollBarControl.cpp:378`, and `GUIButtonControl.h:56` in Kodi 21.3.
- Hidden native bounds 999 keep the context dim at screen origin. Group 997 contains the movable sheet and native grouplist 996.
- Python cannot access native grouplist controls directly. The context adapter moves group 997 instead.
- Native keyboard edit 312 stays above the bottom sheet, in the page-field position. No edit field appears inside the sheet.
- Keyboard IDs 100–179 preserve all four native rows and twenty columns. Extra layout characters scroll horizontally.
- The auxiliary keyboard controls appear when edit 312 holds focus. Native callbacks retain phone, hardware, and password input.
- Search result callbacks and Up-to-results belong to step 5. The keyboard currently returns Up to native edit 312.
- `tools/render_window.py` expands the actual XML with local sample records. The renderer does not execute Kodi actions or emulate native input.
- Run `python3 tools/render_window.py --art /path/to/sample/art --output /tmp/starlight-step3` for all nine previews.

## PKC person hook

- Custom window 11103 owns every `Starlight.Person.*` property. No network metadata provider runs in the skin.
- The cast action clears old enrichment before a new person opens. The action sets `Name`, `Thumb`, `Meta`, `Blurred`, `Hub`, and `Request`.
- `Request` identifies the current person request. A future provider must compare `Request` before each asynchronous update.
- The library tab reads native movie and TV actor filters. Credits merge by year, newest first. Labels show role and year.
- The future PKC provider sets `Meta` to department, born date with age, and birthplace. `Biography` accepts plain text, clamped to three lines.
- `ProviderKey` holds the Plex person identifier. `CreditsPath` and `ImagesPath` hold provider-owned Kodi directory URLs.
- Leave unavailable values empty. Empty biography, credits, and images have visible fallback messages.
- Credit records need native video tags and poster art. `Starlight.RoleYear` supplies the role and year label.
- Image records need thumb art. Credit activation and image activation use the provider's normal Kodi directory actions.
- The provider must restrict directory URLs to trusted PKC routes. Never embed credentials in a URL or window property.
- `Tab` accepts `library`, `credits`, or `images`. The library tab is the default. Focus lands on the first library poster when available.

## Publish

- Follow `https://github.com/primez-x/kodi.addons/blob/main/VERSIONING.md`.
- Change one version component per release. Reset later components to zero.
- Add release news with the new version on the first line.
- Run the configured tests before a publish.
- Preserve the shared publish validator. Run `python3 .githooks/publish_check.py check` against a commit.
- The hook checks committed exports. A working-tree test run does not replace the hook.

## Step 5: libraries, Search and Discover

- `Includes_Library.xml` owns the 26 locked library views and the named View menu.
- Native IDs 500–508 and 510–515 retain the locked shapes. Dropped IDs 509, 549 and 550 stay absent.
- Variant IDs: 517 = 507B; 518 = 508B; 526/527 = 526A/B; 528/529 = 528A/B.
- Movies and TV use `MyVideoNav.xml`. Music uses `MyMusicNav.xml`. The spec defines no separate hub pages.
- Kodi owns native folders, sort order, selected-item actions, queues and context menus.
- Combined selectors read native genre directories. The current library path remains a native database path.
- Search keeps custom window 11100. Discover keeps custom window 11101. Rail return paths reach page controls.
- Search requires `script.starlight` 1.0.0. Every search command passes `window=11100` explicitly.
- Search controls 610–619 hold ranked source rows. Control 620 holds the cached source wall. No XML content binds those lists.
- Search text travels through the Home query property. Never interpolate query text into Kodi command strings.
- The page controller reads native keyboard edit 312 during Search. Generic keyboard callers keep their original field position.
- Up from the keyboard top row confirms text and returns focus to Top results. The native sheet remains the sole keyboard.
- Discover uses `HomeBoardWidget`. New Board parameters preserve the Home defaults.
- The skin reads PKC directories through `Files.GetDirectory`, including native `customproperties`.
- Every Discover card opens the exact provider `Starlight.InfoPath`. No title or year match creates a library identity.
- A 30-second ordered snapshot supplies Board record 1, grid records 2–5, and remaining records below.
- A temporary exclusive file lock prevents concurrent Board loads from fetching separate snapshots.
- Provider-only titles reuse `DialogVideoInfo.xml`. Control 409 binds the validated provider watchlist action.
- Provider-only shows expose cast and hide native episode rows, season tabs and library actions.
- Watchlist feedback reads matching `PKC.Watchlist.Detail.Identity`, `Pending`, `State` and `Error` properties.
- The PKC contract names that property namespace but omits the exact state fields. Confirm the fields during integration.
- `script.starlight` search selection currently reads a fresh Python list wrapper. Kodi cannot expose another wrapper's item cache.
- The parent must correct that helper command to read the native selected record. The skin retains the documented call.
- Search song records lack capsule runtime fields in the helper contract. Search shows Play without a fabricated runtime.
- Library context anchors use retained native cursor labels and the shared XML geometry. Search anchors retain the result shape.
- Render previews with `python3 tools/render_library.py --art /path/to/design/art --output /tmp/starlight-step5`.
- Preview images use sample records. Verify input, native focus, provider mutations and playback in the parent Kodi integration round.
