# SMK Decision Log (for AI agents)

Append-only log of **why** non-obvious choices were made. Rationale usually
survives even when the exact implementation changes, so this should stay
accurate longer than `ARCHITECTURE.md`. Add a new dated entry whenever you
make a decision a future agent (or the user, months later) might otherwise
have to re-derive or might accidentally reverse without knowing why.

Newest entries at the top. Keep each entry to a few lines - link to the
relevant file/function instead of pasting code.

---

### 2026-08-04 - Raw-first phases; never re-encode when only raw is missing

**What**: With "Also save without filters" on, `process_bundled_export` runs
a raw copy phase first, then a merged/overlay phase (`only="raw"` /
`only="merged"` in `_process_single_item`). If merged already exists and only
raw is missing (e.g. user toggled raw on after a finished library), SMK copies
raw only and does **not** re-burn overlays. Status text says so via
`_missing_outputs_message`.

**Why**: Las v1.0.1 re-ran ~13k items (~4h of ffmpeg) after enabling raw,
because reconcile treated missing raw as "no output" and full reprocess
re-encoded overlays. Fresh raw-on runs also match the user’s mental model:
originals first, filters second. Raw-off stays a single merged pass.

### 2026-08-01 - Doc title underlines via document image resource

**What**: `headed_title` uses a 2-row table (title, then 2px
`<img src="smk_title_rule.png">`); `inject_title_rule_image` fills that
image after every `setHtml`. Width from `QFontMetrics` like Save Memories.
Level-3 titles keep ~26px top margin.

**Why**: CSS/table backgrounds are unreliable in `FlowDocBrowser`. A bare
`<div>`+`<img>` put the bar inline after the title. Two table rows match
`QLabel` + `QFrame#sectionTitleRule`.

### 2026-08-01 - Doc/section title underlines via tables and QFrame

**What**: Guide/Help/About/Palestine titles use `headed_title()` (1-column
table + 2px colored row). Save Memories box titles use
`QFrame#sectionTitleRule` sized to the label text. Theme sync rebuilds all
doc browsers with `palette(dark)["secondary"]`.

**Why**: Qt QTextBrowser ignores CSS `border-bottom` / `display:inline-block`
on headings; QLabel borders under styled frames are flaky on Windows. Earlier
CSS-only underlines never appeared for the user.

### 2026-08-01 - Trim After processing; pair duplicate wording

**What**: Removed **Open technical folder** and **Verify staging** buttons.
Renamed checkbox/button to **Keep duplicates for review** /
**Review duplicates**. Staging cleanup stays automatic after a clean finish;
technical logistics for curious users = **Add run info to finished folder**.

**Why**: Open technical was only needed when someone wants logistics beside
photos (Add run info). Manual Verify staging duplicated the end-of-run path.
Matching “duplicates” wording makes the checkbox and button read as one flow.

### 2026-08-01 - Title rules hug text; combo chevron; no red on buttons; full-height tabs

**What**: Section title underline only as wide as the title. Performance
combo gets a chevron + themed list view (fixes white popup bars). Technical
view no longer paints QPushButtons red (normal gold/orange; disabled =
flat dashed muted). File
Checker restored to full-height splitter; Help/About/Palestine fill height
again (`WidthAwareColumn(fill_height=True)`).

**Why**: Full-width gold rules were too heavy; red-on-yellow buttons looked
broken; WidthAwareColumn AlignTop crushed File Checker / doc tab height.

### 2026-08-01 - Layout pass: nested margins, section height, File Checker column

**What**: Zeroed default Qt margins on nested Account/My Data/After/Progress
rows; `_section` vertical Preferred (removed My Data/Performance stretches);
`WidthAwareColumn` top-aligns short content; File Checker uses the same
centered column + `SECTION_PADDING` as Save Memories; live dashboard title
uses real `sectionHeader` class.

**Why**: Same indent/gap class of bugs as Run; File Checker sat ~28px further
left than other tabs; Help/Guide floated vertically in tall windows.

### 2026-08-01 - Gold title rules; Run layout; My Data wording; tech label in Run

**What**: Section titles get a 2px underline via theme **secondary**
(`sectionTitleRule` / doc `h2`/`h3`): orange in light, gold in dark.
Run options use zero nested margins + Preferred height. Zip section
renamed **My Data – zip files**. Technical storage label moved into Run.

**Why**: Titles were hard to parse as box headers; Run’s nested layouts
added default Qt margins/stretch; Technical toggling was shifting the zip
section (“lag”). Cursive rejected — hurts grandma readability.

### 2026-08-01 - Add run info as Technical-view checkbox; dashboard toggle on status row

**What**: Restored run-info as **Add run info to finished folder** checkbox
(under Technical view, above Keep duplicates). When on, end-of-run calls
`copy_run_info_into_library()` → `SMK-run-info/`. Progress: **Show live run
dashboard** sits on the right of the status/mode/ETA block (no extra row).

**Why**: Checkbox matches the other Run options; packing the dashboard toggle
saves vertical space without shrinking type.

### 2026-08-01 - Product rename: Snapchat Memories Keeper (SMK)

**What**: User-facing name is **Snapchat Memories Keeper** / **SMK**
(was Snapchat Memories Downloader / SMD). Window title, splash, About,
installer, `SMK.exe`, Desktop `SMKTester.bat`, video `\xa9swr` tag, and docs updated.
`smd/branding.py` holds constants. AppData dirname, QSettings org/app, and
Python package `smd/` stay legacy so installs keep accounts/prefs.
Single-instance focus accepts both old and new window titles.

**Why**: “Keeper” matches own-your-data / offline preservation positioning;
short code SMK replaces SMD everywhere users see it.

### 2026-08-01 - File Checker light theme defaults to Terrain

**What**: `_create_themed_map(dark=False)` selects Terrain (OpenTopoMap) as
the only `show=True` base layer; dark still uses CartoDB Dark Matter.
`_apply_current_theme` calls `refresh_map_for_theme()` so toggling Light/Dark
rebuilds the open map (pan/zoom resets; skipped while a check is running).

**Why**: Light mode should read as Terrain, not OSM/Dark Matter leftover from
the previous theme. Folium LayerControl cannot switch tiles without a rebuild.

### 2026-08-01 - File Checker summary must use library-check HTML (not old ==== dump)

**What**: `_apply_scan_report` always `setHtml`s
`build_library_check_report` (date range, TOP PLACES, full PHOTO SIZES,
embedded vs JSON GPS, short rules, few/no emojis). Verbose ScanWorker
extension logs stay suppressed. Old MEDIA STATISTICS / GPS METADATA
`====` append path removed.

**Why**: Report builder existed but the tab still painted the legacy dump,
so Check folder never showed the agreed summary.

### 2026-08-01 - File Checker: quiet mid-scan status; no per-account shortcuts

**What**: During Check folder, status text updates only on step changes and
25% buckets (`_set_check_status_quiet`); no spinner animation. Progress bar
and Cancel stay live. Rejected: “Check merged/raw” buttons and remembering
the last checked folder (confusing across accounts).

**Why**: Per-file ETA/spinner rewrites felt flickery; folder shortcuts would
point at the wrong account’s tree.

### 2026-08-01 - Remove Create; Start processing creates the folder

**What**: Dropped the New-account **Create** button. Typed name + **Start
processing** creates/activates the folder. Button label shortened from
“Start full processing”.

**Why**: Create was a redundant step that also cleared the name field;
Start already created the folder.

### 2026-08-02 - Isolate macOS/Linux betas in separate repos

**What**: Official Windows stays in `LasHSHS/SMK`. Contributor starting
points are `LasHSHS/SMK-macos` and `LasHSHS/SMK-linux` (copied trees,
`0.1.0-beta`, untested). Unix packaging removed from the Windows repo.

**Why**: Platform experiments must not break Windows. Maintainer will not
claim Mac/Linux confidence for months; betas are explicitly unverified.

### 2026-08-02 - Splash until UI ready (no blank window flash)

**What**: Startup keeps the splash on top, centers the main window, shows it at
`opacity=0` so Qt can finish layout/paint, closes splash, then sets opacity to 1.

**Why**: Users already see “Loading application…”. Showing an empty white
main window (or corner→center jump) looked unprofessional. Reveal only when ready.
`SMKTester.bat` still uses `python.exe` on purpose (console owns the process).

### 2026-08-02 - macOS/Linux beta packaging only (untested)

**What**: Added `build_smk_unix.sh`, `scripts/fetch_ffmpeg.sh`, and
`.github/workflows/beta-unix.yml`. Cross-platform ffmpeg name resolution
(no `.exe` required). README marks macOS/Linux as beta / untested.
Not iOS — desktop only.

**Why**: Contributors asked for non-Windows paths; maintainer will not
claim confidence without months of real Mac/Linux soak testing. Official
product stays Windows.

### 2026-08-02 - Hide ffmpeg/ffprobe consoles on startup

**What**: `verify_tool` / About version probes use `CREATE_NO_WINDOW` via
`smd.procutil.subprocess_flags` (same as merge/metadata paths).
`verify_tool` / `bundled_status` are process-cached (`lru_cache`) so About +
startup self-check do not re-spawn the tools.

**Why**: Startup ran bare `ffmpeg`/`ffprobe -version` (console flashes). Logs
also showed many duplicate probes per launch before caching.

### 2026-08-01 - GitHub only; no Store / no paid signing

**What**: Official Windows builds ship from **GitHub Releases** only. No
Microsoft Store listing, no Authenticode purchase, no ID/selfie developer
onboarding. SmartScreen warning is documented; SHA-256 is published.

**Why**: Maintainer won’t pay for a cert or submit biometric/ID verification.
Store also conflicts with the offline/privacy positioning (Microsoft account
in the middle). Unsigned GitHub + clear “Run anyway” copy is the accepted tradeoff.

### 2026-08-01 - Layout resize: one owner, skip no-ops

**What**: Dropped per-`WidthAwareColumn` resize timer; window debounced
refresh owns width updates. Skip `setMin/MaxWidth` and doc `setTextWidth`
when values are unchanged. Tab-switch still force-syncs docs.

**Why**: Runtime logs showed window+column double-apply (~half of applies
no-ops) and ~1.3ms redundant doc syncs during drag.

### 2026-08-01 - Hard-cap context width to tab viewport

