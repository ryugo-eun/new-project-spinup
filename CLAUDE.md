# CLAUDE.md — New Project Spinup

Local working folder for the **New Vertical Startup** effort. The live deliverables are Google Docs/Sheets in the Drive folder **New Project Spinup**: https://drive.google.com/drive/folders/1nHwjJu1P-Dtg8p-cZSLHx5Rn0mj4pkny

## What we're doing

Sparta is launching **new verticals** and we want a repeatable package to set each one up for success. Next up is **Accounting**, but the whole point is that this generalizes across verticals. Goal: a **menu** of things we could do for a new vertical, plus an opinionated **essentials package** (EPM structure, automations, integrations, onboarding email, instructions doc, Slack channels, Teams integration, tags), all derived from what already works in **Panacea** and **Vigil**.

Approach: scrape everything we've built across Panacea, Vigil, and SVA (automations sheets, comms engine, EPM/reviewer structure), reconcile the spec docs against the live messaging, then distill into the menu + essentials.

## Deliverables (in the Drive folder)

- **New Vertical Startup Playbook** (Doc) — https://docs.google.com/document/d/1B2m77LvX2sX2_PDF3oOoJ1JpquKw-WG8J80bvaFv5Is — Phase 1 (Essentials) + Phase 2 (Nice-to-haves). Structured as a doc with a companion sheet checklist.
- **Project Startup Essentials (New Vertical)** (Sheet) — https://docs.google.com/spreadsheets/d/1CZqjPsGV2WQoWCcKil89KbPJ2QDqj5V0uzNAFowq46Y — the essentials checklist companion to the Playbook.
- **Vertical Setup Menu + Automation Inventory (Sparta)** (Sheet) — https://docs.google.com/spreadsheets/d/1VotpDkOWk5s8aj9jkTTmXYKM_h0EmMdq5ZuA9JgJLAM — the full menu: automations catalog + messaging check, with SVA tab (incl. the bonus sheet being built in SVA) and the Studio Workspace Updates project. Cross-checked against the Vigil + Panacea automations sheets (both linked from it).
- **Accounting Instructions** (Doc) — https://docs.google.com/document/d/1AWfqU4mLja8s58xKAj_v12p_BWcf8gdS5SUmxIPOuFc — first concrete instance: the writer-facing instructions doc for the Accounting vertical, cloned from the Panacea Hub instructions template with consulting-specific content stripped out.

## Essentials package (from the session)

