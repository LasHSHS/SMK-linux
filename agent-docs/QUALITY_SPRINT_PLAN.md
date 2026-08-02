# SMK quality sprint plan (locked 2026-07-19)

**Status:** Decided. Do not reopen the debates listed under “Out of scope this sprint” until items 1–2 are done.

**Related:** [QUALITY_ASSESSMENT.md](QUALITY_ASSESSMENT.md) — full Cursor Pro + Perplexity assessment for the boss to review/correct.

**Rule for agents:** Implement changes only from this plan (or boss corrections to it). Do not expand into CDN support, wizards, rebrand, signing-first, or Palestine relocation unless the boss explicitly changes the locked decisions below.

---

## Product stance (locked)

| # | Decision |
|---|----------|
| 1 | **Trust → Outcome → Reach** (priority order this quarter) |
| 2 | **Primary audience: you + aligned users** — not generic YouTube/GitHub strangers |
| 3 | **Duplicates: safe-trash/quarantine as default; permanent delete = advanced/explicit** |
| 4 | **Link-only exports: educate toward bundled re-export + calm note that CDN tools exist; no CDN in core** |
| 5 | **Palestine: keep visible in-app this sprint; no relocation to About/docs** |
| 6 | **Pride metric:** scariest destructive edge case fixed + export story clear + one aligned friend can finish a run alone |

**One-line identity:** SMK is a **safety-first niche archive tool** for people who accept its boundaries (offline, ZIP-only, bundled media, values visible) — not a mass-market JSON/HTML + CDN downloader.

---

## Sprint execution order

Do in this sequence. Stop after #3 if time is short; #4 is optional.

### 1. Duplicate flow (Trust — start here)

- Default action: move duplicate candidates to a recoverable safe-trash / quarantine folder (not `unlink` / permanent delete).
- Permanent delete: keep for power users, behind explicit advanced UI + blunt danger wording.
- Copy must not sound like harmless “review”; state that the default is move-aside, not destroy.
- Align docs / privacy-safety language with this default.

### 2. Export-type conversation (Trust + Outcome)

- When detection is link-only / JSON-only / hybrid: diagnose clearly (links vs bundled media).
- Guide path: how to request a Memories export that includes media in the ZIP (official Snapchat My Data flow).
- Calm note: other third-party tools download from CDN links and need network access; SMK deliberately does not.
- Tone: conversation / care, not “unsupported / app broken.”
- **Do not** add CDN download to the pipeline.

### 3. Lightweight Outcome clarity

- After a successful run: explicit “your finished library is here” (path).
- Clearer done-state language (what staging is, what duplicates did if relevant).
- Optional: warn before Start when active account’s stored `mydata_id`(s) disagree with the current export’s `mydata_id`(s).

### 4. First-run friction (only if needed)

- Progressive disclosure on Save memories (core path visible; advanced behind a fold).
- Only after real aligned users still get lost — not as a wizard rewrite.

---

## Out of scope this sprint (do not reopen)

- CDN / link download in core
- Full first-run wizard
- Moving Palestine tab / heavy content to About or external-only
- Code signing as the first milestone
- Rebrand / SEO rename of the product
- Cross-platform ports
- Targeting “random exporters” / mass-market Reach as the success metric

---

## Success check (end of sprint)

Boss can honestly say:

> I fixed the one destructive inconsistency (duplicates), made the export conversation honest and clear, and I can tell one aligned friend: download a bundled Memories ZIP, run SMK, and you’ll get a safe, usable library without me sitting next to you.

---

## Notes for implementers

- Prefer small, targeted GUI + docs changes; no pipeline rewrite.
- Verify current duplicate-delete paths in `gui/dialogs.py`, Save memories / completion mixins, and any duplicate report helpers before changing defaults.
- Export classification already lives in `smd/export_detect.py` (`ExportFormat`, `LINKS_ONLY`, etc.) — improve UX messaging, don’t reinvent detection.
- After behavioral changes: update [ARCHITECTURE.md](ARCHITECTURE.md) and add a dated “why” to [DECISIONS.md](DECISIONS.md) if the trade-off is non-obvious.