**What**: `WidthAwareColumn` sizes against the scroll viewport (visible) or
`mainTabs` width minus border+pane padding (hidden tabs). Content
`minWidth == maxWidth == min(cap, available)` so the context column never
outgrows the tab box or eats the ~12px inset
(`TAB_PANE_PADDING` 4 + `TAB_CONTENT_MARGIN_H` 8).

**Why**: Using raw `mainTabs.width()` overstated space; the context box
grew to the pane edges even after the tight-margin tweak.

### 2026-08-01 - Tight tab→content inset; no forced H-scroll

**What**: Tab pane padding 8→4px; content-column margins 28→8px
(`TAB_CONTENT_MARGIN_H`). `WidthAwareColumn` never forces min width above
available space. Resize still refreshes all tabs (debounced).

**Why**: Pane 8 + column 28 = 36px gap tab-box→context-box; with
`CONTENT_MIN_FORM` that forced horizontal scroll at half of a 2K window.

### 2026-08-01 - Resize all tabs; narrower columns; debounce layout

**What**: Window resize refreshes every `WidthAwareColumn` (not only the
active tab), debounced ~32ms. `FlowDocBrowser` height sync debounced.
Content column caps 1270→1230 and form min 720→680.

**Why**: Hidden `QStackedWidget` pages skip resizeEvents, so inactive tabs
stayed at the old width until switched. Per-pixel layout during drag felt
laggy.

### 2026-08-01 - Live run panel emojis; avoid “dashboard” label

**What**: Live run cards/title use light emoji labels. Checkbox text is
**Show live run panel** (not “dashboard”).

**Why**: Segoe UI Variable on Windows mis-kerns “oa”, so “dashboard”
showed overlapping o/a. Renaming avoids the font bug without a custom font.

### 2026-08-01 - Faster Dark/Light theme toggle

**What**: Theme apply freezes widget updates, skips mid-switch `repaint()`,
defers doc HTML rebuild to the next event-loop tick (visible window only),
rebuilds the active tab’s doc browser first, and caches About `gather_about_facts`
so ffmpeg `-version` is not re-run on every toggle.

**Why**: Toggle felt sticky because four `setHtml` passes (Guide with images)
plus About’s tool probes ran synchronously on the UI thread.

### 2026-08-01 - Disk warn = copies×ZIP + 5 GB; ETA uses real ZIP GB

**What**: Soft disk warn when free &lt; `(1 or 2)× ZIP + 5 GB` — 1× filters-only,
2× if “Also save without filters”, plus **5 GB** OS headroom. ETA extract
uses real ZIP part total (Las **~49 GB**, not a folder that also held
`extracted/`). Merge/dup still file-count based (Las Maximum **3 h 33 min**,
Mary **~7 min**).

**Why**: Snapchat cloud (~50.6 GB) matched Las ZIP parts; the “~91 GB”
folder was ZIP + a leftover unpack. Filters-only finish ≈ ZIP; keep_raw
finish ≈ 2× ZIP (Mary/Las). Pure ZIP+5 under-warned keep_raw finals;
blind 2× ZIP scared filters-only users. 5 GB OS headroom stays.

### 2026-08-01 - Soft disk-space warning (ZIP + 5 GB; mention keep_raw)

**What**: First pass used ZIP + ~5 GB for all runs (superseded above for
keep_raw scaling).

**Why**: Blind 2× ZIP was too scary before we separated ZIP-only vs
ZIP+extracted folder sizes.

### 2026-08-01 - Flat account folders (no Memories parent / nested wrapper)

**What**: Technical layout stores media in `<base>/<account>/` (not
`<account>/Memories/`). Default base is Desktop. On load, accounts under
`Desktop/Memories` or `Desktop/SMD Media` move up to Desktop.
`account_identity.json` keeps `account_name` + `mydata_ids` + layout; drops
`username`/`display_name`.

**Why**: Users expected sibling folders `Las-memories` / `Mary-memories`, not
a parent Memories bag; null username fields were useless noise.

### 2026-08-01 - Finishing overlay as failsafe; Technical contents dialog

**What**: Keep centered “Almost done…” shield from verify through finalize
until the summary dialog (progress bar still updates). Performance combo
wording stresses CPU / multitasking, not battery. Duplicate logs say
“Removing duplicate staged copies…”. Technical view gets a hint + **What’s
in technical?** dialog listing staging/json/reports/checkpoint/logs/
quarantine/debug/account_identity/README. Early+late duplicate scans stay
(early saves encode time; late catches post-merge twins).

**Technical folder keep/drop (reassess)**: Keep `json`, `reports`,
`checkpoint`, `logs`, `quarantine`, `account_identity.json`, `README`.
`staging` stays temporary (auto-delete after clean verify). `debug` rarely
used but cheap empty folder — keep for failure dumps. Do not drop
`account_identity` (layout/mydata bookkeeping; without it After-processing
resolves wrong folders).

**Layout note (not migrated yet)**: Prefer one account folder per person
(`Las-memories` / `Mary-memories`) under Desktop or a chosen base — avoid an
extra parent `Memories/` that holds multiple accounts. Nested
`account/Memories/` in technical mode is separate; unify later if desired.

**Why**: Silent end-of-run stall confused users; “use all power” read as
battery; Technical view looked like “mystery settings”; early/late dedupe is
intentional quality, not redundancy.

### 2026-07-31 - Optional “Keep duplicates for my review” (Technical view)

**What**: Technical-only checkbox; when on, `auto_delete_duplicates=False`
skips staging auto-dedupe and post-run `auto_delete_duplicate_extras`. Scans
still run; groups are left for **Check leftovers**. Off (default) = current
auto-remove behavior. Ignored when Technical view is off.

**Why**: Some users want to choose keepers themselves; burying the opt-out
under Technical view keeps the default safe/simple.

### 2026-07-31 - Map marker click uses embedded paths (not lat/lng lookup)

**What**: Each folium Marker carries `smdPaths` (JSON list). Click JS reads
`marker.options.smdPaths` and cycles if several files share a pin. Removed
nearest-neighbor lat/lng fallback that opened the wrong neighbor after
MarkerCluster spiderfy. MapRenderWorker supports Cancel; MapWorker cancel no
longer also emits `finished` (that restarted marker rendering).

**Why**: Same-GPS photo+video pins looked clickable as video but opened the
neighbor photo when the cluster moved the pin. Cancel during “Adding markers”
looked ignored for the same reason.

### 2026-07-31 - Duplicate review demoted to Technical “Check leftovers”

**What**: After-processing button renamed to **Check leftovers** and shown only
when Technical view is on (`_technical_widgets`). Pipeline still auto-removes
duplicates on Start.

**Why**: Average users already get cleanup during processing; a always-visible
“Review duplicates” button implied a required second step and scared people.
Capability kept for rare leftovers / power users.

### 2026-07-31 - Cancel mid-pipeline; skip work when library already complete

**What**: `should_stop` is polled during ZIP extract, staging dedupe, and late
duplicate scans (`PipelineCancelled` / `DuplicateScanCancelled`). When
checkpoint outputs exist and every ZIP main stem is accounted for
(done/skipped + prior staging-dedupe reports), skip extract/encode. Staging
visual dedupe uses `duplicates_staging_visual_hash_cache.json`. Session
counts distinguish this-run processed vs library size.

**Why**: After staging auto-delete, a second Start on a finished account
re-extracted ZIPs and re-ran minutes of visual staging hashing, then
processed nothing — Cancel also did nothing until the encode loop. Honest
counts fix “library kept 0” on no-op resumes.

### 2026-07-31 - File Checker summary: no phone guesses from resolution

**What**: Library check report lists every photo WxH with counts and only soft
labels (`common Snapchat export size`, `tall phone portrait`). Never names
iPhone/Samsung/etc. Dates and no-GPS-by-year come from filename stems.

**Why**: Snapchat strips Make/Model; sizes like 1008x1792 are Snapchat crops,
not native screens. Brand guesses would be wrong often and undermine the
tab's "sleep well before upload" trust. See `smd/resolution_notes.py` and
`smd/file_checker_report.py`.

### 2026-07-31 - Summary shows JSON vs ZIP vs library counts (duplicates explained)

**What**: Session summary "How many memories" lists Snapchat JSON row count,
ZIP media before dedupe, staging duplicates removed (byte + visual), and
final library size. Does **not** claim library always equals JSON count.

**Why**: Users often expect 1:1 with `memories_history.json`. In practice JSON
can list more rows than unique files in the ZIP (missing parts, or a twin
UID removed as a duplicate after the user saved the same Memory twice).
Early staging dedupe is the real cleanup; the post-encode duplicate pass is
a safety net (often finds nothing after early cleanup).

### 2026-07-31 - Checkpoint stores output filename (survive match drift on resume)

**What**: `local_checkpoint.json` now includes `output_by_stem` (stem →
filename actually written). Resume reconcile and staging verify prefer that
name; if rematch wants a new name and the old file still exists, rename it
instead of calling the stem "missing." Prune will not delete recorded names.

**Why**: Las hit "1 missing" after multi-resume / power-off runs: one staging
stem was unmatched on a later rematch (`…_a1ddf9b9.mp4` plan) while its real
output still lived under an earlier date name. Checkpoint only stored stems,
so verify looked for the wrong filename. Not caused by Review-delete order.

### 2026-07-31 - Auto-remove duplicates (keep oldest); staging dedupe before process

**What**: Byte-identical and same-content (visual) duplicates are no longer
review-only. After each scan, `auto_delete_duplicate_extras()` permanently
deletes extras from `merged/` (+ `raw/` when enabled), keeping
`keeper_filename()` (oldest `YYYY-MM-DD_HH-MM-SS…`, then shortest name).
Before match/encode, `dedupe_staging_items()` drops duplicate staging mains
(and their overlays) the same way so GPU time is not spent on copies.

**Why**: Exact SHA / decoded-content hashes mean false "different memory"
flags are negligible in practice; the real choice was always which copy to
keep. Oldest name prefers the original capture over a later Snapchat
re-export. JSON matching is per-UID/stem - removing one duplicate never
rewrites another file's GPS/date.

### 2026-07-30 - Always delete staging after clean verify (no keep-staging option)

**What**: Removed the Technical-view "Keep staging media files" checkbox and
the post-run skip path. Every successful run always runs
`StagingVerifyWorker`; if `safe_to_delete`, `CompletionFinalizeWorker`
deletes `technical/staging/` automatically.

