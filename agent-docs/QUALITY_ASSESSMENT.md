# SMK quality assessment — Cursor Pro & Perplexity (2026-07-19)

**Purpose:** Log what we assessed so the boss can read, correct, and override.  
**Actionable plan:** [QUALITY_SPRINT_PLAN.md](QUALITY_SPRINT_PLAN.md) (locked decisions + sprint order).  
**How to use this file:** Mark anything wrong with `[BOSS CORRECT]` notes, or edit directly. Agents should prefer the plan file for execution; this file is the reasoning trail.

**Authors of this assessment:** Cursor Pro (in-repo / product stance) and Perplexity (ecosystem / stranger lens), converging in chat. Not a third-party audit of the codebase line-by-line.

---

## 1. What we think SMK is

SMK solves a real problem: Snapchat’s “Download My Data” path is often browser-centric (ZIP → open `index.html` → click through). SMK’s job, as we understand it:

- Take an official **Memories-bundled** export ZIP.
- Process **entirely offline** (no login, no CDN download, no telemetry in the core pipeline).
- Produce a proper local photo/video library: **overlay merge**, capture time / GPS where available, careful matching, staging verify, resume, quarantine.

**Boss — correct us if:** the product is meant to grow into link/CDN download, or if “bundled only” is temporary rather than a hard line.

---

## 2. Goals we attributed to you

| Goal | Our read |
|------|----------|
| Safety and trust | People don’t lose irreplaceable media; offline/privacy story is solid |
| Usability for one-time archivists | Aligned users should finish without a whitepaper; not mass-market funnels |
| Boundaries | No login, no CDN, ZIP-only by design |
| Solo maintainability | Targeted changes, no giant rewrites |

**Boss — correct us if:** Reach / strangers / signed distribution / cross-platform are higher priority than we assumed.

---

## 3. Where we think SMK is ahead

Relative to many niche tools (JSON/HTML + CDN downloaders, EXIF fixers, simple GUIs):

- Overlay merge (`-main` / `-overlay` → single media).
- Staging verification before suggesting delete of extract leftovers.
- Atomic writes, quarantine for suspect files, checkpoint/resume.
- Explicit export-format detection (bundled vs links-only vs JSON-only) instead of failing mid-run.
- Duplicate *detection* beyond naive “same filename” (byte + visual/deep scan in the pipeline).

**Boss — correct us if:** any of these are weaker in practice than we claim, or if competitors already match overlay + staging culture in ways we underweighted.

---

## 4. Where we think SMK is behind (product, not pipeline)

| Gap | Assessment |
|-----|------------|
| First-run cognitive load | Multiple tabs, account vs export, presets, File Checker, After processing — careful engine, busy surface |
| Export-type UX | Detection exists; messaging can still feel like “broken” for link-only ZIPs people got from tutorials |
| Destructive duplicate default | Pipeline is paranoid; “Review duplicates” → hard delete is the philosophical outlier |
| Packaging for strangers | Windows-only, unsigned EXE (SmartScreen) — only matters if Reach is a goal |
| Competitive positioning copy | Subtitle/README could say “offline export converter, not a CDN client” more loudly |

**Boss — correct us if:** cold users already find Save memories clear, or if duplicate delete is rarely used / already feels safe enough to you.

---

## 5. Competition (our framing — open to correction)

We argued the bar moved up: polished GUIs/CLIs now do download + metadata + resume narratives across platforms. That does **not** erase SMK’s moat (overlay + offline + staging culture), but it does mean:

- “We’re the only serious tool” is outdated.
- Differentiation must be stated as **overlay + safety + ZIP-only**, not “scripts with GUIs glued on.”

Examples discussed in chat (illustrative, not a full market study): ToTheMax-style memories downloaders, ethanwheatthin GUI, various `memories_history.json` / HTML CDN tools, EXIF-focused CLIs.

**Boss — correct us if:** you’ve already evaluated specific competitors and we mischaracterized what they do or don’t do (especially overlays / staging / offline).

---

## 6. Tensions we named

### 6.1 Duplicates vs safety culture

**Claim:** Staging delete is gated; quarantine exists; merged isn’t auto-wiped — but duplicate review can permanently delete library media. Users skim; “review” sounds harmless; mistakes are irreversible.

**Recommendation we locked:** safe-trash/quarantine **default**; permanent delete **advanced**.

**Boss — correct us if:** you rely on permanent delete every run and refuse a move-aside default, or if duplicates never touch `merged/` / user-facing library paths in ways we assumed.

### 6.2 Link-only / hybrid exports

**Claim:** Philosophical ZIP-only boundary is correct; treating it only as “internal invariant” underweights UX and support burden. Tutorials push JSON/HTML + CDN; users bring that ZIP and feel betrayed.

**Recommendation we locked:** diagnose → Guide to bundled re-export → calm “other tools use the network” note. **No CDN in core.**

