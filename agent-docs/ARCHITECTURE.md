# SMK Architecture Map (for AI agents)

**Read this first when picking up work on SMK. This is a navigation aid and a
record of non-obvious behavior, not a full spec.** Code changes constantly;
this file can go stale. Always verify exact current behavior by reading the
referenced file/function before making changes or answering a user's
question about behavior - especially anything load-bearing (data safety,
file deletion, matching logic).

**Update the relevant section of this file (and `DECISIONS.md` if it's a
"why" decision) whenever you make a structural or behavioral change.** See
`.cursor/rules/agent-docs.mdc` for the enforcement rule.

**Related:** [AUDIENCE_BRIEFING.md](AUDIENCE_BRIEFING.md) — comprehensive CEO / PM / developer product briefing (v1.0.0).
[QUALITY_SPRINT_PLAN.md](QUALITY_SPRINT_PLAN.md) — locked Trust-first sprint (duplicates → export UX → outcome).
[QUALITY_ASSESSMENT.md](QUALITY_ASSESSMENT.md) — Cursor Pro + Perplexity assessment for boss review/correction.

## What SMK is

A Windows desktop app (PyQt5, packaged with PyInstaller as `SMK.exe`) that
processes a Snapchat "Memories" data export ZIP entirely offline: extracts
bundled media, merges Snapchat overlay filters (stickers/text/drawings) onto
photos and videos, embeds capture date + GPS metadata, and verifies the
result. No network calls in the core pipeline. Not affiliated with Snap Inc.

**Product brand:** Snapchat Memories Keeper (`SMK`). Constants live in
`smd/branding.py`. The Python package folder remains `smd/`; AppData
`%LOCALAPPDATA%/SnapchatMemoriesDownloader/` and
`QSettings('SnapchatMemories','Downloader')` stay on legacy names so
existing accounts/settings are not orphaned. Single-instance focus matches
both current and legacy window titles via `matches_window_title()`.

## Top-level layout

- `desktop_gui_pyqt.py` - thin entry script (~550 lines): early
  `pythonw` stdout redirect, `DownloaderGUI` (`__init__` + slim `init_ui`
  shell that wires tab mixins), and `main()`. Dev launch is Desktop
  `SMKTester.bat` (foreground `.venv\Scripts\python.exe`; close console
  closes SMK). PyInstaller ships `SMK.exe` under `dist/smd/`.
- `gui/` - split-out desktop GUI package (mixin pattern, zero behavior
  change from the old god file). See "GUI" below for the class map.
- `smd/` - all backend logic, importable independently of the GUI (and unit
  tested that way - see `tests/`). Package name is historical; product is SMK.
- `tests/` - pytest suite, no GUI/Qt dependency, runs in ~1s. Most files
  each unit-test one helper in isolation (matching, naming, hardlinking,
  staging checks). `test_full_pipeline_integration.py` is the exception -
  it drives the real top-level entry point (`local_pipeline.
  process_bundled_export`) against a synthetic-but-real ZIP (real JPEGs,
  a real tiny MP4 via the bundled ffmpeg) end to end: extract -> JSON
  match -> merge/hardlink -> checkpoint -> simulated-crash resume ->
  `check_staging_readiness`. This is the net that would actually catch a
  bug that loses/corrupts memories; the narrower unit tests can't, since
  each one mocks or bypasses the surrounding orchestration. Skips itself
  if ffmpeg isn't resolvable in the environment.
- `agent-docs/` - this file, `DECISIONS.md`, `AUDIENCE_BRIEFING.md`, and packaging/publishing docs.
  Kept separate from user-facing `README.md`.
- `build_smd.ps1`, `smd.spec` - PyInstaller build. `tools/ffmpeg/` holds the
  bundled ffmpeg/ffprobe binaries (not built by us; downloaded, see
  `agent-docs/ALL_IN_ONE_PACKAGING.md`).

## Account folder layout (`smd/account_layout.py`)

Per account name (always suffixed `-memories`, e.g. `Las-memories` -
`ensure_memories_suffix()`), two roots:

- **User-facing**: photos/videos live directly in the account folder
  (`Desktop/<account>/` for simple mode; `<base_dir>/<account>/` for
  technical - default base is Desktop). No parent `Memories/` wrapper and
  no nested `account/Memories/`. Only gets nested `merged/` (+ `raw/`) when
  "Also save without filters" (`keep_raw`) is on. Controlled by the
  `keep_raw` kwarg on `AccountPaths.for_account()`/`for_user()` - never
  infer it from the live checkbox for an *existing* account (see persisted
  layout below).
- **Technical** (`technical/` inside the account folder for technical-mode
  accounts; `%LOCALAPPDATA%/SnapchatMemoriesDownloader/accounts/<account>/technical/`
  for simple-mode ones): `staging/`, `json/`, `reports/`, `checkpoint/`,
  `quarantine/`, `logs/`, `debug/`, `account_identity.json` (account name +
  mydata IDs + layout bookkeeping - no Snapchat username/display name).

`AccountPaths` is the source of truth; resolve via
`resolve_account_paths()`/`_account_paths()`. Legacy nested `Memories/` /
`downloads/` and Desktop/`Memories` or `SMD Media` parent wrappers are
lifted by `migrate_account_layout()` /
`migrate_accounts_out_of_desktop_wrapper()`.

**Persisted per-account layout is the only source of truth for an existing
account** (`save_account_layout_info()`/`load_account_layout_info()`/
`resolve_existing_account_layout()`, written into the same
`account_identity.json` as the mydata-ID bookkeeping below). Records
`layout` (`"simple"` or `"technical"`), `base_dir` (technical only), and
`keep_raw` the *first* time an account is created, and every later lookup
(`_account_paths()` in `save_memories_tab.py`) trusts that over today's live
Technical view toggle / "Also save without filters" checkbox. This is the
fix for a real bug (2026-07-19): before this existed, toggling Technical
view after creating an account made every "After processing" button resolve
to a different, wrong, usually-empty folder. An account created before this
bookkeeping existed (no stored info) falls back to whichever location
actually has a folder on disk.

**Legacy on-disk layouts get migrated/flattened lazily, not just on
create=True.** `_account_paths(name, create=False)` (a plain lookup, e.g.
"Confirm output folder" for an old account, or any After-processing button)
still runs `migrate_account_layout()` whenever the account directory already
exists - migration is pure renames, never invents folders, so it's safe on
a read path. Two real legacy shapes it fixes up:
- `downloads/` → `Memories/` rename (see above).
- `collapse_merged_to_flat()`: accounts created before `keep_raw` existed
  always nested `merged/`(+`raw/`) even with no raw copies. If a `keep_raw`
  account has no `raw/` content, its `merged/` contents get moved up flat.
  Genuine `keep_raw=True` accounts (real `raw/` content present) are left
  nested - flat can't hold two variants.
- `migrate_account_layout()`'s directory-merge step recurses
  (`_deep_merge_dir()`) rather than doing a single shallow level. This
  matters because `ensure_dirs()`/`ensure_user_dirs()` can pre-create empty
  `Memories/merged/`+`Memories/raw/` stub folders *before* migration runs
  (`create=True` path); a shallow merge would see "`Memories/merged`
  already exists" and skip the whole legacy `downloads/merged/` folder,
  silently orphaning every file inside it. Regression-tested in
  `tests/test_account_layout.py::test_migrate_account_layout_keeps_nesting_when_keep_raw_true`.

**Single "which account" source in `save_memories_tab.py`** (2026-07-19
rework - replaced the old per-export `AccountRunChoiceDialog` modal and the
separate "After processing" account combo, which used to fall out of sync
with each other):
- `_active_account_name` (set only via `_set_active_account()`) is the one
  account every part of the tab acts on - the next run, and every "After
  processing" button. `_account_name()` / `_after_processing_account_name()`
  are both thin aliases onto it now.
- The **Account** section (top of the Save memories tab, before Export) is
  an explicit toggle, never a silent guess:
  - **New account** - `QLineEdit` (`new_account_name_edit`) only. Live
    preview shows the folder name (auto `-memories` suffix). Folder is
    created when the user hits **Start processing** (`create=True` in
    `start_download` / `_set_active_account`). No separate Create button.
  - **Existing account** - `old_account_label` shows the best candidate from
    `_list_known_accounts()` (defaults to last-used via
    `QSettings('last_account_name')`); "Change output folder" picks another.
  - `active_account_label` (an `infoBanner`) always shows the current
    active account name and its real on-disk `library_root` once one is
    picked - this is the *only* place the resolved save location is shown;
    there is no separate "Where to save"/project-name field.