**Why**: Staging is only the unpacked ZIP. On Las (~14k memories / ~4h),
reuse saved ~2 minutes of extract — not ~20–50%. The option mainly left
tens of GB on disk and skipped the integrity check users actually need.
Manual "Verify staging" remains for Technical view.

### 2026-07-30 - New account mode never keeps the previous folder active

**What**: Switching to New account clears `_active_account_name`. While New
is selected, a typed name (`_pending_new_account_name`) is what
`_account_name()` returns. Start auto-creates that folder before the run
(`start_download` → `_set_active_account(..., create=True)`).

**Why**: Users could type "Mary", leave Las still active (forgot Create),
and Start wrote Las's export into `Las-memories` with no `Mary-memories`
folder created.

### 2026-07-29 - Always-visible run stages; never say "done" during post-run tidy

**What**: `process_bundled_export` emits `__SMD_STAGE__|n|6|title` markers
(`SMD_STAGE_MARKER` in `smd/local_pipeline.py`). `LocalExportWorker.stage`
forwards them; Progress shows stage title + Prepare/Extract/Match/Save/
Duplicates/Finish overview **regardless of the live run dashboard toggle**.
The existing `QProgressBar` is kept and **resets to 0% each stage**, then
fills to 100% for that stage (`__SMD_PROGRESS__` + existing X/Y status
lines). Never use an indeterminate bar. Stage 6 ("Finishing last touches")
is GUI-owned: `on_download_finished` no longer says "completed successfully"
or plays the happy tone — that waits until
`CompletionMixin._on_completion_finalize_finished` after verify/summary.

**Why**: Long Mary/Las runs left the bar stuck or at 100% while extract,
duplicate scan, or post-run verify still ran; users thought SMK was frozen.
Dashboard-only phase text was invisible when the toggle was off.

### 2026-07-29 - Mixin showEvent + QMainWindow-first MRO crashed startup (0xC0000409)

**What**: Removed `WindowChromeMixin.showEvent`. Reordered `DownloaderGUI`
bases so mixins come **before** `QMainWindow`.

**Why**: With `QMainWindow` first, sip still hooked a mixin `showEvent` that
called `super().showEvent()`; that re-entered the wrapper, overflowed the
stack, and aborted at `show()`/`showNormal()` with `0xC0000409` ("Unhandled
Python exception"). Taskbar identity stays on AppUserModelID + Qt window
flags; do not add Win32 `GetWindowLong*` style hacks in `showEvent` without
re-testing show on 64-bit Windows.

### 2026-07-29 - Console launch must tee stdout, not replace it

**What**: `StreamRedirector` accepts `also=` (original console stream).
`DownloaderGUI` tees into the debug panel instead of assigning a redirector
that fully replaces console stdout/stderr.

**Why**: After `Run-SMK.bat` switched to foreground `python.exe`, assigning
`sys.stdout = StreamRedirector(...)` aborted with Windows `0xC0000409`
during main-window init ("Unhandled Python exception"). Teeing keeps the
bat console alive and the GUI log fed.

### 2026-07-29 - Run-SMK.bat owns the GUI process (close console = close SMK)

**What**: `Run-SMK.bat` runs `.venv\Scripts\python.exe desktop_gui_pyqt.py`
in the foreground (no `start` + `pythonw`). Closing the bat console closes
that SMK only. Main window `closeEvent` cancels workers and `app.quit()`;
`setQuitOnLastWindowClosed(True)`.

**Why**: Detached `pythonw` left orphan Task Manager entries after users
closed the launcher window, so they had to End Task by hand. Foreground
`python.exe` ties lifetime to that console without `taskkill` of unrelated
Python processes (e.g. Cursor).

### 2026-07-29 - Overlay video encode nudged sharper (still far from lossless bloat)

**What**: `gpu_encode.py` quality knobs moved: x264 CRF 16→14, AMD AMF
QP 22→18, NVENC/QSV 18→16.

**Why**: User wants caption videos closer to `raw/` look without returning to
CRF 0 / QP 0, which made `merged/` absurdly larger than Snapchat originals
(whole-frame lossless re-encode after burn-in). There is no way to keep the
original video bitstream and only compress the overlay in one file; this is
the available lever. Modest step only - expect somewhat larger overlay
`merged/` videos and a bit more encode time, not the old multi‑× blow-up.

### 2026-07-29 - Second launch focuses existing window; never kill a live run

**What**: If `SingleInstance` finds a live owner, the second process writes the
show-signal, focuses any "Snapchat Memories Keeper*" HWND, and **exits**.
`force_takeover()` only runs when the lock owner is gone. Taskbar: force
`WS_EX_APPWINDOW` / clear `WS_EX_TOOLWINDOW` on show + flash on re-focus;
set `QApplication` window icon.

**Why**: Old path waited 1.5s then killed the prior instance if the signal
file lingered - during a long processing run the UI can be busy, so that
could destroy a multi-hour job. User also lost the taskbar button on a
second monitor and thought SMK had been closed. Discord/Spotify behavior:
one instance; second launch only brings it forward.

### 2026-07-29 - Loop still overlay PNGs when burning into video (fix 1-frame "photo videos")

**What**: `merge_video_overlay()` passes `-loop 1` on the overlay PNG input
before `scale2ref` + `overlay=...:shortest=1`.

**Why**: With scale2ref we added `shortest=1` so output length follows the
video. A non-looped PNG is one frame, so shortest ended the encode after
frame 1 - metadata duration stayed ~full length but `nb_frames=1` (frozen
still, tiny file). Confirmed on Las merged vs raw for 2025-01-03 /
2025-02-08 / 2024-10-20 overlay clips. Photos were fine (Pillow composite,
JPEG q=100); this bug was video-overlay only.

### 2026-07-29 - Video overlays scale2ref to the main frame (fix zoomed captions)

**What**: `merge_video_overlay()` uses
`[1:v][0:v]scale2ref[ov][base];[base][ov]overlay=...` instead of bare
`overlay=0:0`. Image merge applies `ImageOps.exif_transpose` before
compositing; still resizes full-frame overlays to main size.

**Why**: On a real Las extract, 0/2262 video+overlay pairs shared pixel
size (overlays commonly ~1.5× or taller than the video). Without scaling,
ffmpeg kept overlay-native pixels and clipped them → magnified text
banners. Scale overlay *to* the video (not the reverse).

### 2026-07-29 - Export diagnosis shows ZIP size / year span / empty-URL note; Start warns on low disk

**What**: `ExportAnalysis` gains `year_min`/`year_max`/`zip_bytes`; Save
memories summary surfaces them. `start_download()` warns when free space
on the output drive is under ~2× ZIP size (Cancel / Continue anyway).

**Why**: Users need to know immediately whether the export is usable
offline and how big the run will be before a multi-hour extract.

### 2026-07-26 - Same-day photo JSON matching uses ZIP entry mtimes

**What**: `extract_media_from_zips()` now restores each file's mtime from
the ZIP entry (`_restore_zip_entry_mtime`). `build_deterministic_match_map()`
sorts same-day **photos** by that mtime when the bucket's mtimes are not
all identical (≥2s spread); otherwise falls back to UID-stem order.
Videos still use embedded `creation_time` (2026-07-14 entry).

**Why**: Empty Download Link exports have no media-id match. UID-stem
order silently swapped photo time/GPS on multi-photo days (confirmed vs
Snap + All-In-One on Las samples 1/5/7/8, especially 2024-07-07). Snapchat
strips photo EXIF but leaves capture-related clock digits in ZIP entry
times; preserving and sorting by them pairs rows correctly. Stomped
extracts (all mtimes equal) keep the old UID fallback so we don't invent
order. Focused check: `scripts/test_photo_mtime_samples_1578.py`.

### 2026-07-19 - Account section becomes an inline New/Old account toggle; folders always suffixed `-memories`; layout persisted per account

**What**: Replaced the per-export `AccountRunChoiceDialog` modal (previous
entry below) and the separate "After processing" account combo with a single
always-visible **Account** section at the top of the Save memories tab
(`gui/tabs/save_memories_tab.py`): a `New account`/`Old account` radio toggle,
a name field + Create button for the former, Confirm/Change output folder
buttons for the latter, and one `active_account_label` banner showing the
resolved folder. `_active_account_name` (via `_set_active_account()`) is now
the *only* "which account" state in the tab - `_account_name()` and
`_after_processing_account_name()` are both aliases onto it, so a run and
every "After processing" button always agree. Every account name gets
`ensure_memories_suffix()` applied (`Las` → `Las-memories`), and the user
media root is renamed `downloads/` → `Memories/` (`MEMORIES_DIRNAME`,
`migrate_account_layout()`). "Choose ZIP files" and "Choose folder" are now
one function, `select_export_folder()` (folder-picker only - the empty-state
hint tells the user to put all ZIP parts in one folder first). The
"selected account folder:" combo is gone entirely; the Account section's
banner is the only place a resolved save path is shown.

New `AccountPaths.for_account()`/`for_user()` `keep_raw` kwarg controls
flat-vs-nested layout: `Memories/` directly (or `Desktop/<account>/`
directly) when there are no raw copies (the common case - avoids a
pointless single-child `merged/` folder), `Memories/merged/`+`Memories/raw/`
only when raw copies genuinely exist. Because an account's actual layout
must never depend on today's live Technical view toggle (see the persisted-
layout entry directly below), `_account_paths()` resolves `keep_raw` from
disk for existing accounts, not from the live checkbox.

The standalone "Deep scan for re-exported duplicates" button was removed -
redundant now that the deep scan already runs automatically in every run
(see the duplicate-detection entries below). "Review duplicates" absorbed
its job: checks the byte-scan cache, then also always checks for a cached
visual-scan report, surfacing whichever kind(s) found groups.
`review_duplicates_btn` is enabled only once the active account has files in
`merged/` - not just "an account is selected." All After-processing buttons
now grey out via new `#accentBtn:disabled`/`#toolbarBtn:disabled`/
`#runAction:disabled`/`QLineEdit:disabled`/`QLabel:disabled` QSS rules
(`smd/theme.py`) - previously they looked identical whether enabled or not,
because their own non-`:disabled` object-name rules beat the generic
`QPushButton:disabled` rule by specificity.

