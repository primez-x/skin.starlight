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
- License: GPL-2.0-or-later (`LICENSE.txt`). The Manrope fonts keep the OFL; preserve `fonts/OFL.txt`.
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

## Step 4 player contracts

- `MusicVisualisation.xml` owns the fixed music stage. Back opens Music. Down opens queue window 11104.
- MusicOSD keeps native transport controls in one capsule. More opens modal window 11105 above a 35% dim.
- `MyPlaylist.xml` redirects Kodi's MusicPlaylist entry to window 11104. Up and Back return to the music stage.
- Queue rows 510 and 520 read one skin-owned snapshot through native directory bindings. Kodi dispatches the row actions.
- Queue reads use 200-record pages. Notifications refresh metadata. A one-second player-state check detects track and shuffle changes.
- Queue activation checks the selected native position against the current file before `Player.Open`. The adapter never rebuilds a playlist.
- Repeat all wraps the Up next row. Played shows preceding queue records, newest first, rather than a separate playback history.
- Queue properties belong to window 11104: `Starlight.Queue.Request`, `Ready`, `Error`, `Count`, and `NextCount`.
- `resources/player.py` owns `Window(home).Property(Starlight.Player.Blurred)` and `Starlight.Player.Monitor`.
- The passive next-track pill reads only the documented `Starlight.NextTrack.*` properties from `script.starlight`.
- The pill pads countdown seconds, measures native labels 601 and 604, and resizes group 600, background 602, and progress 603.
- The capsule stays at y=832, height 90. The pill starts at y=972. The gap is 50 pixels.
- `script.starlight` supplies next-track data and music provider actions. Search requires the helper dependency.
- Without that helper, the pill, heart, and More hide. Native transport, the music stage, and the skin-owned queue remain available.
- Spotify heart state reads `Spotify.CurrentTrackLiked`. `RunScript(script.starlight,spotify.like)` sends the contract's toggle notification.
- Spotify More commands: `spotify.playlist`, `spotify.radio`, `music.artist`, `music.album`, and `spotify.follow`.
- Non-Spotify More shows only `music.artist` and `music.album`. The helper resolves local library identities.
- Visualisation control 2 occupies `(600,22,720,720)`. The centre is `(960,382)`. Album art occupies `(800,222,320,320)`.
- The separate visualisation add-on supplies the live spectrum. Kodi's selected visualisation runs inside control 2.
- `Skin.HasSetting(Player.Visualiser.Disabled)` stores the inverse of the Visualiser preference. Empty means enabled.
- Step 6 must place include `PlayerVisualiserSetting` in the settings page. Parameters: `id`, `x`, `y`, `width`, `up`, and `down`.
- String 31231 supplies the Visualiser help text. Disabled, paused, or unavailable visualisation states show the static dotted ring.
- Ambient effects never disable the playhead glow or busy feedback. The music stage has no idle animation.
- `tools/textures_player.py` owns new player assets. The shared builder calls that module once.
- `tools/render_player.py` expands the actual player XML. The preview spectrum is sample data and never ships as a skin texture.
- Render: `python3 tools/render_player.py --art /home/user/task-scratch/starlight-design/art --output /tmp/starlight-step4`.
- Tests: `python3 -m unittest discover -s tests -p test_step4_player.py`.
- Kodi 21.3 source: `xbmc/music/windows/GUIWindowVisualisation.cpp` requires visualisation control 2.
- Native playlist source: `xbmc/music/windows/GUIWindowMusicPlaylist.cpp` loads `MyPlaylist.xml`.
- Native label width source: `xbmc/guilib/GUILabelControl.cpp:173`; Python wrapper reads width in `xbmc/interfaces/legacy/Window.cpp:332`.
- Real Kodi checks remain required: remote navigation, seek focus, playlist notifications, stale selection, shuffle, repeat, and empty/error queues.
- Also check pill width, long text, countdown pause/seek/stop cleanup, Spotify account actions, local artist/album routes, and spectrum placement.
- Verify native video OSD, seek feedback, full-screen info, process info, and buffering feedback during playback.
- Audio and subtitle OSD buttons use native `DialogSettings.xml`. Step 6 owns that shared settings dialog.
- `VideoOSDBookmarks.xml` provides native list 11 and Add bookmark 2. Kodi supplies chapters and bookmark actions.
- The queue reuses `HomePlayCapsule` for Play actions, as the global play-card rule requires.
- `DefaultAlbumCover.png` supplies Kodi’s native missing-art fallback. Menu album icons use a separate texture.