- `_list_known_accounts()` unions two disk scans (base_dir's direct
  children for technical-mode accounts, `Desktop/`'s direct children for
  simple-mode ones) - **must exclude the technical base_dir folder itself**
  when it happens to live directly on the Desktop (custom base dirs can be
  `Desktop/<anything>`; default base is Desktop itself). Without this
  exclusion a non-empty base_dir container can be mistaken for a
  simple-mode account - found and fixed 2026-07-19.
- Choosing an export ZIP/folder (`select_export_folder()` - one unified
  folder-picker button, no more separate "Choose ZIP files"/"Choose folder")
  only *suggests* an account (`_suggest_account_from_export()`, non-blocking,
  pre-selects "Old account" only if this exact export's `mydata~ID` was seen
  before) - it never creates or activates anything by itself. No manual
  "Where to save"/project-name field, and no reading of the export's
  `account.json`/`account_history.json` for naming (removed 2026-07-19, see
  `DECISIONS.md` - avoids any UX implying users should request/expose that
  personal data just for folder naming).
  `save_account_identity()` persists `account_name` + the export's
  `mydata~ID` (batch id, not Snapchat username/display name) so re-selecting
  the same export can pre-select "Old account" with the right folder - never
  used to invent a name from profile data.
- "After processing" buttons (`_refresh_after_processing_actions()`) are
  enabled purely from what's actually on disk for the active account
  (`has_merged`/`has_debug` via `_folder_has_files()`), independent of the
  live Technical view toggle - greyed out until there's something real to
  act on. Technical-only After buttons (**Review duplicates**, Open debug)
  are visibility-gated via `WindowChromeMixin._technical_widgets`. Open
  technical / Verify staging were removed (Add run info + automatic staging
  cleanup cover those jobs).

## Processing pipeline (`smd/local_pipeline.py`)

Entry point: `process_bundled_export(...)`. Rough flow:

1. **Detect export format** (`smd/export_detect.py`) - bundled media in the
   ZIP vs "link-only" (JSON with download URLs, no media) which SMK
   deliberately does not support (offline-only by design). Analysis also
   reports JSON row count, year span, ZIP total bytes, and whether download
   URLs are empty (normal for bundled). GUI Start soft-warns if free disk is
   under `(1× or 2× ZIP) + ~5 GB` — 2× when “Also save without filters” is on
   (Cancel / Continue anyway). Snapchat ZIPs ≈ cloud size (Las ~49 GB ZIP ≈
   50.6 GB cloud); filters-only finish ≈ ZIP, keep_raw ≈ 2× ZIP.
2. **Extract ZIP(s) to `staging/`** - main/overlay files are paired by
   filename pattern `<date>_<uid>-main.<ext>` / `<date>_<uid>-overlay.<ext>`.
   ZIP entry mtimes are restored onto extracted files (needed for photo
   matching below).
2b. **Auto-dedupe staging** (`smd/duplicates.dedupe_staging_items`) - drop
   byte-identical then same-content staging mains (keep oldest stem name,
   delete extras + overlays) *before* match/encode. See DECISIONS 2026-07-31.
3. **Match staging items to JSON rows** - `build_match_map()` matches by
   Snapchat media UID first (`mid=` in `Download Link`/`Media Download Url`
   - **always empty, and thus always a no-op, for fully-bundled exports**),
   falling back to `build_deterministic_match_map()`'s date/type positional
   matching, which is what actually runs for most accounts. Within a
   same-day, same-type bucket: videos sort by each file's own embedded
   `creation_time` (ffprobe); photos sort by restored ZIP entry mtime when
   those times are usable (not all identical), else UID-stem order. Iterates
   `items.items()` in **sorted-by-stem order** for media-id matching
   determinism. See DECISIONS.md 2026-07-14 (videos) and 2026-07-26 (photos).