**Why**: User asked for the New/Old-account choice to be a toggle (not a
per-export modal), for the two folder pickers to be one function, for
After-processing buttons to visibly grey out instead of silently doing
nothing, and for the redundant Deep-scan button to go away since it now
happens automatically. Also asked for two clearly separate mental models -
"default: name-memories > merged(-or-merged/raw) > media files" vs
"technical view: name-memories > technical > merged(-or-merged/raw) > media
files" - hence the flat-vs-nested `keep_raw` layout and the `Memories/`
rename (so the *user-facing* wording never says "downloads", which was
never accurate - nothing is downloaded, SMK processes an export already on
disk).

### 2026-07-19 - Per-account layout (simple/technical, base dir, keep_raw) persisted instead of re-derived from live UI state; legacy folders self-heal on any lookup, not just on create

**What**: `save_account_layout_info()`/`load_account_layout_info()`/
`resolve_existing_account_layout()` (`smd/account_layout.py`) persist which
physical layout an account actually uses, into the same
`technical/account_identity.json` the mydata-ID bookkeeping already used.
`_account_paths()` (`gui/tabs/save_memories_tab.py`) now trusts this for any
account that has it, and only falls back to today's live Technical
view/"Also save without filters" state for a genuinely brand-new account.

Two real bugs found and fixed while wiring this up (both regression-tested
in `tests/test_account_layout.py`):
1. `_account_paths(name, create=False)` (used by "Confirm output folder" for
   an old account, and every After-processing button) used to skip
   migration entirely, calling `AccountPaths.for_account()` directly instead
   of `resolve_account_paths(..., migrate=True)`. A legacy account still
   using the old `downloads/` name (real accounts on this machine, `Las`/
   `Mary`, are in exactly this state) would resolve to an empty, not-yet-
   renamed `Memories/` and every button would look broken until the user
   ran a full new process. Fixed by routing the `create=False` path through
   `resolve_account_paths()` too (migration is pure renames, safe on a read
   path) and adding the equivalent `elif paths.account_dir.exists():
   migrate_account_layout(paths)` for simple-mode accounts.
2. `migrate_account_layout()`'s directory-merge step only merged one level
   deep. `ensure_dirs()`/`ensure_user_dirs()` can pre-create empty
   `Memories/merged/`+`Memories/raw/` stub folders *before* migration runs
   (the `create=True` path); the old shallow merge saw "`Memories/merged`
   already exists" and skipped moving legacy `downloads/merged/` into it at
   all, silently orphaning every file nested inside. Fixed with
   `_deep_merge_dir()`, a recursive version that merges into an
   already-existing target instead of skipping it. Caught by
   `test_migrate_account_layout_keeps_nesting_when_keep_raw_true` failing
   during test-writing, not by manual testing.

Also added `collapse_merged_to_flat()`: accounts created before `keep_raw`
existed always nested `merged/`(+`raw/`) even with zero raw copies: this
flattens that specific legacy shape (no `raw/` content present) to match the
new flat default, and deliberately leaves genuine `keep_raw=True` accounts
(real `raw/` content) nested.

**Why**: The user reported "the buttons in the After processing box don't
work unless technical view is selected" - root cause was `_account_paths()`
recomputing the physical location from *today's* toggle state instead of
where the account actually lives on disk. Fixing that exposed the two
migration bugs above, both of which are real risks for this user's own
`Las`/`Mary` accounts (still on disk in the pre-rename `downloads/` shape,
`Las` with genuine `raw/` content) the first time those accounts get
confirmed/re-processed under the new code.

### 2026-07-19 - `_list_known_accounts()` must exclude the technical base dir itself from the Desktop scan

**What**: `_list_known_accounts()` (`gui/tabs/save_memories_tab.py`) unions
two disk scans for "Old account" candidates: the technical base dir's direct
children, and `Desktop/`'s direct children (for simple-mode accounts,
heuristically: has stored layout info, or is just non-empty). When the
technical base dir itself lives directly on the Desktop - true for this
user's real setup (`Desktop\Memories`, containing real `Las`/`Mary`
account folders) and for the default `Desktop/SMD Media` - the second scan
found the base dir folder itself (non-empty, since it holds real accounts)
and offered it as if it were a simple-mode account of its own. Fixed by
skipping any Desktop child whose resolved path equals the resolved base
dir.

**Why**: Found via manual smoke-testing the New/Old account toggle end to
end against this user's real base dir - the "Old account" candidate showed
"Memories" (the container) instead of "Las"/"Mary" (the real accounts). Left
uncaught by unit tests since it needs a `QApplication` + real/patched
`AccountPaths` classmethods together; this codebase has no GUI test harness
yet (see `ARCHITECTURE.md`'s `QSettings` gotcha for why constructing
`DownloaderGUI()` for this kind of test needs care).

### 2026-07-19 - Replaced automatic ZIP-identity account naming with an explicit New run / Continue run prompt

**What**: Reverted the GUI's use of the export's own account info for naming.
`AccountRunChoiceDialog` (`gui/dialogs.py`), shown by
`_prompt_account_for_export()` (`save_memories_tab.py`) right after ZIP
selection, now always asks the user directly: **"New run"** (type/edit a name,
pre-filled only from folder/parent-folder naming - never from account.json) or
**"Continue an existing run (may not be finished)"** (pick from
`_list_known_accounts()`). This replaces the old `_apply_account_from_export()`
which silently called `extract_account_identity_from_zip()` and even
auto-renamed existing folders on disk. `extract_account_identity_from_zip()`,
`AccountIdentity`, `format_account_folder_name()`,
`derive_account_name_from_export()` (`smd/export_detect.py`) and
`rename_simple_mode_account()`/`rename_technical_mode_account()`
(`smd/account_layout.py`) are kept (still tested, still correct utilities) but
are no longer called from the GUI. `save_account_identity()` is still called,
but now only ever with `mydata_ids` (never `username`/`display_name`) - purely
to let the dialog default to "Continue" + the right folder when the exact
same export is re-selected later, which needs no personal data at all.

**Why**: The prior approach (2026-07-19, "Read the real Snapchat username...")
required the export to include `account.json`/`account_history.json`, which
in practice is often missing (memories-only exports, like the user's own Las
export) and implicitly nudged toward "request Account Information too" -
personal data (username, display name, email/phone are all in that same file)
that the naming feature didn't need to touch. The user explicitly asked to
stop relying on it and instead just ask directly: is this a new account, or a
continuation of one you already started? This is simpler, needs zero personal
data, and is unambiguous - no guessing, no silent folder renames.

### 2026-07-19 - "Unknown account N" fallback, made rename-safe via a stored mydata ID

**What**: When an export has no readable username/display name (no
`account.json`/`account_history.json` in the ZIP at all - the common case for
older/memories-only Snapchat exports) and no usable folder name either,
`derive_account_name_from_export()` now assigns `Unknown account N` via
`next_unknown_account_name()` (lowest free `N`, scanning existing folders)
instead of the old opaque `Memories {mydata-id}` fallback.

The tricky part the user asked about directly: **what happens if the user
renames that folder?** Fixed by persisting the export's `mydata~ID` (not just
username/display name) into `technical/account_identity.json` unconditionally
- `save_account_identity()` is now called even when there's no identity at all,
both from `_apply_account_from_export()` (ZIP-selection preview) and
`start_download()` (run start, `save_memories_tab.py`). `AccountIdentity` grew
a `mydata_ids: frozenset[str]` field, and `AccountIdentity.matches()` treats a
shared ID as an automatic match regardless of name fields.
`find_existing_account_folder_name()` checks this first, before username/
display-name/legacy-folder-name matching. Net effect: rename `Unknown account
1` to anything, even something with zero identifying text (e.g. `Random
Friend`) - re-selecting the *same* export later resolves back to `Random
Friend`, not a new `Unknown account 2`. Covered by
`test_unknown_account_folder_survives_rename_to_unrelated_name` in
`tests/test_derive_account_name.py`.

**Why**: User asked for a clear placeholder name instead of `Memories {id}`,
then immediately asked "but what if the user renames the folder?" - a real
edge case, since a plain folder-name-based fallback would otherwise silently
create duplicate folders for the same account after any rename.

### 2026-07-19 - Account folder names use display name + username from the export

**What**: `AccountIdentity` + `format_account_folder_name()` in
`smd/export_detect.py` now read both `display_name` and `username` from the
export's account info file and format folder names like `Las (las_snap)` when
both differ - so multiple accounts are easy to tell apart. When the user
re-selects an export for an account that already exists under a vaguer old
name (e.g. `Las`), `_apply_account_from_export()` in `save_memories_tab.py`
renames both the Desktop library folder and the matching internal
`%LOCALAPPDATA%` account root via `rename_simple_mode_account()` /
`rename_technical_mode_account()` (`smd/account_layout.py`). Identity is
persisted to `technical/account_identity.json` for later folder matching.
Simple-mode "After processing" account list now also scans `Desktop/<account>/`
(not just the technical base dir).

**Why**: User asked to rename account names to whatever identifying
information the export actually contains, instead of relying on manual folder
names like `Las` / `Mary` or opaque `Memories {id}` fallbacks.

### 2026-07-19 - Read the real Snapchat username out of the export ZIP for account naming

**What**: `extract_account_username_from_zip()` (`smd/export_detect.py`) opens
each selected ZIP part, finds `json/account.json` or `account_history.json`
(filename varies by export format version), and recursively searches the
parsed JSON for any key named `username` (case-insensitive, any nesting -
Snapchat's own export key casing has varied). `derive_account_name_from_export()`
now tries this **first**, before the folder-name heuristics added in the
"removed Where to save" change below - it overrides even an explicitly
selected/named folder, since the real username is authoritative and a folder
name is just a guess at it. Falls back to the existing heuristics silently if
no account file is present (e.g. user deselected "Account Information" when
requesting the export) or it has no readable username. `save_memories_tab.py`
(`_apply_account_from_export`) also tracks whether the name came from this
authoritative source (`_account_name_from_zip`) purely to add "(from your
Snapchat account)" to the export summary banner - not used for any logic.

**Why**: User asked to check whether the account name is visible inside the
ZIP itself rather than only inferred from how they happened to organize
folders/files on disk. It is (confirmed against public docs on Snapchat's
"Download My Data" format); using it directly is more reliable than folder
naming and works even when the user selects loose ZIP files sitting in a
generic folder (e.g. `Downloads/`), which previously fell through to the
unfriendly `Memories {mydata-id}` fallback.

### 2026-07-19 - Sped up the visual duplicate scan with a per-file cache (not a pre-filter)