## Step 6 settings and Live TV

- `Includes_Settings.xml` owns the settings templates, Live TV rows, and native EPG layouts.
- `Settings.xml` and rail destination `Custom_1102.xml` share the three-column settings home.
- `SkinSettings.xml` exposes native hub, widget, art, Ambient effects, and visualiser preferences.
- Choice dialog 11106 writes the selected skin string, closes, and reloads the skin.
- `Player.Visualiser.Disabled` is false by default. Step 4 consumes the inverse for the visualiser.
- The screensaver action calls `Addon.Default.Set(xbmc.ui.screensaver)` to open the native selector. No screensaver dependency exists.
- Native settings use category group 3, settings group 5, and templates 7 through 15.
- Category template 10 uses a toggle button. Kodi retains the selected category after focus moves into the settings.
- `DialogSettings.xml` also serves native profile settings. Numeric input and popup sliders have separate native windows.
- `FileManager.xml` retains native lists 20 and 21. `FileBrowser.xml` retains native chooser views 450 and 451.
- `Custom_1107.xml` owns the Live TV hub. Home also shows the recent-channel row.
- Native PVR groups populate control 11. Favourites appear when the PVR backend defines that group.
- Recent channels use the native last-played directory, sorted by last play time.
- SmartTube supplies `plugin://plugin.video.smarttube/live_now`. Cards read `Starlight.Source` and show no invented schedule or progress.
- `MyPVRGuide.xml` uses native grid 50. A ruler unit of 6 shows half-hour labels.
- Kodi EPG grid clicks retain the current Kodi select action. The native context menu exposes programme options.
- Recent-channel and YouTube cards supply the shared context adapter with native cursor metrics and actual lifted bounds.
- Full pages reuse `InfoContentMotion` for the rail and top navigation layouts.
- The native Guide currently uses the existing centred context sheet. Exact programme-cell anchoring needs a native grid geometry source.
- Startup uses an asynchronous two-second alarm, short native animations, and cancellation on exit. No helper service delays startup.
- `Pointer.xml` provides the four native pointer states. `tools/textures_settings.py` generates every step 6 texture.
- Render each new window with `python3 tools/render_settings.py --art /path/to/sample/art --output /tmp/starlight-step6`.
- Previews expand shipped XML and supply native-control fixtures. YouTube preview cards are explicit synthetic fixtures without schedule fields.
- Verify remote navigation, native setting persistence, add-on settings, file selection, PVR actions, and startup on the integration box.
- Verify PVR programme art, native progress, variable-width EPG cells, pointer motion, and guide scrolling on the integration box.

## Step 5: libraries, Search and Discover

- `Includes_Library.xml` owns the 26 locked library views and the named View menu.
- Library view IDs use the Starlight block 4200–4225, grouped by family. Design names remain vocabulary only.
- Walls use 4200–4205. Rows use 4206–4211. Lists use 4212–4216. Category views use 4217–4225.
- Home, Discover, queue, settings, and Kodi-mandated controls keep their window-local IDs.
- Native view state stores the new IDs. Old saved views use Kodi's fallback. Select the preferred view again when needed.
- Kodi 21.3 accepts container IDs from the window's explicit `<views>` list. IDs must fit the low 16 bits of the view mode.
- Source: `https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/windows/GUIMediaWindow.cpp#L126-L149`.
- Stored-view fallback: `https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/view/GUIViewControl.cpp#L53-L75`.