**Boss — correct us if:** you’d rather hard-refuse with no mention of other tools, or you’d rather add CDN after all.

### 6.3 First-run / golden path

**Claim:** Guide + Export + Account + Start is a golden path *for people who already know the app*; cold users see options, not rigor. Full wizard is expensive and was rejected as urgent; progressive disclosure later is enough.

**Boss — correct us if:** first-run confusion is already your top pain (friends bounce) and should outrank or equal duplicates this sprint.

### 6.4 Palestine / identity

**Early Perplexity lean:** move heavy content to About/docs; lighter chrome — for trust/contributors/Reach.

**Cursor Pro pushback:** if audience is aligned and Reach is last, relocating politics this sprint is premature Reach optimization; keep visible; optional one-line “non-technical; memories never leave this PC.”

**Locked:** keep Palestine visible in-app; **no relocation this sprint**. Revisit only if you later choose Reach.

**Boss — correct us if:** you want quieter chrome now anyway, or the tab placement/order should change for your own reasons (not adoption).

### 6.5 Packaging / signing

**Claim:** Signing matters for strangers + SmartScreen; secondary if distribution stays friends/aligned. Not the pride metric this sprint.

**Boss — correct us if:** you plan public EXE distribution soon and signing should jump the queue.

---

## 7. Quality layers (shared vocabulary)

| Layer | Meaning | Our score for SMK today |
|-------|---------|-------------------------|
| **Trust** | Risk of loss / fear; offline honesty | Strong overall; **weak at hard-delete in duplicate review** |
| **Outcome** | One run → usable library | Strong for bundled; muddy for wrong export type / “where’s my folder?” |
| **Reach** | Cold stranger finishes alone | Weaker; consciously deprioritized |

**Boss — correct us if:** you’d score any layer differently, or you want Reach raised this quarter after all.

---

## 8. What we may have under- or over-estimated

| Topic | Cursor Pro / Perplexity read | Risk of being wrong |
|-------|------------------------------|---------------------|
| Duplicate hard-delete severity | Highest regret risk in the product | Overstated if UI already moves files / rarely deletes, or if you never ship duplicate delete to others |
| First-run load | Real but not #1 this sprint | Understated if friends already bounce hard |
| Competition polish | Stronger than “toy scripts” | Overstated vs your overlay+safety bundle |
| Contributor filter from Palestine tab | Real for *some* people; not this sprint’s problem if niche | Overstated if you don’t want contributors |
| Maintenance of UI surface | Mild underestimation by boss | Soft claim — correct if you disagree |

---

## 9. Disagreements that got resolved

| Topic | Earlier tension | Resolution |
|-------|-----------------|------------|
| Palestine relocation | Perplexity: lighter chrome soon; Cursor: don’t dilute if Reach is last | **Keep visible this sprint** |
| Wizard | Perplexity-style “Archive my memories” flow vs Cursor “expensive” | **No wizard this sprint**; optional progressive disclosure as item 4 |
| Duplicate vs first-run priority | Both matter | **Duplicates first** (alignment with safety philosophy); first-run later |
| Mentioning CDN tools | Ignore vs endorse | **Calm acknowledgment, no endorsement, no feature** |

---

## 10. Explicit non-goals (this sprint)

Do not treat these as open design debates until sprint items 1–2 are done:

- CDN in core  
- Full wizard  
- Palestine move to About-only  
- Signing-first  
- Rebrand  
- Cross-platform  
- “Compete with every GitHub memories downloader on simplicity”

---

## 11. Boss correction checklist

Edit this section (or add notes inline above). Agents should update [QUALITY_SPRINT_PLAN.md](QUALITY_SPRINT_PLAN.md) if you change a locked decision.

- [ ] Priority order Trust → Outcome → Reach is correct / should be: ________  
- [ ] Audience “you + aligned” is correct / should be: ________  
- [ ] Safe-trash default for duplicates: agree / disagree because: ________  
- [ ] Educate + CDN note (no CDN core): agree / disagree because: ________  
- [ ] Palestine stays visible this sprint: agree / disagree because: ________  
- [ ] Pride metric (scary edge case + export story + one friend): agree / should be: ________  
- [ ] Sprint order (duplicates → export UX → outcome clarity → simplify): agree / reorder to: ________  
- [ ] Other corrections / facts we got wrong: ________  

---

## 12. Joint closing judgment (for you to accept or reject)

> SMK’s pipeline is ahead of the niche; stranger-facing product is behind if measured as a mass-market downloader. The main integrity hole is destructive duplicate cleanup vs the rest of the safety culture. The main communication hole is wrong-export-type dead ends. Fix those before chasing Reach, signing, or politics relocation. Own the niche: offline bundled archive tool with overlays and paranoia — not another CDN client.

**If this paragraph is wrong, rewrite it here as the boss’s version.**