Phase-1 essentials to stand up a vertical, taken from Panacea:
- Onboarding email
- Instructions doc (clone Panacea Hub template, remove vertical-specific content)
- **Slack channels** — the canonical set is **nine**, and only six get created: the workspace ships `general`, `random` and `help-desk`, which are RENAMED to `<v>-announcements` (public, PLURAL), `<v>-epms` (private) and `<v>-technical-issues` (private). The six made by hand are `<v>-onboarding`, `<v>-pod-a`, `<v>-reviewers`, `<v>-maven-support` (public), `<v>-doctor-bot`, `<v>-world-file-upload-bot`. Skill: **`provision-vertical-slack-channels`**. Note there is **no channel-mutation API at all** (0 of mercor-mcp's 35 Slack tools, and the claude.ai connector likewise), so creating and renaming is manual in the UI forever; the skill supplies the spec, then verifies live and audits the Teams targets. Two traps it exists to catch: `slack_search_channels` defaults to public-only so it shows 2 of 9 unless you pass `channel_types="public_channel,private_channel"`, and **a rename leaves the Teams audience target's NAME stale while its `externalId` stays correct** — always resolve targets by channel id, never by name.
- Automations + Teams integrations
- **Studio AutoQC hooks** — part of the `clone-studio-world` skill (step 4; it absorbed `provision-autoqc-hooks` on 2026-07-29). Wires the canonical **22-hook Sparta-only** pipeline (Task AutoQC → Sparta runner → Taiga QA → FA → Pref Labels → delivery syncs) plus the qc_specs it fires onto the campaign's live tasking world(s). Without it, tasks strand in "Running Task AutoQC". Each new vertical supplies its own RLS key. **Never attach the 3 Prometheus hooks** — they made Abacus double-run.
- Tags — **prefix every team tag with the vertical name** (e.g. `Cadre Onboarding`, `Cadre Active Writer`, `Cadre Writer`). Sparta team tags are company-scoped and shared across all verticals; bare names like "Onboarding"/"Active Writer" already exist dozens of times, so an automation targeting a bare tag can act on the wrong project. Point the onboarding/active-writer grant automations at the vertical-prefixed tags. (`list_tags` caps at 200 rows for Sparta, so new tags aren't visible via the API — verify in the Teams UI.)
- **Auto-provision email** — enable it on the Teams project (`auto_provision_email_enabled`, via `set_project_autoprovision_email`). A fresh Teams project ships with it OFF; every live vertical (Panacea) has it ON. Without it, new members don't get an @mercor.expert address auto-provisioned.
- **Slack channel canvases** — each vertical's Slack channels get the standard channel-canvas set (the Abacus set of ~11, org chart + onboarding + ops canvases). Build via the `editing-channel-canvases` skill; they start standalone, then get shared into the channels. A plain channel creation does NOT add these.
- EPM + reviewer structure (Panacea's structure, names removed, EPM type only)
- **Studio Doctor bot + automation crons** — **ONE shared multi-tenant deploy, not one per vertical.** All five verticals run off `panacea-cli-slack.vercel.app`; adding a vertical is code (a campaign key + 4 cron endpoints) plus a Slack app plus two env vars, never a new Vercel project. Skill: **`add-vertical-bots`** (in this folder's `skills/`), which is the authority on the steps; repo `ryugo-eun/panacea-cli-slack`, and its own `CLAUDE.md` is canonical if the two ever drift. Crons ship OFF and are enabled per name via `/doc cron enable <exact-name>`. The sweep suite as of 2026-07-29 is **three** per vertical, plus an hourly digest (it was seven; four were retired). Taiga-verified, never trusting `taiga_qc_status`:
  - `unclaim-reviews` — release stale review claims (>5h). Only First Human Review and Final Review.
  - `advance` — the flow router: reads the run live off Taiga and takes ONE cautious action (advance / re-dispatch / re-fetch / pull QC), and dispatches the judge for any ungraded rollouts without waiting for scores.
  - `nudge-writer-to-hand-off` — DMs the WRITER when their own finished FA / preference-label work has sat unsent >3h and idle >2h. **Never advances a task**; the old auto-submit version shipped a mentee's unfinished work at 2:35am and was reverted 2026-07-17.
  - `digest` — one hourly ops-channel summary, scheduled last in the hour for its vertical.

  **Retired, do not re-add without reading why:** `qc-sweep` (7/13, fired a deleted remix), `resync` (7/28, a second brain over `advance` with a ~3-task lifetime yield), `heal-grade` (7/29, grading now rides the advance), and **`faga-sync` + `pref-sync` (7/29, they LOOPED)**. The last two guarded on a Studio-side `_sync` stamp that is also the runner's own dedupe, so when the stamp failed to land they re-fired and re-pushed: one task fired 82 times over 10 days. They were also redundant — the tasking world's four `Auto-sync on ready for delivery` hooks fire the same remixes, so nothing ships unsynced. Never guard a sync sweep on that stamp.

  Schedules follow a fixed convention: **sweeps at :00 / :15 / :30, digest at :50, plus 2 minutes per vertical in join order** (Panacea +0, Abacus +2, Atria +4, Rampart +6, Cadre +8; next takes +10). Enable by EXACT name, one per command — there is no wildcard.

  These directly address the recurring "Taiga QA/QC not syncing to RLS" incident EPMs hit (e.g. Vigil's "825 stuck," 2026-07-13). Per-vertical scoped — a bot instance only acts on its own campaign.

## Cloning a tasking world so it actually RUNS (learned on Abacus, 2026-07-21)

A plain Studio world clone copies the config bundle (flow, statuses, remix configs, eval_config defs, custom fields) but leaves the world **unrunnable**. Cloning 7 Abacus worlds surfaced the full set of things that do NOT clone and must be done per world before "Run External Agent" works. The Sparta runner preflights and rejects a world **one reason at a time**, so fix ALL of these up front or you fix one and immediately hit the next.

**One skill does the work: `clone-studio-world`** (hooks + qc_specs + env + verifier + default agent + base_world_id + scrub + file sync), in `~/.claude/skills/`. It absorbed `provision-autoqc-hooks` and `insert-autoqc-hooks` on 2026-07-29; hook mechanics live in its `references/autoqc-hooks.md`.

**Per cloned tasking world checklist:**
1. **Hooks + qc_specs** — the `/hooks` router chain does NOT clone, and does not inherit on a builder spawn either. Zero hooks → task strands in "Running Task AutoQC" and never reaches the runner. `clone-studio-world` step 4 (source from the campaign's own proven `[Live New Flow]` world; Sparta-only keeps 22 hooks, dropping the 3 Prometheus ones). qc_specs do not clone either — fork them per campaign and remap every hook id in payload AND predicate.
2. **World-level Sparta verifier** — does NOT clone. Create exactly one: `POST /verifiers/` `{world_id, task_id:null, eval_config_id:"5502d234-7a43-4ae8-a8b6-75ce19a82186" (sparta_agentic_grading), verifier_values:{}, verifier_index:0}`. Missing → runner error `Found 0 world-level verifier(s)`. (Note: `GET /verifiers/world/{id}` and the Snowflake mirror under-report — trust the POST 201 / runner DB check.)
3. **Default agent = `sparta_external_agent`** — a clone can carry a `loop_agent` (e.g. an APEX in-Studio agent) as its `default_agent_ids`. Runner error `no_sparta_external_agent`. Fix: `PATCH /worlds/{id}` `{"default_agent_ids":["<sparta_external_agent id>"]}` (copy the id from a known-good world in the same campaign).
4. **World file sync** — a clone inherits a STALE `world_custom_fields.prometheus_gcs_path` pointing at the SOURCE world's files, so the runner mounts an empty/wrong volume and the trajectory errors (`platform_has_environment=False`). Fire **Sync to External Storage** (`POST /world-remix/world/{id}/remix` with the sync remix config id, or the Studio UI, or `sync-to-external-storage`) so the path repoints to THIS world. Verify `prometheus_gcs_path` now contains this world_id + a fresh `prometheus_synced_at`.
5. **Taiga env** — `world_custom_fields.taiga_environment_id` must be the TARGET campaign's env, not the source's (clones can leak, e.g. Abacus once carried Vigil's env). Verify even when it looks right.
6. **base_world_id + cross-campaign scrub** — for the world-building spawn path, repoint the `sparta_create_tasking_world` remix's `base_world_id` to the target's own `[Live New Flow]`, and scrub any source campaign/env/world ids.
7. **Instructions-doc link** — the layout's `instructions_card` modules (in `module_layout` + `module_layout_draft`) carry the SOURCE's writer-instructions Google Doc, i.e. the OLD Vigil doc `1nvj9D-IW7dBQyn-lOaXTINZoxVEJJ1R4GwzNgMOUi7U`. Swap it to the vertical's own instructions doc in every tasking world + the Golden World Building world. Skill: **`replace-instructions-link`** (in `~/.claude/skills/`) — `scan <campaign> <old_doc_id>` to list worlds still carrying it, then `replace <world> <campaign> <old> <new>`. (Direct API needs a browser User-Agent to dodge Cloudflare 1010; PATCH replaces the whole world_settings, so the script GET-modifies-PATCHes the full object.) Done for Abacus/Atria/Rampart 2026-07-23.

**Observed preflight failure order:** verifier (0 found) → default agent (loop_agent) → file sync (empty volume). Plus zero hooks means the task never reaches the runner at all.

**The durable fix:** get the Studio team to fold hooks + verifier + sparta_external_agent default + env re-stamp + file sync into the world-clone itself, so future clones are runnable without this manual wiring.

## Conventions

- Doc styling matches the Mercor / Panacea Hub look: Inter font, bold purple headers (indigo `#4F46E5`), no colors in sheets, 10pt body / 12pt headers.
- Sheets: the Panacea automations spec sheet has checkbox padding down to ~row 1000 — `appendRow` drops rows below it. Find the real last row before writing.
- **The Google Docs API cannot tick a checklist checkbox.** Verified against the live v1 discovery doc 2026-07-28: `Bullet` exposes only `listId`, `nestingLevel`, `textStyle`, and no schema anywhere carries a checked/checkbox-state property. `BULLET_CHECKBOX` exists solely as a `createParagraphBullets` preset for MAKING a checklist. So the Playbook doc's boxes can only be ticked by hand in the UI; the API-writable checkoff surface is the Essentials sheet's `Done` column. Corollary: do NOT re-run `createParagraphBullets` over an existing checklist "to make it tickable" — it is already tickable, the API just can't show you the state, and re-applying the preset risks clearing ticks you cannot see.

## Notes

- This local folder is a companion/scratch space; the source of truth is the Drive folder above.
- Reconstructed from session `7bc8587b-6f82-4eff-8591-860fdfdcf9a9` (2026-07-09/10).
