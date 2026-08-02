# Notes for premium agents / premium models

**Purpose:** Backlog of UX, layout, and duplicate-review issues captured from user testing (2026-07-19). Read this before picking up Save Memories tab or Review duplicates work.

**Last updated:** 2026-07-19 — Account + Export **rename/copy pass done** (see § Done below). **§9 brainstorm added** (Account + ZIP picker merge — ideas only, not approved). Other items still open unless marked done here.

---

## Done (2026-07-19) — Account + Export renames

Implemented in `gui/tabs/save_memories_tab.py`:

### Account — Existing account row

| Element | Was | Now |
|---------|-----|-----|
| Radio label | Old account | **Existing account** |
| Status text | `Is Las your folder?` | **`Your output folder is Las-memories`** (uses `ensure_memories_suffix` on candidate for display) |
| Primary action | Yes, confirm output folder (button) | **Removed** — folder activates automatically when Existing account is selected or when user picks another folder |
| Secondary action | No, change output folder | **Change output folder** |
| Control type | QRadioButton pair (circle / filled ring) | **QCheckBox** with same gold-border checkmark style as Run options; still exclusive via `QButtonGroup` |

**Behavior:** `_activate_existing_account_candidate()` runs silently when toggling to Existing account or after Change output folder. New account still uses **Create**.

### Export — Snapchat My Data zip files section

| Element | Was | Now |
|---------|-----|-----|
| Section title | Export | **Snapchat My Data zip files** |
| Button | Choose mydata ZIP files folder | **Choose folder** |
| Hint placement | Below button | **Above button** |
| Hint text | Generic “put mydata ZIPs in one folder” | Points user to **Guide tab** for My Data download; choose folder with all ZIP parts |
| Summary placeholder | “Select the folder containing your mydata ZIP…” | **“After you choose a folder, a summary of the ZIP parts SMK found appears here.”** |
| Folder picker dialog title | (mydata wording) | **“Select the folder with your Snapchat My Data ZIP file(s)”** |

### Still deferred from this pass

- **Lever toggle** (New account ↔ Existing account) — skipped; user later chose **checkmarks like Run** instead (done 2026-07-29).

---

## Priority summary (remaining work)

| Area | Severity | Status |
|------|----------|--------|
| Run box enabled during processing | Bug | **Done** (options locked; Cancel stays clickable) |
| Review duplicates: second popup + empty previews | Bug | **Open** (button demoted to Technical → Check leftovers) |
| Deep scan vs Review duplicates split | UX bug | **Open** |
| Duplicate review empty pairs (Mary) | Bug | **Open** |
| Account mode control (radios → Run-style checkmarks) | UX | **Done** (2026-07-29) |
| Export section copy + layout | UX | **Done** (renames above) |
| Existing account: statement + Change only | UX | **Done** |
| Performance / After processing layout | UX | **Open** |
| Font sizes inconsistent | Polish | **Open** |
| Account + ZIP export picker merge | UX brainstorm | **Ideas only — §9** |

---

## 1. Run box — lock options while processing

**Done (2026-07-31):** `_set_run_lockout()` disables `_run_options_host` (Also save without filters / Technical view) while a run is active. Start/Cancel stays enabled.

**Note (2026-07-30):** "Keep staging media files" was removed; staging always verifies then auto-deletes when safe.

---

## 2. Account section — mode control

**Done:** Existing account label, status text, single Change button, auto-activate (see **Done** section above).

**Done (2026-07-29):** New account / Existing account use `QCheckBox` with the same gold-border white-checkmark style as Run (`Also save without filters`, etc.). Selection stays exclusive via `QButtonGroup.setExclusive(True)`. Lever/switch idea abandoned in favor of matching Run checkmarks.

**Related code:** `save_memories_tab.py` Account section, `_on_account_mode_toggled`.

---

## 3. Export section — rename and copy

**Done** — see **Done (2026-07-19)** section above.

---

## 4. Layout — section order

**Requested order (Save Memories tab, process controls):**

1. Account  
2. Snapchat My Data zip files  
3. Run  
4. **Performance** — move **between Run and After processing** (today Performance may be hidden unless Technical view; user wants it in this slot when visible)  
5. Progress (live run / status)  
6. **After processing** — move **under Progress** (not above it)

**Related code:** `_rebuild_process_controls_grid()`, section stacking in `save_memories_tab.py`.