| Family | Design name | View ID |
| --- | --- | --- |
| Wall | 510B square | 4200 |
| Wall | 511B landscape | 4201 |
| Wall | 512A poster | 4202 |
| Wall | 513B circle | 4203 |
| Wall | 514A board | 4204 |
| Wall | 515A poster details | 4205 |
| Row | 500B square | 4206 |
| Row | 501B landscape | 4207 |
| Row | 502A poster | 4208 |
| Row | 503B circle | 4209 |
| Row | 504A board | 4210 |
| Row | 505B expanding poster | 4211 |
| List | 506B video | 4212 |
| List | 507A music | 4213 |
| List | 507B music columns | 4214 |
| List | 508A expanded with poster | 4215 |
| List | 508B expanded full width | 4216 |
| Category | 520 square row | 4217 |
| Category | 521 landscape row | 4218 |
| Category | 522 poster row | 4219 |
| Category | 523 circle row | 4220 |
| Category | 524 board row | 4221 |
| Category | 526A genre list | 4222 |
| Category | 526B genre poster wall | 4223 |
| Category | 528A tabs with poster | 4224 |
| Category | 528B tabs full width | 4225 |

- Card dimensions use a 4-pixel grid: 736×312 wide, 416×232 landscape, and 216×312 poster.
- Wide ratio: 2.359:1. Landscape ratio: 1.793:1, within 0.9% of 16:9. Poster ratio: 0.692:1.
- Preserve card gaps, label offsets, capsule insets, bottom-edge zoom centres, and 48-pixel glow padding when dimensions change.
- Movies and TV use `MyVideoNav.xml`. Music uses `MyMusicNav.xml`. The spec defines no separate hub pages.
- Kodi owns native folders, sort order, selected-item actions, queues and context menus.
- Combined selectors read native genre directories. The current library path remains a native database path.
- Search keeps custom window 11100. Discover keeps custom window 11101. Rail return paths reach page controls.
- Search requires `script.starlight` 1.0.0. Every search command passes `window=11100` explicitly.
- Search controls 610–619 hold native cached source rows. Control 620 holds the source wall. Hidden control 699 receives helper output.
- Search text travels through the Home query property. Never interpolate query text into Kodi command strings.
- The page controller reads native keyboard edit 312 during Search. Generic keyboard callers keep their original field position.
- Up from the keyboard top row confirms text and returns focus to Top results. The native sheet remains the sole keyboard.
- Discover uses `HomeBoardWidget`. New Board parameters preserve the Home defaults.
- The skin reads PKC directories through `Files.GetDirectory`, including native `customproperties`.
- Every Discover card opens the exact provider `Starlight.InfoPath`. No title or year match creates a library identity.
- A 30-second ordered snapshot supplies Board record 1, grid records 2–5, and remaining records below.
- A temporary exclusive file lock prevents concurrent Board loads from fetching separate snapshots.
- Provider-only titles reuse `DialogVideoInfo.xml`. Control 418 owns the provider watchlist action.
- Provider-only shows expose cast and hide native episode rows, season tabs and library actions.
- Watchlist feedback reads matching `PKC.Watchlist.Detail.Identity`, `Pending`, `State` and `Error` properties.
- The PKC contract names that property namespace but omits the exact state fields. Confirm the fields during integration.
- `script.starlight` reads the selected native record property. The skin retains the documented selection command.
- Kodi dispatches container XML click actions only for native providers. Search and queue directories read cached data.
- Search song records lack capsule runtime fields in the helper contract. Search shows Play without a fabricated runtime.
- Library context anchors use retained native cursor labels and the shared XML geometry. Search anchors retain the result shape.
- Render previews with `python3 tools/render_library.py --art /path/to/design/art --output /tmp/starlight-step5`.
- Preview images use sample records. Verify input, native focus, provider mutations and playback in the parent Kodi integration round.