4. **Process items** - `_process_single_item()`, via `ThreadPoolExecutor`.
   When **keep_raw** is on: **two phases** — (1) all missing raw copies
   (`only="raw"`), then (2) all missing merged/overlay outputs
   (`only="merged"`). When keep_raw is off: a single merged pass. If merged
   already exists and only raw is missing, phase 1 fills raw and **skips**
   overlay re-encode (see DECISIONS 2026-08-04).
   - **No overlay + raw enabled** → fast path: process once into `raw_out`,
     then `link_or_copy()` (`smd/fsutil.py`) hardlinks `merged_out` to it
     instead of a second copy/remux - raw/ and merged/ are byte-identical in
     this case, so this is the same file on disk with zero extra I/O or
     space. Falls back to a real copy on non-hardlink-capable filesystems.
     See DECISIONS.md, "raw/merged hardlinked when identical" (2026-07-15).
   - **No overlay + raw disabled** → merged file is copied (or WebP→JPEG
     converted for images) straight to the output; no raw file at all.
   - **Overlay present** → `merge_image_overlay` (Pillow + exif_transpose,
     resize overlay to main) or `merge_video_overlay` (ffmpeg `-loop 1` on
     the PNG, then `scale2ref` + overlay with `shortest=1`) in
     `smd/overlays.py` for `merged_out`;
     `raw_out` (if enabled) still gets the unfiltered original via its own
     copy/remux - these two are genuinely different bytes, so never
     hardlinked. See DECISIONS.md 2026-07-29 (zoomed-caption + 1-frame fixes).
   - Metadata (`smd/metadata.py`) embeds capture date + GPS. For videos this
     is folded into whichever ffmpeg pass already touches the file (overlay
     merge, or `copy_video_with_metadata` for the no-overlay case) rather
     than a second separate remux - see DECISIONS.md, fixed 2026-07-12.
   - `validate_media_file()` (`smd/media_integrity.py`) does a cheap
     magic-byte check on every output in real time (not a full ffprobe -
     that only happens post-run, see Staging verification below).
   - Any "repair a bad output" retry on a hardlinked pair always uses an
     atomic (`os.replace`-based) write, never an in-place truncate+write -
     the latter would silently mutate both hardlinked names at once instead
     of just the broken one.
5. **Checkpoint** (`checkpoint/local_checkpoint.json`) saved every ~25 items
   so an interrupted run can resume without reprocessing everything. Stores
   `completed_stems` / `skipped_stems` plus `output_by_stem` (the filename
   actually written) so a later rematch cannot mark a finished file "missing"
   under a new planned name (see DECISIONS 2026-07-31).
6. **Post-run**: session report + staging verification (see below).

### Concurrency model (`smd/system_profile.py`)

- Performance modes: `maximum` (0.8 × logical CPUs), `balanced` (0.6×,
  default and persisted across launches), `conservative` (0.4×, used
  automatically on low battery).
- `max_ffmpeg` (concurrent ffmpeg subprocesses) is capped separately from
  worker count, tiered by RAM (1 if <8GB; up to 6 if ≥32GB) - GPU hardware
  encoders (AMF/NVENC/QSV) don't reliably support unlimited concurrent
  sessions, so this is a deliberate ceiling, not just a CPU/RAM guess.
- GPU encoder selection (`smd/gpu_encode.py`, `detect_video_encode_profiles()`):
  a one-time, cached, real test-encode probe (`_working_gpu_encoder()`)
  determines which single GPU encoder (NVENC, AMF, or QSV) actually works on
  *this* hardware - checking ffmpeg's `-encoders` list alone is not enough,
  since full ffmpeg builds compile in all three vendor wrappers regardless
  of what GPU is installed. Only that one GPU profile (if any) plus CPU
  x264 are returned; `merge_video_overlay` still tries them in order and
  falls back to CPU if the "working" one somehow fails on a specific file.

### Overlay/GPU encoding quality (`smd/gpu_encode.py`, `smd/overlays.py`)

Video overlays are scaled to the main frame via ffmpeg `scale2ref` before
compositing (Snapchat overlay PNGs rarely match video resolution). Encode
quality (`smd/gpu_encode.py`): x264 CRF 14, AMD AMF QP 18, NVENC/QSV 16 -
sharper than the 2026-07-11 "visually lossless" tune, still far below the
old CRF 0 / QP 0 size blow-up. See DECISIONS.md 2026-07-29.

## Duplicate detection (`smd/duplicates.py`)

**Policy (2026-07-31):** by default extras are **auto-deleted**; keeper =
`keeper_filename()` (oldest `YYYY-MM-DD_HH-MM-SS…` name, then shortest).
Technical view → **Keep duplicates for review** sets
`auto_delete_duplicates=False` (skip staging dedupe + post-run delete; still
scan). Audit: `reports/duplicates_deleted_report_*.json` or staging reports.
Manual **Review duplicates** (Technical view) for leftovers / manual mode.