**What**: `scan_visual_duplicates()` (`smd/duplicates.py`) now persists a
`duplicates_visual_hash_cache.json` (filename -> size/mtime_ns/hash). A file
is only decoded if its size or mtime changed since the cached entry - on a
repeat scan of an unchanged library, every file is skipped and no ffmpeg/PIL
work happens at all.

**Why**: after making the scan automatic on every run (entry below), the
user asked to make the ~20-minute first-run cost faster. The first attempt
was a "cheap fingerprint" pre-filter: read each video's duration+resolution
via ffprobe (no decode, in isolation ~3x faster than a full decode) and only
fully decode videos that share a fingerprint with another video - the video
equivalent of the byte scan's same-size bucketing. **This made things worse
in practice**, not better: spawning ~8,400 ffprobe processes across 12
threads in parallel overloaded the machine badly enough that even unrelated
PowerShell commands (`Get-Process`) stalled for tens of seconds, and when the
runaway scan was force-killed, its child `ffmpeg.exe`/`ffprobe.exe`
processes were orphaned (Windows doesn't cascade-kill children of a
force-killed parent) and kept running/contending for resources afterward.
Per-file subprocess-spawn overhead (~150-400ms, likely AV real-time scanning
of each new process) dominated the "cheap" check's cost almost as much as
the real decode, so the pre-filter pass was nearly pure added cost with an
unproven benefit (duplicate detection on Snapchat clips is also undermined by
many unrelated videos sharing the same near-max recording-length duration,
weakening the fingerprint's ability to discriminate). It was fully reverted.

**Trade-off**: the very first scan of an existing large library still takes
the full decode time (no way around it - only playback can tell two videos
apart). Only repeat scans benefit. This is the expected common case though:
most processing runs on an account are re-runs/incremental additions, not a
brand new multi-thousand-file library every time.

**Lesson for future agents**: be very wary of "add a cheap pass to filter
candidates before the expensive pass" optimizations when the cheap pass
still means spawning one OS process per file - on Windows in particular,
process-creation overhead (and AV scanning of each new process) can dominate
over the actual work being skipped, especially at thread-pool concurrency
across thousands of files. Measure the *pre-filter's own cost at full scale*
before trusting it, not just per-file in isolation with a small sample.

---

### 2026-07-19 - Made the visual duplicate scan run automatically in every processing run

**What**: Moved `scan_visual_duplicates()` from GUI-triggered-only into
`process_bundled_export()` itself (`smd/local_pipeline.py`, right after the
existing `scan_content_duplicates()` call), so it now runs unconditionally
on every full processing run, same as the byte scan. `SessionReport` gained
`visual_duplicate_groups` (`smd/session_report.py`), and
`_after_processing_summary()` (`gui/tabs/completion.py`) now auto-opens
`DuplicateReviewDialog` for it too, right after the byte-scan dialog (if
any) closes.

**Why**: Immediately after shipping the opt-in version (previous entry
below), the user asked for it to be automatic/built into the main run
instead of a separate button they'd have to remember to click - the whole
point is catching duplicates they don't know to look for.

**Trade-off (accepted deliberately)**: every full processing run now also
pays the visual scan's full-decode cost - no same-size shortcut is possible,
so this added ~20 minutes to processing on the user's 13.9k-file library.
The "Deep scan for re-exported duplicates" button/worker were kept (not
removed) for on-demand re-checks when the cache is missing or stale, but in
the normal case they just hit the cache the pipeline already wrote.

---

### 2026-07-19 - Added a "visual" (decoded-content) duplicate scan alongside the byte scan

**What**: `smd/duplicates.py` gained `scan_visual_duplicates()` /
`load_cached_visual_duplicate_report()` (report `kind="visual"`, cached to
`reports/duplicates_visual_report.json`), a `VisualDuplicateScanWorker`, and
a "Deep scan for re-exported duplicates" button next to "Review duplicates"
in Save memories → After processing. It reuses `DuplicateReviewDialog`
(which now branches its wording/cache file on `report.kind`) instead of a
new UI.

**Why**: A user had pairs of videos with different filenames/timestamps that
looked identical when played. Investigation (hashing the *original* files in
`technical/staging/`, before SMK ever touched them) proved Snapchat's own
export had logged the same recording twice under separate UUIDs/timestamps -
different container bytes (so whole-file SHA-256, and thus the existing
byte-identical scan, never matches them), but byte-identical *decoded* video
frames. A full-library scan on that user's ~13.9k-file export found 269 such
groups (~1 GB of true extra copies) that "Review duplicates" had correctly
never flagged. Root cause is Snapchat's export data, not an SMK bug - so this
adds a way to *find* them without changing what the byte scan considers a
duplicate.

**Trade-off**: Decoding every file (no same-size shortcut, since re-exported
copies can differ in size) took ~20 minutes for 13.9k files - too slow to run
automatically. Kept strictly opt-in with an explicit file-count confirmation
dialog before starting, unlike the byte scan which can run unattended after a
run.

---

### 2026-07-19 - Auto-derived account name from export selection; removed "Where to save"

**What**: Dropped the manual "Where to save" / project name field on Save
memories. When the user picks export ZIPs, `derive_account_name_from_export()`
(`smd/export_detect.py`) sets `_derived_account_name`: folder name if they
selected a folder (e.g. `Las/`), else parent folder of the ZIPs if not generic
(`Downloads` skipped), else existing output folder matching the mydata ID,
else `Memories {id}`. The yellow export summary banner shows account + save
path.

**Why**: ZIP filenames are opaque (`mydata~1783…`); users already organize
exports in named folders — use that instead of a redundant text field.

### 2026-07-19 - Palestine tab with resource links and policy-focused framing

**What**: New **Palestine** main tab (`PalestineTabMixin`, `smd/palestine_content.py`)
between File Checker and Help. Lists external human-rights/education/donation
sites (B'Tselem, Al-Haq, UN OCHA, Amnesty, HRW, Decolonize Palestine, IMEU,
Electronic Intifada, MATW) with short blurbs; includes user-requested solidarity
phrases focused on occupation, accountability, and documented violations.
Header `Free Palestine` tooltip now points users to this tab plus the existing
MATW donation link.

**Why**: User wanted in-app education/help beyond the header link, using
action/policy framing (not people-as-enemies language). Expanded 2026-07-19
with oppression aspects, journalist killings (CPJ/RSF), whistleblower sources
(Breaking the Silence, +972), and BDS/boycott resources. Deliberately omitted
dehumanizing or unverified conspiracy claims.

### 2026-07-19 - Flattened the "accounts" folder for Technical view custom base dirs

**What**: `_account_paths()` (`gui/tabs/save_memories_tab.py`) used to put
account folders at `<base_dir>/accounts/<name>/` whenever Technical view had
a custom base dir set. Now it's `<base_dir>/<name>/` directly - no `accounts`
wrapper - matching simple mode's `Desktop/<account>/` pattern. Also updated
the two other places that assumed the `accounts/` subfolder:
`_suggest_account_from_export()`'s existing-folder search and
`restore_account_name_field()`'s single-account auto-fill.

**Why**: User found the extra nesting level pointless when the base dir is
already dedicated to SMK's own output (which it normally is, once picked).
Simple mode never had this wrapper to begin with, so this just makes
Technical view consistent with it.

**Migration**: `migrate_flat_accounts_root()` (`smd/account_layout.py`) moves
any existing `<base_dir>/accounts/<name>/` folders up one level (skips if a
same-named flat folder already exists - never overwrites), then removes the
now-empty `accounts/` dir. Runs automatically inside `_account_paths()`
whenever `create=True`. Not related to the separate, always-hidden
`%LOCALAPPDATA%/SnapchatMemoriesDownloader/accounts/<account>/` internal
data root, which still nests under `accounts/` and was left alone.

### 2026-07-19 - "Free Palestine" header label is now a clickable flag link

**What**: `self.free_palestine_label` (bold, left of the Support button in
`#appHeader`) is rich-text HTML: a flag image + "Free Palestine" wrapped in
an `<a href>` to `https://matwproject.org/crisis-and-emergencies/palestine`.
`setOpenExternalLinks(True)` opens it in the system browser (same
`QDesktopServices` mechanism used elsewhere, just via Qt's built-in rich-text
handling instead of a manual `clicked` connection). The flag started as a
Unicode emoji (`\U0001F1F5\U0001F1F8`) but that glyph didn't render (showed
as a blank/tofu box) on the user's system font, so it was swapped for a
real bitmap: `assets/flags/palestine.png` (300x150, generated with
Pillow - exact 2:1 ratio, official black/white/green bands + red hoist
triangle to the horizontal midpoint), embedded via `<img src=... width=20
height=10>` inside the same anchor. `smd.spec` bundles `assets/flags/*`
the same way it already does `assets/ui/*`.

### 2026-07-19 - Moved "Free Palestine" from top banner to header label

**What**: Removed the centered `#infoBanner` row above `#appHeader`.
`DownloaderGUI.init_ui` now places a bold `QLabel` ("Free Palestine",
`self.free_palestine_label`) directly left of the Support button inside
`#appHeader` instead.

**Why**: User-requested repositioning - same text, less prominent chrome
(inline in the header vs. a full-width banner row).

### 2026-07-17 - Split `desktop_gui_pyqt.py` into `gui/` package via mixins

**What**: Relocated the ~6,500-line god file into `gui/` (`common`,
`widgets`, `workers`, `dialogs`, `single_instance`, `window_chrome`, and
`tabs/*` mixins). `desktop_gui_pyqt.py` is now a thin entry
(`DownloaderGUI.__init__` + slim `init_ui` shell + `main()`). Entry path
for PyInstaller/`Run-SMK.bat` unchanged.

**Why mixins (not composition)**: every tab/handler already used `self.foo`
across concerns; mixins preserve that shared state without a months-long
redesign of attribute ownership. Pure move-and-rewire - no intentional
behavior change. Ordered Phase 1 (self-contained workers/widgets/dialogs)
before Phase 2 (DownloaderGUI mixins, lowest-risk Help/Guide first, then
chrome, File Checker, Save memories/completion) so each step stayed
bisectable. Done *after* `test_full_pipeline_integration.py` so the
backend risk surface had a regression net before the GUI refactor.

**Import rule**: tabs/chrome import from common/widgets/workers/dialogs
only - never peer tabs, never back into the entry script - to avoid
circular imports.