---

## 5. Review duplicates — one flow, not two pop-ups

**Observed:** After a run, duplicate review feels like **two separate windows**:

1. Byte-identical (or first pass) Review duplicates dialog  
2. **Separate** deep-scan / visual duplicate dialog  

**Expected:** **One** Review duplicates entry point and **one** dialog sequence (or one scrollable dialog with sections), not a second modal that feels like “Review duplicates again.”

**Related code:** `gui/tabs/completion.py`, `gui/dialogs.py` — `DuplicateReviewDialog`.

---

## 6. Review duplicates — empty / no-preview entries (Mary account)

**Observed:** Some groups show **one thumbnail and one card with “no preview” / no size**.

**Examples (Mary account):**

| File A | File B | Issue |
|--------|--------|--------|
| `2026-07-09_12-58-12.jpg` | `2026-06-22_23-42-53.jpg` | Pairing seems wrong; one side empty |
| `2025-08-20_00-34-58.jpg` | `2022-08-20_15-00-37.jpg` | First has **no size / no preview**; second has data |

**Expected:** Only show pairs where every member exists, has non-zero size, and can preview. Log skipped entries separately.

**Related code:** `smd/duplicates.py`, `gui/dialogs.py`, `gui/tabs/completion.py`.

---

## 7. Typography — button and caption sizes

**Observed:** Font sizes **inconsistent** across buttons and captions between tabs.

**Expected:** One coherent scale in `smd/theme.py` across all tabs.

---

## 8. Collision / deep-scan product notes

- Same-timestamp collision pairs can be **same moment, different resolution** — native visual hash will **not** match.  
- Future: tiered collision review + scoped perceptual compare within `filename_collisions.json` groups only (not approved).

---

## 9. Brainstorm — merge “Snapchat My Data zip files” into Account? (ideas only)

**Status:** User reflection captured 2026-07-19. **Not approved for implementation.** Treat everything below as design exploration for a future session — agents should not build this unless the user explicitly picks a direction.

### The underlying feeling

Today the Save Memories tab splits two things the user mentally treats as **one job**:

1. **Which account am I working on?** (output folder / library)  
2. **Where are my export ZIPs?** (input folder from My Data)

The **Account** box answers (1). The separate **Snapchat My Data zip files** section answers (2). The user wonders whether (2) belongs **inside or beside** the Account box — especially for **Existing account**, where the output folder is often already known and the real next step is “point SMK at the new export ZIPs again.”

---

### What the user said (rephrased clearly)

**New account flow (feels obvious):**

- User names the folder (Create).  
- User chooses the folder that contains all My Data ZIP parts.  
- Then Run.

Both steps are required and order makes sense: *create destination, then pick source.*

**Existing account flow (feels awkward today):**

- Output folder is already shown: *“Your output folder is Las-memories.”*  
- User may only want to **add another export** or **re-run** with ZIPs sitting in Downloads (or wherever).  
- A separate section below for “choose ZIP folder” feels disconnected — like Account is “done” but Export is still a whole other box for something that belongs to the same account.

**Placement ideas (user was unsure):**

- Put **Choose folder** (ZIPs) **next to** **Change output folder** on the Existing account row.  
- Or **above / below** that row inside the Account section.  
- Maybe remove the standalone Export section entirely if Account can hold both concerns.

---

### Idea A — Two buttons in Account (user leaned toward this)

Keep **two distinct actions**, not one smart button:

| Mode | Button 1 | Button 2 |
|------|----------|----------|
| **New account** | Name + **Create** (output) | **Choose folder** (ZIP input) |
| **Existing account** | **Change output folder** | **Choose folder** (ZIP input) |

**Why two buttons might be right:** “Output folder” and “ZIP folder” are different paths on disk. One button that tries to guess (“if I see ZIPs, treat this as export; if not, treat as output”) gets messy fast — user explicitly rejected a single ambiguous picker.

**Copy challenge:** Labels must be unambiguous, e.g. **Change output folder** vs **Choose export folder** (or **Choose ZIP folder**) — not two vague “Choose folder” buttons.

---

### Idea B — One section, mode-dependent layout

Collapse Export **into** Account visually:

- **New account:** name field → Create → then ZIP hint + Choose folder (stacked).  
- **Existing account:** “Your output folder is …” + Change output folder → ZIP hint + Choose folder below.