**Cancel:** `should_stop` is checked during ZIP extract, staging dedupe
hashing, encode, and late duplicate scans. Cancelled runs return
`stats.stopped_by_user` (GUI shows Stopped, not the success summary).

**Already-complete fast path:** `library_already_complete()` — if every
checkpoint output exists and ZIP main stems are accounted for
(done/skipped + `load_staging_removed_stems`), skip extract/encode; still
run a quick late duplicate safety check.

**Early (staging, before match/encode):** `dedupe_staging_items()` — byte
then visual — removes duplicate staging mains + overlays so they are never
processed.

**Late (merged/, after process):** `scan_content_duplicates` /
`scan_visual_duplicates`, then `auto_delete_duplicate_extras()` on
`merged/` (+ `raw/` when enabled).

- **Byte:** whole-file SHA-256 (same-size buckets only).
- **Visual/deep:** decoded content hash (ffmpeg video MD5 / PIL RGB) — not
  "looks similar"; same pixels/stream. Caches (size+mtime):
  `duplicates_visual_hash_cache.json` (merged/) and
  `duplicates_staging_visual_hash_cache.json` (staging; survives staging
  delete). First full visual pass is slow; repeats are cheap. Do not
  reintroduce ffprobe pre-filters (tried/reverted 2026-07-19 — slower).

## Staging verification (`smd/staging_check.py`)

`check_staging_readiness()` ffprobes **every** video (not a sample) plus
checks every staging item has a matching file in `merged/`/`raw/`, using the
*same* `build_match_map()` the real pipeline uses (a past bug used a
different/older matching function here, causing false "missing" reports -
fixed 2026-07-11). Excludes files intentionally removed via duplicate review
(reads the audit report above) from the "missing" count.

This check is expensive (minutes on a large library) and runs in
`StagingVerifyWorker` / `CompletionFinalizeWorker` (background), not on the
GUI thread. **Automatically after every run** — if 100% clean,
`technical/staging/` is deleted silently. There is no manual Verify staging
button and no "keep staging" option (removed 2026-07-30 / 2026-08-01): unpack
reuse only saved minutes on Las-scale runs, while keeping ~tens of GB of
staging confused users. If verify fails or errors, staging is left alone.

`SessionReport.summary_html()` (`smd/session_report.py`) leads with a
completeness banner (green/red/neutral) answering "did I lose any files?"
before anything else - built from `readiness.staging_main_count` (ground
truth: how many memories were actually found to process) vs
`outputs_verified`/`missing_merged`/`missing_raw`. Next section **"How many
memories"** (from `LocalProcessStats`) shows Snapchat JSON row count, ZIP
media before dedupe, duplicates removed early/late, this-run processed vs
library size — without claiming library always equals the JSON row count.

## GUI (`gui/` package + thin `desktop_gui_pyqt.py`)

Main window: `DownloaderGUI(WindowChromeMixin, GuideTabMixin,
SaveMemoriesTabMixin, FileCheckerTabMixin, CompletionMixin,
PalestineTabMixin, HelpAboutTabMixin, QMainWindow)`. Mixins must precede
`QMainWindow` so Qt virtuals like `closeEvent` resolve to the mixins (see
DECISIONS 2026-07-29). Mixins share `self` with the main window - method
bodies moved, call sites unchanged. One-way import rule: `gui/tabs/*` and
`gui/window_chrome.py` may import from `gui/common.py` /
`gui/widgets.py` / `gui/workers.py` / `gui/dialogs.py`, never from each
other or back into `desktop_gui_pyqt.py`.

Layout of `gui/`:

- `common.py` - `ROOT`, `TAB_SAVE_MEMORIES`, WebEngine availability,
  panel builders, `play_happy_tone`, `startup_log`, etc.
- `widgets.py` - reusable widgets (`DocBrowser`, `WidthAwareColumn`,
  `LiveRunDashboard`, `ProcessingShieldOverlay`, `_MainTabBar`, …).
  `WidthAwareColumn` hard-caps the context column to the tab scroll
  viewport (or `mainTabs` pane inner width); inset ≈ 12px
  (`TAB_PANE_PADDING` + `TAB_CONTENT_MARGIN_H` in `theme.py`).