### 2026-07-17 - App icon reverted to original yellow logo; full-pipeline integration test added before the planned god-file split

**What (icon)**: The DALL-E-generated icon added earlier the same day was
reverted. The user wanted the original yellow download-arrow icon back
(`icon.ico`/`icon.png`/`assets/icon.*`), which was still recoverable
byte-for-byte from the `Baseline: SMK v1.0.0` commit. Restored via
`git checkout 9d3e36f -- icon.ico assets/icon.ico assets/icon.png`, then
copied to the loose root-level `icon.png` (never tracked, only used at
runtime/build time) and rebuilt so both the taskbar and window titlebar
pick it up. Lesson: don't redesign user-visible brand assets speculatively
even when asked to "check if it's applied" - the ask was about the icon
*pipeline* (missing files/AppUserModelID), not the artwork itself.

**What (tests)**: Added `tests/test_full_pipeline_integration.py`, which
drives `local_pipeline.process_bundled_export()` end to end (synthetic ZIP
with real JPEGs + a real ffmpeg-generated MP4) instead of unit-testing
helpers in isolation. Covers: extract -> JSON match -> merge/hardlink ->
checkpoint -> simulated-crash resume (delete a merged/ output, rerun,
confirm exactly the one broken item is repaired via
`reconcile_checkpoint_with_disk`, not a full redo) -> `check_staging_readiness`.

**Why**: User flagged (and I agreed) that the existing 47 unit tests run in
under a second, which for an app whose core job is "don't lose someone's
memories" is a signal they're each testing small helpers, not the actual
risk surface. This integration test is the net that would catch a real
data-loss bug. It was deliberately built *before* the `desktop_gui_pyqt.py`
god-file split (also requested) so that large refactor has a regression
safety net on the pipeline it doesn't even touch directly - the split is
GUI-only, but confidence that "the pipeline still behaves" needed to exist
independent of GUI changes. Uses `pytest.mark.skipif(not ffmpeg_available())`
so CI/dev environments without ffmpeg degrade gracefully instead of failing.

### 2026-07-17 - File Checker made read-only; no camera make/model stat; App icon added

**What**: `run_full_analysis()` (`desktop_gui_pyqt.py`) now always runs
`ScanWorker` with `dry_run=True` - File Checker reports mismatched
extensions but never renames anything, on any folder. Extension fixing
stays exactly where it already was: automatic, inside `_fix_extension()`
(`smd/local_pipeline.py`), as part of every "Save memories" run.

**Why**: user wanted a clean mental model - "File checker should only check
files... the fixing stuff should be in save memories." Investigation showed
the fixing already only ever happened in the Save Memories pipeline for
SMK's own output; File Checker's rename-on-scan behavior was leftover
functionality for arbitrary external folders that blurred that line and
wasn't asked for.

**What (metadata stats)**: Tested real Make/Model EXIF and video container
tags on live Las-account output. Confirmed Snapchat strips all camera/device
identifying metadata from both photos and videos before export (only
`DateTime`/`GPSInfo`/`Orientation` survive on photos - and SMK wrote those -
plus generic `Core Media Video/Audio` handler names on videos). Added a
photo resolution breakdown to File Checker's media stats instead ("N unique
resolutions, most common WxH") as an honest proxy stat, and explicitly did
not add a fake "shot on which phone" feature since there is no real data
behind it.

**What (app icon)**: Added `icon.ico`/`icon.png` at repo root and under
`assets/` - they did not exist anywhere in the repo before, despite four
separate code paths (`apply_window_icon()`, the `DownloaderGUI.__init__`
icon set, the header logo, the splash screen logo) all being wired up to
load one if present. This is also why the *compiled* `SMK.exe` had no icon
either, not just source/bat runs - `smd.spec`'s `icon_arg` silently
resolved to `None`. Also added `SetCurrentProcessExplicitAppUserModelID`
so Windows gives SMK its own taskbar identity instead of grouping it under
pythonw.exe's generic icon when run from source.

**Why not implement**: cloud upload, a media gallery grid, and macOS/Linux
builds were re-confirmed out of scope per prior decisions (see below) after
a competitor sweep (`canvases/smd-competitive-landscape.canvas.tsx`) turned
up nothing that changed that calculus.

---

### 2026-07-16 - Keep system/display awake for the duration of a run

**What**: `_set_keep_awake()` (`desktop_gui_pyqt.py`) calls Win32
`SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)`
when a run starts, and clears it (`ES_CONTINUOUS` alone) at every exit path:
setup failure, cancel/fail in `on_download_finished`, the early-return in
`_show_completion_summary`, both `_on_completion_finalize_*` callbacks, and
`closeEvent` as a last-resort safety net. Scope is "run start" through "post-run
verification/finalize done" - not just the extract/merge phase - since that
tail work (`StagingVerifyWorker`, `CompletionFinalizeWorker`) can also run
for minutes on a large library.

**Why**: user with an AMD RX 6900 XT reported SMK getting dramatically slower
partway through a multi-hour run, coinciding with the monitor going to sleep;
`Ctrl+Shift+Win+B` (restarts the GPU driver) was their existing workaround.
Checked the actual run log (`run_activity_20260716_204525.log`, Las account,
13,988 files): throughput was a steady ~60-90 files/min for the first ~2.5
hours, then dropped to ~10-45 files/min from roughly 23:25 to 00:20 - the
window spanning the monitor-sleep report (~23:01) and the driver restart
(~23:32) - before recovering. That's a real, measurable 2-4x slowdown, not
just a perception. Rather than try to detect/recover from the AMD post-wake
render slowdown (a driver-level issue outside SMK's control), it's simpler
and fully sufficient to just never let the display/system sleep while SMK
has active work in flight. Deliberately does NOT keep the machine awake
outside of a run - normal power saving is untouched the rest of the time.

### 2026-07-15 - raw/merged hardlinked when identical, instead of processed/copied twice

**What**: `_process_single_item()` (`smd/local_pipeline.py`) now has a fast
path: when "Also save without filters" (`keep_raw`) is on **and** the item
has no overlay to burn in, `raw_out` and `merged_out` would end up
byte-identical - so it processes once into `raw_out`, then calls the new
`link_or_copy()` (`smd/fsutil.py`) to hardlink `merged_out` to it instead of
a second full copy (photos) or ffmpeg remux (videos). `link_or_copy` falls
back to a real atomic copy if hardlinking isn't possible (different volume,
non-NTFS filesystem) - always correct, just not space/time-saving in that
case. Overlay items are completely untouched (they need genuinely different
bytes in each folder) and so is `keep_raw=False` (nothing to link from).

**Why**: this was previously ~2x the disk I/O, EXIF writes, and ffmpeg
remuxes for every no-overlay item when raw was enabled, for output that is
provably identical bytes in both folders. Flagged as the biggest throughput
win in a 2026-07-14 pipeline audit; hardlinking is the correct fix rather
than "just skip raw" because it doesn't change what the user gets - both
folders still contain a real file at the expected path, they just share the
same disk blocks.

**Non-obvious correctness constraint**: any code that "repairs" a bad
raw/merged output written after this fast path (see the two `not ok_raw` /
`not ok_merged` retry blocks in `_process_single_item`) must use an atomic,
`os.replace`-based write (`atomic_copy`, `_write_main_to_output`), never an
in-place truncate+write (`shutil.copy2` onto an existing path, `open(path,
"wb")`). Since the two paths can be the same inode, an in-place write on one
name would silently mutate the *other* hardlinked name's content too,
instead of just fixing the broken one. The pre-existing overlay-path repair
at line ~925 (`shutil.copy2(work_main, merged_out)`) is safe *only* because
that branch is never reachable when a hardlink exists - don't reuse it for
the fast path without re-checking this invariant.

**Known side effect**: `folder_size_bytes()` (used for the session summary
and Technical-view storage label) sums each file's logical size per folder,
so it double-counts hardlinked pairs - the merged/raw byte counts shown to
the user are each the full logical size, not deduplicated true disk usage.
Not fixed here (display-only, no data-safety impact); worth revisiting if
the discrepancy confuses users the way the original 125GB-vs-45GB question
did.

### 2026-07-15 - Post-run finalize + duplicate review: move remaining GUI-thread blocking work to QThreads

**What**: `CompletionFinalizeWorker` (staging delete + `build_session_report`),
`TechnicalStorageWorker` (debounced folder-size scan for Technical view),
`DuplicatePreviewWorker` (lazy duplicate-dialog thumbnails/captions), and
routing `_open_duplicate_review_if_needed`'s cache-miss fallback through the
existing `DuplicateScanWorker` instead of a synchronous hash on the GUI thread.

**Why**: two audits found the pipeline run itself was already off-thread, but
the minutes-long freeze users reported after a large run finished was still
real: Pillow re-validating every merged photo, `shutil.rmtree` on staging,
ffmpeg/ffprobe per duplicate card, and 7× recursive size scans on account-name
keystrokes were all still synchronous on the Qt main thread. This pass moves
those to background workers without changing verification thoroughness or
output correctness.

### 2026-07-15 - Safe throughput wins: ffmpeg semaphore gap, duplicate size pre-filter, x264 preset

**What**: `copy_video_with_metadata()` now runs under `ffmpeg_sem` like overlay
merges; duplicate scan buckets by file size before SHA-256; CPU x264 fallback
preset `slow` → `medium`; checkpoint flush every 25 items (was 10); duplicate
hash workers cap raised to 16; video-ordering ffprobe pool raised to
`min(16, max_workers)`.

**Why**: low-risk fixes from a throughput audit - the semaphore gap was causing
unbounded concurrent ffmpeg remuxes; size pre-filter skips hashing files that
cannot possibly be byte-identical; other tweaks reduce I/O/subprocess overhead
without touching the hardlink/GPU-hwaccel ideas deferred to a later pass.

### 2026-07-14 - Line across the top of the main tab strip: `QSS border-top: none` on `::tab` wasn't enough; needed `QTabBar.setDrawBase(False)`

**What**: `_MainTabBar.__init__()` (`desktop_gui_pyqt.py`) now calls
`self.setDrawBase(False)` on construction.