The standalone **Snapchat My Data zip files** section disappears; Guide-tab hint moves with the ZIP button.

**Pros:** One mental “setup account” card. **Cons:** Account box gets tall; Technical view users still need Performance elsewhere.

---

### Idea C — Auto-detect ZIPs and “just apply them” (user doubted this)

Rough idea: user picks **some** folder; if SMK detects `mydata~*.zip` (or bundled export signatures), auto-bind that as the export selection without a second step.

**Why it’s tempting:** Fewer clicks for Existing account re-runs.  
**Why it’s risky:**

- User picks output folder by mistake → SMK might find old staging/ZIPs in `technical/` and do the wrong thing.  
- User keeps ZIPs on Desktop and library under `Memories/` — same picker can’t mean both without disambiguation.  
- “Detect ZIPs → apply” hides what SMK is using; conflicts with simple UX (“show me what’s selected”).

**Verdict in brainstorm:** Maybe useful as **assistant** behavior (pre-fill export path when ZIPs are obvious), not as a replacement for an explicit **Choose export folder** action.

---

### Idea D — Move/copy ZIP files into `technical/` when Existing account is selected (user rejected for now)

Thought: when user continues Las, physically **move** My Data ZIPs into that account’s `technical/` folder so everything for Las lives in one tree.

**Why it might seem logical:** One folder per account; exports become part of the project.

**Why it’s probably wrong (user’s own “maybe not”):**

- ZIPs are often huge; duplicating or moving from Downloads may surprise users (“where did my export go?”).  
- Same export might be reused for multiple accounts (edge case).  
- Deletes/moves are **data safety** — out of scope for a casual picker UX.  
- SMK already extracts to `technical/staging/`; raw ZIPs don’t need to live inside the account folder for processing to work.

**Verdict in brainstorm:** Prefer **remembering the last ZIP folder path per account** (bookkeeping only) over **moving files on disk**.

---

### Idea E — Existing account: ZIP picker as the *primary* action

Reframe Existing account as:

> “I’m continuing **Las-memories** — here are the ZIPs for this run.”

Output folder becomes **read-only context** (Change only if wrong). The **main** button is **Choose export folder** (ZIPs), placed prominently because that’s what changes every run.

**Pros:** Matches repeat-user workflow. **Cons:** New users might not understand output vs export without copy.

---

### Tensions to resolve before any implementation

1. **Clarity vs compactness** — One Account card vs two labeled sections.  
2. **Two pickers, zero ambiguity** — Output path vs export path must never share one unlabeled button.  
3. **Re-run memory** — Existing account already stores `mydata~ID` → folder mapping; ZIP folder path could be stored similarly (no personal data).  
4. **Empty states** — New account with name but no ZIPs yet; Existing account with ZIPs chosen but wrong account active.  
5. **Layout knock-on** — If Export merges into Account, section order (§4) simplifies: Account (incl. ZIPs) → Run → Performance → Progress → After processing.

---

### Open questions for the user (next conversation)

- Should **Choose export folder** appear for **both** New and Existing, always in the same place?  
- For Existing account, is **Change output folder** rare enough to tuck behind a link/smaller button?  
- Should the ZIP summary banner (parts count, bundled/not) live **inside Account** once merged?  
- Any desire to **hide** output folder entirely for Existing account when `mydata~ID` already maps export → account?

---

### Agent guidance

- **Do not implement** any of §9 without explicit user approval of a single direction (A/B/E or hybrid).  
- If prototyping, prefer **layout/mockup** or a short comment in this file over code changes.  
- When discussing with the user, use the terms **output folder** (library) vs **export folder** (ZIP input) — never two generic “Choose folder” labels.

---

1. Run lockout — disable Run-section checkboxes during processing.  
2. Review duplicates — filter non-previewable files; unify byte + visual into one UX.  
3. Layout reorder + typography polish.

---

## Files likely touched (remaining)

| File | Topics |
|------|--------|
| `gui/tabs/save_memories_tab.py` | Run lockout, layout grid, lever toggle |
| `gui/tabs/completion.py` | Unified duplicate review flow |
| `gui/dialogs.py` | DuplicateReviewDialog filtering, previews |
| `smd/duplicates.py` | Report generation, eligibility filters |
| `smd/theme.py` | Font size consistency |