- `workers.py` - all eleven `QThread` workers + map/thumbnail helpers.
- `dialogs.py` - `DuplicateCompareDialog`, `SessionSummaryDialog`,
  `DuplicateReviewDialog`.
- `single_instance.py` - single-instance lock.
- `window_chrome.py` - `WindowChromeMixin` (theme, nav/section helpers,
  technical-view toggle, close/cleanup).
- `tabs/guide_tab.py`, `tabs/save_memories_tab.py`, `tabs/completion.py`,
  `tabs/file_checker_tab.py`, `tabs/help_about_tabs.py` - tab mixins.

Shell chrome in `DownloaderGUI.init_ui`: `#appHeader` (logo/title, a bold
clickable `self.free_palestine_label` - flag emoji + "Free Palestine"
linking to matwproject.org - just left of the Support button, then theme
toggle), then `#tabsShell` with the six tabs.

Six tabs (`self.tabs`): **Guide**, **Save memories** (Setup / Performance /
Run / After-processing via `_rebuild_process_controls_grid`), **File
Checker**, **Help**, **About**, **Palestine** (`gui/tabs/palestine_tab.py` +
`smd/palestine_content.py` — external resource links and solidarity framing;
opens links in browser). The tab bar does **not** use
`setExpanding(True)` - each tab sizes to its own text via Qt's normal
sizeHint so "Save memories" cannot get clipped (fixed 2026-07-12).

Key background workers (`gui/workers.py`) - anything that could take more
than a fraction of a second runs off the GUI thread:

- `LocalExportWorker` - runs `process_bundled_export`; parses
  `__SMD_STAGE__|n|total|title` and `__SMD_PROGRESS__|current|total` into
  `stage` / `progress` signals. Progress bar is determinate 0–100% **per
  stage** (resets on each stage). Pipeline stages 1–5; GUI stage 6
  ("Finishing last touches") runs in `CompletionMixin` after the worker
  exits — happy tone / "All done" only after finalize finishes.
- `StagingVerifyWorker` / `StagingCheckWorker` - staging readiness check.
- `DuplicateScanWorker` - byte (SHA-256) duplicate scan.
- `VisualDuplicateScanWorker` - decoded-content duplicate scan (opt-in, slow).
- `MapRenderWorker`, `MapWorker`, `ScanWorker` - File Checker tab.

`self.map_view` is **not** created in `init_ui()` - it's `None` behind a
placeholder until `_ensure_map_view()` (`FileCheckerTabMixin`) runs on
first File Checker open (`WindowChromeMixin._on_main_tab_changed`).
Constructing a `QWebEngineView` spins up Qt WebEngine (separate helper
processes); doing it eagerly made every launch pay that cost (fixed
2026-07-12). Any new code that touches `self.map_view` must call
`self._ensure_map_view()` first.

## File Checker tab (report-only, `gui/tabs/file_checker_tab.py`)

Folder pick: `resolve_check_folder()` (`smd/media_types.py`) prefers
`merged/` over `raw/` when the user selects a parent that contains both
(same memories — scanning both would double-count). The green label and
report preface show which folder is actually checked.

Mid-scan status stays quiet (`_set_check_status_quiet`): step labels + 25%
buckets only — no spinner; progress bar and Cancel still update freely.

`run_full_analysis()` always runs `ScanWorker(..., dry_run=True)` - it never
renames anything. Extension fixing is not a separate step users need to run:
it already happens automatically inside `_fix_extension()`
(`smd/local_pipeline.py`) as part of every "Save memories" run, before a
file is written to `merged/`/`raw/`. File Checker exists to (a) report
extension mismatches on *any* folder, including ones SMK never touched, and
(b) show media stats + the GPS map - not to fix SMK's own output (fixed
2026-07-17; previously it silently renamed files, which conflicted with the
"check only" mental model this tab should have).