**Why**: the horizontal line the user kept seeing across the whole tab strip
was not the border on individual tabs (`QTabWidget#mainTabs > QTabBar::tab`
already had `border-top: none;` in `smd/theme.py` from an earlier, ineffective
fix attempt). It was Qt's `PE_FrameTabBarBase` primitive - a separate line the
Fusion style paints for the `QTabBar` widget itself, to visually connect the
bar to its pane. This primitive is independent of the `::tab` box model, so no
amount of QSS on `::tab` selectors touches it. `QTabBar::setDrawBase(bool)` is
the actual Qt API for suppressing it, hence the code-level fix instead of a
third QSS attempt. Verified fixed only after confirming the user was testing
a freshly rebuilt EXE, not a stale running instance - worth checking that
first next time a "the CSS fix didn't work" report comes in.

### 2026-07-14 - Fixed `NameError: name 'message' is not defined` crash on every run start

**What**: A previous refactor that split per-run disk logging out of
`append_debug_message()` into its own `_write_run_log_line()` helper left a
few trailing lines (`short = message.strip()` +
`self._refresh_run_dashboard(...)`) behind in the *new* helper instead of
moving them there deliberately - `_write_run_log_line(self, line)` has no
`message` or `phase` in scope, so this raised `NameError` unconditionally,
every single time `append_debug_message()` ran. Since the very first call
happens immediately when a run starts (logging the chosen performance
mode), this crashed *every* "Start full processing" click, before the
worker thread even began, with a `QMessageBox` showing the raw
`NameError` text and no `processing_error.log` written (the crash was in
GUI setup code, not inside the worker's own try/except). Moved the
orphaned lines back into `append_debug_message()`, where `message`/`phase`
are actually defined.

**Why it wasn't caught sooner**: the accounts tested earlier in this
session (Las) had already finished processing before this dashboard-log
refactor landed, so nothing in this session actually clicked "Start" again
until testing a second account (Mary) afterward - the bug was latent in
the built EXE the whole time. Ran `pyflakes` across `desktop_gui_pyqt.py`
and every file in `smd/` afterward to confirm no other undefined-name
bugs are lurking; only pre-existing unused-import/variable warnings
remained.

### 2026-07-14 - Video-to-JSON-row matching uses each file's own embedded creation_time

**What**: `build_deterministic_match_map()` (`local_pipeline.py`) is the
fallback used whenever a file has no Snapchat media id to match on - which,
critically, is **always**, for any bundled export where `Download Link`/
`Media Download Url` are empty (a fully-offline/bundled export, seemingly
Snapchat's current default). It used to sort same-(day,type) files by
their UID string and JSON rows by `Date`, then pair index-by-index. UID
strings have zero relationship to actual capture order, so this could -
and did - silently swap which JSON row (date/GPS/time) got assigned to
which real file whenever 2+ items of the same type shared a UTC day.

Fixed by sorting video items (only) by each file's own embedded
`creation_time`, read directly off the staged file via ffprobe *before*
SMK writes anything to it (`metadata.read_video_capture_time`). This is
the phone's own encoder timestamp, and it reliably preserves the same
relative order as the JSON `Date` field (empirically: `Date` consistently
lags a video's own `creation_time` by ~15-40s, the "saved to memories"
delay) - so sorting by it instead of by UID string gives the correct
pairing. Photos are **not** fixed by this: Snapchat strips EXIF entirely
from exported photos (confirmed empty on every sample checked), so there
is no per-file signal to sort same-day multi-photo bursts by; they remain
on UID-stem order and can still mismatch. Only probes videos in buckets
with >1 item (a lone video has nothing to be mis-ordered against, so skip
the ffprobe call) and only trusts ffprobe when it actually returns a
value, falling back a video with no readable time to the end of the
group (sorted after all timed ones) so it can't bump a correctly-ordered
neighbor out of place.

**Why**: found via a user's report that a specific video's filename
(`17-31-37`) didn't match what Snapchat's own app showed for that exact
clip (`21:56` local). Traced the video's *own* embedded `creation_time`
(read straight from the original ZIP, confirmed by content: matched the
exact scene in the user's screenshot) to `19:57:12 UTC`, one JSON row
away from what SMK had actually assigned it (`14:31:37 UTC` - a
completely different, unrelated clip's row). Rebuilding the whole day's
video group by hand confirmed **4 of 6** videos that day were mismatched
under the old UID-string sort; all 6 came out correct once sorted by
their own `creation_time` instead, each landing within a consistent
15-40s "save lag" of its JSON row. Given how common multi-video days are,
and that UID-matching is completely inert for any account with an empty
`Download Link` (seemingly the norm now), this likely affected a
meaningful fraction of every such account's video output, not just this
one clip.

**Caveat**: this only fixes *future* runs. Files already extracted before
this fix keep whatever (possibly wrong) date/GPS/name they got; fixing
them requires reprocessing from the original export ZIP, since the
correct pairing can't be reconstructed from the already-mismatched output
alone.

### 2026-07-14 - Local time uses system timezone, not GPS-derived timezone

**What**: `smd/timeutil.py`'s `to_local_datetime()` used `timezonefinder` +
`pytz` to look up the timezone at the memory's GPS coordinates and convert
UTC to *that* zone. Changed to always use the PC's own system timezone
(`date.astimezone()` with no arg), dropping `timezonefinder`/`pytz` as
dependencies entirely (removed from `requirements.txt`, `pyproject.toml`,
`smd.spec`, `NOTICE`).

**Why**: a user found a video filed as `17-31-37` from a trip to Iraq that
Snapchat's own app displayed as `21:56`. Root cause: the phone's system
timezone stayed on the user's home zone (Denmark, UTC+2) the whole trip
(no auto-update while roaming), so Snapchat displays every timestamp in the
*device's configured timezone*, never the GPS-implied one. SMK's GPS-based
conversion was "geographically accurate" but disagreed with what the
Snapchat app - and the user's memory - actually showed. Confirmed by
recomputing the raw UTC timestamps against the user's home timezone: the
numbers lined up with what Snapchat displayed once GPS was taken out of the
equation. Using the local machine's system timezone matches Snapchat's own
behavior for the common case (processing your own export on your own PC in
your own home timezone) without needing to guess a traveling phone's
clock setting, which the export JSON doesn't record. This changes output
filenames/EXIF timestamps for any future exports containing memories
captured while traveling outside the PC's timezone; already-extracted
files from before this fix keep their old (GPS-derived) names unless
manually reprocessed.

### 2026-07-12 - Single-instance lock: atomic exclusive-create, not exists()-check-then-write()

**What**: `SingleInstance.is_already_running()` (`desktop_gui_pyqt.py`) used
to `Path.exists()` the lock file, and only if absent, `open(path, 'w')` to
claim it - two separate steps with a gap between them. Replaced with one
atomic `os.open(path, O_CREAT | O_EXCL | O_WRONLY)`: the OS itself
guarantees only one caller can ever succeed when two try at the same path
at the same time, closing the gap entirely.

**Why**: found two `pythonw.exe` processes running `desktop_gui_pyqt.py`
with the exact same process-creation timestamp (real evidence, not
theoretical) - a classic TOCTOU race, plausibly from a double-click
registering twice. Both had checked "does the lock file exist?" before
either had written it, so both proceeded to build a full window: double
the startup cost (explaining a "feels slow again" report) and two windows
independently touching the same account data with no awareness of each
other. Verified the fix with a 20-thread concurrent-claim stress test:
exactly 1 winner, 19 losers, every run.

### 2026-07-12 - Tab clipping fix, round 2: setElideMode(ElideNone) + scroll buttons, plus the real culprit (an unshortened checkbox label)

**What**: removing `setExpanding(True)` (previous entry, same day) turned
out not to be sufficient - "Save memories" was still rendering clipped
("iave memorie:") in a real screenshot. Root cause of the *remaining* clip:
Qt's `QTabBar` will still shrink/elide tabs below their natural sizeHint
whenever the bar doesn't have room for all tabs at full size and can't
scroll - true even without `setExpanding`. Fixed properly with
`tab_bar.setElideMode(Qt.ElideNone)` (Qt-guaranteed: text is never
shortened) + `setUsesScrollButtons(True)` as the fallback for genuinely
insufficient width (small arrows instead of silently truncated text).

Separately, while investigating a related "content box still needs a
horizontal scrollbar" report, found the actual likely cause: the
"Keep staging media files after processing" checkbox
(`self.keep_staging_chk`) kept its full long sentence as the *visible*
label (unlike its siblings "Also save without filters" / "Technical view",
which were shortened in the 2026-07-11 width fixes) - the full explanation
was already in its tooltip, so the long visible label was pure oversight.
Shortened to "Keep staging media files". Since this checkbox only shows
with Technical view on, this cost was invisible unless you had that
setting enabled - which the primary tester does, so it was the most likely
real cause of the residual overflow, not the outer content-box cap.

**Lesson**: when adding any new Technical-view-only control, check its
*visible* label length against its siblings, not just whether it has a
tooltip - `_technical_widgets()` keeping visibility/styling in sync doesn't
catch label-length regressions.

### 2026-07-12 - GPS map (QWebEngineView) built lazily, not eagerly at every startup

**What**: `self.map_view` used to be a real `QWebEngineView()` created
unconditionally in `init_ui()`, plus a default Copenhagen map built and
loaded into it 200ms after startup (`QTimer.singleShot(200,
self.init_default_map)`). Now `self.map_view` starts as `None` with a cheap
`QLabel` placeholder in its place; `_ensure_map_view()` swaps in the real
widget (and only then builds the default map) the first time the user
opens **File Checker** - via `_on_main_tab_changed`, plus a defensive call
in `on_map_render_finished`.

**Why**: user reported startup "took forever" with a loading screen every
launch. `QWebEngineView`/`QWebEngineProfile` spin up Qt's embedded-Chromium
subsystem (confirmed via Task Manager: two separate `QtWebEngineProcess.exe`
helper processes appear the moment it's constructed) - by a wide margin the
single most expensive thing the app does at startup, paid by **100% of
launches** even though only the File Checker tab (one of five) ever uses
it. Deferring it until that tab is actually opened means most sessions
(Guide/Save memories/Help/About only) never pay this cost at all, and even
File Checker users pay it once, when they navigate there, not blocking the
initial window.

**Caveat on this investigation**: attempts to get an exact before/after
timing number via automated headless relaunches in this session were
unreliable - an `offscreen` QPA platform env var leaked from earlier GPU
testing contaminated the first round, and even after clearing it,
detached/non-interactive process launches (no real window station) hung far
longer than a real interactive desktop session reasonably would, for
reasons unrelated to this fix (confirmed by reproducing a similar hang with
WebEngine untouched). Treat the *architectural* fix (don't eagerly build
the heaviest possible Qt subsystem for a tab most sessions never open) as
solid regardless; get real-world timing from an actual interactive launch,
not headless automation, if verifying further.

### 2026-07-12 - Main tab bar: size each tab to its own text, don't force equal widths

**What**: `tab_bar.setExpanding(True)` removed from the main `QTabWidget`
setup in `desktop_gui_pyqt.py`. `TAB_PADDING_H` (`smd/theme.py`) bumped
16 -> 20 for extra breathing room.

**Why**: `setExpanding(True)` forces every tab to the *same* width
(dividing the bar's width evenly, then only giving extra room to whichever
tab's natural size already exceeds that share). On the user's real Windows
render, "Save memories" - the longest label - was getting clipped/its
letters cut off. An offscreen PyQt sizeHint measurement couldn't reproduce
clipping using its font-substitution fallback, so this is suspected to be a
real-font-metric ("Segoe UI Variable Text") width the offscreen test
couldn't replicate - rather than debug that further, switching to Qt's
default (non-expanding) per-tab sizeHint sizing removes the whole class of
risk: each tab is guaranteed at least enough width for its own text, by
Qt's own contract, regardless of what any other tab needs. Trade-off: tabs
no longer stretch to fill the full bar width on wide windows (small gap
after the last tab) - a minor cosmetic cost for guaranteed-correct text.

### 2026-07-12 - Content column max-width trimmed another 20px (1370 -> 1350)

**What**: `CONTENT_MAX_FORM`/`CONTENT_MAX_DOCS`/`CONTENT_MAX_NARROW`
(`smd/theme.py`) reduced from 1370 to 1350.

**Why**: user asked to make "the internal box of each tab" (the
`WidthAwareColumn`-capped content area) 20px narrower, as a further tweak
on top of the 2026-07-11 width fixes.

**Update, same day**: reduced further to 1270 (another -80px) per explicit
follow-up request, targeting a horizontal scrollbar the user saw at ~half
their 1440p monitor's width (~1280px window). Note this cap is often *not*
the binding constraint at that window size in the first place - see the
"Tab clipping fix, round 2" entry below for the more likely actual cause
(an oversized checkbox label) found while investigating this.

### 2026-07-12 - GPU encoder detection: probe hardware for real, don't trust ffmpeg's compiled-in `-encoders` list

**What**: `gpu_encode.py` used to pick which GPU encoder to try first by
checking whether `h264_nvenc`/`h264_amf`/`h264_qsv` appeared in `ffmpeg
-encoders` output, in that fixed priority order. Replaced with
`_working_gpu_encoder()`: a real, tiny test encode (320x240 solid color, 1
frame) per candidate, run once and cached, that only returns an encoder id
if it *actually produces output* on this machine.

**Why**: "full" ffmpeg builds (including the one SMK bundles) compile in the
NVENC/AMF/QSV wrapper code unconditionally - `-encoders` lists all three
regardless of what GPU is actually installed. On a real AMD-only machine
(RX 6900 XT, no NVIDIA hardware at all) this meant `h264_nvenc` was always
tried first, always failed, and `merge_video_overlay`'s per-file try loop
silently fell through to AMF - correct output, but one wasted failing
ffmpeg subprocess call (full process spawn + init) on *every single*
overlay video merge, forever. Confirmed empirically: before the fix, each
merge cost 2 ffmpeg calls (failed NVENC + succeeded AMF); after, 1.
`preferred_video_encoder_label()` (used for the GUI/log status line) was
also wrong as a result, unconditionally claiming "NVIDIA GPU" on this
machine.

**Gotcha hit while building the probe**: the first probe attempt used a
64x64 test frame and wrongly reported *no* working GPU encoder at all - AMD
AMF's `encoder->Init()` fails below its minimum resolution, which looks
identical to "hardware not present" if you only check the return code.
Fixed by probing at 320x240. If you ever see a GPU encoder wrongly reported
as unavailable, check resolution/pixel-format minimums before assuming the
hardware genuinely can't do it.

**Not done**: probing QSV/NVENC on real hardware (none available). Probe
logic is generic (same real-encode-attempt approach for all three) so it
should generalize, but only AMD AMF has been hardware-verified end-to-end.

### 2026-07-12 - Metadata embedding folded into the existing ffmpeg pass, not a separate remux

**What**: `copy_video_with_metadata()` (metadata.py) and
`metadata_flags` param on `merge_video_overlay()` (overlays.py) let the
capture-date/GPS `-metadata` flags ride along on whichever ffmpeg pass
already touches the video, instead of a second dedicated remux pass
afterward.

**Why**: every video was being read and written to disk twice - once to
produce the output (copy or overlay-encode), once more just to remux in the
date. On a ~14,000-file library with mostly short clips, that per-file fixed
overhead (process spawn + full read/write) adds up more than raw
compute/GPU-encode time does. Verified via synthetic-video smoke tests
before rollout (creation_time/location land correctly in both paths); full
`pytest` suite green.

**Not done**: raising `max_ffmpeg` concurrency further. Measured on a real
run (Ryzen 7800X3D, 16 threads, 5 concurrent ffmpeg @ "maximum" mode): CPU
~37%, GPU video-codec engine only 5-9% used per job, but the GPU's *shared*
3D/shader engine (used for scaling/compositing before hardware encode) was
near-saturated in aggregate across the 5 jobs. More parallelism likely
wouldn't help and could destabilize AMF encoding, which doesn't reliably
support unlimited concurrent sessions. The concurrency cap is a hardware
constraint, not a software throttle worth loosening.

### 2026-07-11 - "Keep staging media files" checkbox, Technical-view-only, red text for all technical controls

**What**: new checkbox skips the automatic post-run staging ffprobe check
and silent auto-delete entirely. Only visible with Technical view on;
defaults to **off**. All Technical-view-only controls now render in red
(`smd.theme.technical_text_style`).

**Why**: the average SMK user will never open Technical view and has no
mental model of "staging" - for them, silent verify-then-delete-on-success
after a run is correct and expected, and must stay the default. The
checkbox exists purely as an opt-out for people who want to manually inspect
`technical/staging/` before it's gone. Red text makes "these are advanced,
not for you" visually obvious at a glance rather than requiring the user to
read every tooltip.

**Side effect used deliberately**: when the checkbox is on, the expensive
ffprobe-every-video check is skipped entirely (not just the delete) since
there's no point verifying what you're not going to delete - this also cuts
post-run wait time for people who choose it.

### 2026-07-11 - Verification uses the exact same matching function as processing

**What**: `staging_check.py` calls `build_match_map()` - the same function
`local_pipeline.py` uses to actually process files - instead of a separate,
older `build_deterministic_match_map`.

**Why**: a real "Las" account run was 100% successful but "Verify staging"
reported 41 files missing. Root-caused to two independent bugs: (1)
verification didn't know about files the user intentionally deleted via
duplicate review (fixed by reading the `duplicates_deleted_report_*.json`
audit trail), and (2) verification's matching logic could disagree with the
pipeline's own matching logic for items sharing a media UID, because one
iterated a dict in insertion order and the other didn't. Using one shared,
deterministically-ordered function for both eliminates the class of bug
entirely rather than just patching the symptom.

### 2026-07-11 - Processing UI lockout redesigned: dim sections, don't cover the dashboard

**What**: `ProcessingShieldOverlay` (full-window, blocks all input) is now
only used for the short, non-cancelable post-run staging verification.
During the actual run, `_set_run_lockout()` dims/disables Setup, Performance,
and After-processing sections individually and leaves Run (Start/Cancel) and
the Live Run Dashboard fully interactive.

**Why**: the old full-window overlay covered the dashboard too, so users
could not scroll their own live log while a multi-hour run was in progress -
exactly when they'd most want to review it. There was nothing about
"dashboard" that needed to be locked; only settings that could corrupt an
in-flight run needed disabling.

### 2026-07-11 - Video encode quality recalibrated (CRF 0 → 16, "lossless" GPU presets → quality-targeted)

**What**: `gpu_encode.py` overlay-merge encode settings changed from
CRF 0 / literal-lossless GPU presets to VMAF-calibrated "visually lossless":
x264 CRF 16, NVENC CQ 18, AMD AMF QP 22, Intel QSV global_quality 18.

**Why**: literal lossless re-encoding of already-lossy source video produced
enormous files (a `merged/` folder several times the size of `raw/`/staging)
for zero perceptible quality gain over the original. VMAF comparison showed
these settings are visually indistinguishable from lossless at a fraction of
the file size.

### 2026-07-11 - Duplicate detection: content hash, not a separate folder, log-only with permanent delete on request

**What**: `duplicates.py` hashes `merged/` content (SHA-256, byte-for-byte),
not filename/date heuristics. Detected duplicates stay in place - **no**
separate "Duplicates" folder is created. The review dialog lets the user
pick which copy(s) to keep; anything not kept is **permanently deleted**
from both `merged/` and `raw/`, recorded in a dated JSON audit report.

**Why**: an earlier idea (move duplicates into a dedicated folder for
later review) was explicitly rejected by the user in favor of keeping
everything in the normal output folders and only touching disk on an
explicit "delete" action. Scanning is expensive (hashes every file) so it's
cached to `reports/duplicates_report.json` and runs on a background thread
so it never freezes the GUI.

### 2026-07 - Offline-only by design; link-only exports rejected, not worked around

**What**: `export_detect.py` only supports exports where media is actually
bundled inside the ZIP. "Link-only" exports (JSON with download URLs,
requiring a live network fetch from Snapchat's CDN per item) are detected
and rejected with a clear message - not partially supported.

**Why**: product decision for reliability and user trust - no telemetry, no
upload, no dependency on Snapchat's servers staying available or the user's
network. Every known competitor (free or paid) has this exact same
limitation, so it isn't a competitive disadvantage worth extra engineering
or a "workaround" doc.

### 2026-07 - Windows-only; no macOS/Linux/mobile build planned by the maintainer

**What**: official target is Windows 10/11 (64-bit) only. The PyQt5 source is
cross-platform in principle but is not built, tested, or supported on any
other OS.

**Why**: maintainer has no non-Windows hardware to build or test on.
Contributions porting to other platforms are welcome (see `README.md`) but
won't be started proactively.