After the GPS scan, `_apply_scan_report` replaces the metadata panel with one
HTML library-check report from
`smd.file_checker_report.build_library_check_report` (`QTextEdit#libraryCheckReport`:
bold section titles, short rules, light section/item emoji — dates, GPS
embedded vs JSON vs missing with year breakdown, TOP PLACES, full photo WxH
list with soft size notes from `smd.resolution_notes` — never phone brand
guesses). Extension dry-run results fold into a one-liner; verbose
`ScanWorker` log lines are not shown.
`MapWorker` collects `resolution_counts`, `with_date`/`without_date`, and
`no_gps_years` in one pass (`_image_dimensions()` for photos only — video
dimensions skipped: ffprobe-per-file cost not worth it).

Map markers have hover tooltips (thumbnail preview) only — no click popup.
Marker `click` looks up `window.fileData` by lat/lng and sets
`window.pyOpenFile`. The GUI polls that and opens photos/videos with the
OS default app (`QDesktopServices.openUrl` → Photos / Media Player on Windows).

Map tiles: `_create_themed_map(dark=...)` builds with `tiles=None` and adds
base layers with only the theme default `show=True` (CartoDB Dark Matter in
dark mode, Terrain/OpenTopoMap in light). Other base layers use `show=False`
so LayerControl does not leave the wrong layer selected. Used for
`init_default_map` and Check-folder renders. Theme toggle calls
`refresh_map_for_theme()` to rebuild the open map (pan/zoom resets).

**"Technical view" checkbox** gates visibility of advanced controls
(**Keep duplicates for review**, **Review duplicates**, **Add run info to
finished folder** → `SMK-run-info/`, Open debug, `technical_storage_label`) -
see `_technical_widgets()` / `_apply_technical_view_ui()`. Labels/checkboxes
may use `technical_text_style()`; buttons keep normal toolbar colors.
Disabled After-processing buttons use a flat dashed muted style.
**Performance** is always visible.

**Processing UI lockout**: while a run is active, `_set_run_lockout()` dims
and disables Setup/Performance/After-processing sections but leaves the Run
section (Start/Cancel) and the Live Run Dashboard fully interactive and
scrollable. End-of-run verify/finalize keeps Progress stage/bar updating and shows a
centered `ProcessingShieldOverlay` (“Almost done…”) as a failsafe so the UI
never looks frozen before `SessionSummaryDialog`. Overlay hides when the
summary appears.

**Single instance**: `SingleInstance` class + a signal file in the temp dir -
launching SMK while it's already running focuses the existing window (and
flashes the taskbar) instead of opening a second one. A live owner is never
force-killed just because the show-signal lingered during a busy run.

**Keep-awake during a run**: `_set_keep_awake()` wraps Win32
`SetThreadExecutionState` to stop the system/display from sleeping between
run start and the end of post-run verification/finalize (all the
`_set_keep_awake(False)` call sites mark true "run is fully done" points,
not just when `_set_run_lockout(False)` fires - that happens earlier, before
verification). See DECISIONS.md, "Keep system/display awake for the
duration of a run" (2026-07-16).

## Module map (`smd/`)

| Module | Responsibility |
|---|---|
| `local_pipeline.py` | Core processing pipeline (see above) |
| `overlays.py` | Burn overlay onto image (Pillow) or video (ffmpeg) |
| `metadata.py` | Embed EXIF/GPS (images), container date/GPS + iTunes atoms (video); read GPS back out for the map |
| `gpu_encode.py` | Detect/rank GPU video encoders, quality profiles |
| `system_profile.py` | Hardware detection → worker/ffmpeg concurrency limits |
| `export_detect.py` | Bundled vs link-only detection; year span + ZIP bytes for UI |
| `account_layout.py` | Folder layout for one account (user + technical) |
| `duplicates.py` | Byte (SHA-256) + decoded-content duplicate detection |
| `staging_check.py` | Post-run completeness/integrity verification |
| `media_integrity.py` | Cheap real-time output validation (magic bytes) |
| `video_repair.py` | Best-effort repair of corrupt/incomplete source video |
| `session_report.py` | Post-run summary shown to the user |
| `time_estimate.py` | Rough ETA in Performance — file count + video/overlay mix (+ ZIP GB for extract only). Tuned on Las Maximum **3h33m** and Mary Maximum **~7 min** |
| `map_gps.py` | GPS lookups for the File Checker map |
| `file_checker_report.py` | Library-check summary text (dates, GPS gaps, sizes) |
| `resolution_notes.py` | Soft WxH labels for File Checker (no phone brands) |
| `media_types.py` | Shared media extension sets for scanners / File Checker |
| `fsutil.py` | Atomic file writes (crash/disk-full safe); `link_or_copy()` hardlinks byte-identical outputs with an atomic-copy fallback |
| `ffmpeg_bundle.py`, `procutil.py` | Resolve bundled ffmpeg/ffprobe, subprocess flags (hide console windows on Windows) |
| `theme.py` | Design system - colors, spacing, Qt stylesheets |
| `guide_content.py`, `help_content.py`, `about_content.py`, `palestine_content.py` | Doc-tab HTML; titles use `headed_title` + `inject_title_rule_image`. Theme toggle defers rebuild via `_schedule_doc_theme_sync` (About facts cached) so chrome flips first |
| Save Memories section titles | `WindowChromeMixin._add_section_title` + `QFrame#sectionTitleRule` (not QLabel border) |
| Window resize → all tabs | `WindowChromeMixin.resizeEvent` debounces `_refresh_all_content_columns` so hidden tabs track width (stacked pages skip resizeEvents) |
| `models.py` | `Memory` dataclass (one JSON row) |
| `runtime.py` | Path resolution for frozen (PyInstaller) vs source runs |

## Known sharp edges

- `_process_single_item` writes raw before merged, per item - see pipeline
  step 4 above. Don't assume a two-phase global pass.
- Every video costs at least 1 ffmpeg subprocess call even with no overlay
  (metadata embedding needs a real remux; mutagen alone can't set the
  container-level `creation_time` that Explorer/Google Photos read).
- `build_match_map` must stay in sync between `local_pipeline.py` (actual
  processing) and `staging_check.py` (verification) - they must use the
  *same* function, or verification will falsely disagree with what actually
  got written.
- QSS/Qt stylesheet specificity: a widget's own `setStyleSheet()` beats an
  app-wide rule targeting it by object name or property selector. When
  styling a specific existing widget (e.g. red "technical" text), prefer
  setting it directly on the widget instance rather than fighting
  specificity in the global stylesheet. Relatedly: a generic
  `QPushButton:disabled` rule does NOT automatically apply to
  `QPushButton#accentBtn`/`#toolbarBtn`/`#runAction` - their own non-`:disabled`
  object-name rules win by specificity and made disabled buttons look
  identical to enabled ones until explicit `#id:disabled` rules were added
  (`smd/theme.py`, 2026-07-19). Same pattern applies to `QLineEdit`/
  `QComboBox`/`QSpinBox`/`QLabel` - each needs its own explicit `:disabled`
  rule, a bare `:disabled` on the base type is not enough once anything
  more specific targets that widget.
- **`QSettings('SnapchatMemories', 'Downloader')` is real, global Windows
  registry state** (`HKEY_CURRENT_USER\Software\SnapchatMemories\Downloader`),
  not sandboxed per-process. Constructing `DownloaderGUI()` from a throwaway
  Python shell/smoke-test - even read-only-looking code - can read *and
  write* the user's real settings (`download_base_dir`, `last_account_name`,
  `technical_view`, …) as a side effect of normal init code
  (`get_download_base_dir()` persists a default the first time it's called;
  `_set_active_account()` persists `last_account_name` on every confirm).
  When smoke-testing account/layout logic interactively, monkeypatch
  `AccountPaths.user_desktop_dir`/`internal_accounts_root` *and* override
  `self.get_download_base_dir` on the instance **before** triggering any
  account action, and expect to manually restore any settings value you
  touch afterward if you didn't intend to change it for real.
- App icon: `icon.ico`/`icon.png` live at repo root (used by `smd.spec` for
  the compiled EXE's icon, and `apply_window_icon()`'s ROOT-based fallback)
  *and* under `assets/` (used by the window/header/splash icon code paths,
  and bundled into the frozen build via `smd.spec`'s `datas`). Both copies
  must exist and stay in sync - several independent lookups check different
  paths for historical reasons; there is no single source of truth here.
  Missing either copy silently falls back to no icon (fixed 2026-07-17 - the
  files didn't exist at all before, so every lookup was silently failing;
  see DECISIONS.md).
- Map theme sync: `_apply_current_theme` → `refresh_map_for_theme()` rebuilds
  the open File Checker map (default or last pin set). Accepts pan/zoom
  reset so light mode lands on Terrain and dark on Dark Matter without a
  manual rescan. Skips while a check/render is busy.
