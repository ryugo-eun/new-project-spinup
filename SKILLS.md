# Sparta skills inventory

Internal. What we have built, what each one is for, and which parts of the spinup
still have no skill. The goal is a skill for every step that **should** have one, so
the gap list at the bottom is the real backlog. One step is deliberately excluded:
the writer instructions doc (8a), which is domain writing, not automation.

Last audited 2026-07-29.

**16 spinup skills, 12 ops skills.** Install location is
`~/.claude/skills/<name>/SKILL.md`; a skill only becomes slash-invocable once it is
there, and authoring it anywhere else does nothing. `~/.claude` is **not** a git
repo, so every spinup skill is mirrored into `new-project-spinup/skills/`.
Installed is authoritative; the mirror is the backup.

**CORRECTION 2026-07-29: the mirror does NOT reach GitHub.** This file previously
claimed it did. `~/Desktop/MERCOR/new-project-spinup` is not a git repo and neither
is any parent directory (`git rev-parse --show-toplevel` fails). So the mirror is a
second copy on the same disk, not an offsite backup, and a disk loss takes both
copies of all 16 spinup skills. Fix by `git init` + a remote, or by moving the
skills into an existing pushed repo.

---

The operator-facing version of the run order below is the Google Doc **New Vertical Spinup
Runbook** in the master Drive folder:
https://docs.google.com/document/d/1RKyWoKfweCVQLZEzZONMhZQGAzrow0bOUc911uu92o0/edit
Local source: `SPINUP-RUNBOOK.md`. Keep the three in step when the order changes.

**The Doc numbers the steps 1 to 15**; the table below keeps the dependency numbering (0, 0a,
1b and so on). Same order, different labels. Map: Doc 1-2 = project + listing, 3 = Slack
workspace, 4-5 = Studio, 6 = channels, 7 = Drive tree, 8 = integrations, 9 = Drive share +
calendars, 10 = automations, 11 = bots, 12 = instructions doc, 13 = canvases, 14 = the link pass,
15 = audit.

**Steps 13 and 14 swapped on 2026-07-29.** The Doc used to run the link swap at 13 and canvases at
14. That could not work: `replace-instructions-link` surface 4 rewrites the canvases, so it has to
run after they exist. Canvases are now 13 and the single link pass is 14, the last build step before
the audit. **The Google Doc still shows the old order and needs this one edit by hand.**

**How the Doc is produced:** write `SPINUP-RUNBOOK.md`, upload it with `upload_get_url` plus a
`curl` PUT, `upload_send_to_drive`, then `drive.files.copy` with
`mimeType: application/vnd.google-apps.document` to convert markdown into a real Doc. That is
what gives native headings, numbered lists, bullets and bold. Hand-building the same doc through
`insertText` plus index math produced a wall of text and had to be redone. Only the Mercor look
(Inter 12pt body on slate-900, headings bold indigo-600 at 26/20/16) is applied afterwards.

## The run order (dependency-driven, 2026-07-29)

Run in this order. The ordering is not preference, it is what each step needs to already
exist. **One step is permanently manual: the writer instructions doc at 8a.** A skill was written for
it on 2026-07-29 and deleted the same day. Once the link fan-out moved into the step-10 link pass,
all that remained was recasting the doc for the new domain, and that is domain judgment (what an HR
data room and a realistic HR task actually look like), not something to automate. Its gotchas live in
`SPINUP-RUNBOOK.md` step 12.

| # | Do | Skill | Needs to already exist |
|---|---|---|---|
| 0 | Teams project + roles | `create-vertical-teams-project` | nothing. Everything below needs the `proj_` id, and its last 4 chars name every Google group later |
| 0a | the listing, one per expert role | `create-vertical-listing` | the project. **Runs BEFORE the role**: the platform chain is listing to role to milestone, and `create_listing` publishes immediately |
| 0b | Slack workspace | manual / IT | the workspace itself is requested, not scripted |
| 1 | Studio campaign | `clone-sparta-campaign` (adopt mode, after the human clones `[CLONE ME]` in the UI) | Teams project, for the Studio-to-Teams link |
| 1b | extra worlds, or hook gaps | `clone-studio-world` (hooks included) | the campaign. Skip if step 1 already wired qc_specs + the 22 hooks |
| 2 | the 9 Slack channels | `provision-vertical-slack-channels` | the workspace. **Before** audiences, canvases and bots, all of which key off channel ids |
| 3 | Drive tree + the 2 forms (steps 1-7) | `new-vertical-drive-folder` | vertical + domain name only, so it can run early |
| 5 | tags, audiences, targets | `provision-vertical-teams-integrations` | project, channels, campaign, Insightful projects. **Creates the `<v>-core-team` Google group** |
| 6 | share the Drive tree (step 8) | `new-vertical-drive-folder` | the groups from step 5. Cannot run earlier, which is exactly why it gets skipped |
| 6b | the 2 calendars | `add-vertical-calendars` | the groups from step 5 |
| 7 | the 7 launch automations | `provision-vertical-automations` | prefixed tag ids from step 5, plus confirmed comp numbers |
| 8 | Doctor + upload bots | `add-vertical-bots` | campaign, plus `#<v>-doctor-bot` and `#<v>-world-file-upload-bot` from step 2 |
| 8a | **writer instructions doc** | **MANUAL by design** | the Drive tree. Deliberately LATE: the doc waits on the domain spec, so nothing above waits on it. The recast is domain judgment; the link fan-out that follows it is step 10's job, not this step's. Gotchas in `SPINUP-RUNBOOK.md` step 12 |
| 9 | create the canvas set | `create-vertical-canvases` | channels from step 2. Can run as soon as channels exist; it leaves every unknown link as an explicit TBD |
| 10 | **the single link pass, all six surfaces** | `replace-instructions-link` | the doc from 8a, the worlds from step 1, the calendars from 6b, and **the canvases from step 9**. Its surface 4 delegates to `sweep-canvas-links`, so do NOT run that separately |
| 11 | audit | `verify-vertical-spinup` | everything. Run before launch, not after |

**The instructions doc arrives late, and exactly one step waits on it: the link pass at 10.** Build
the canvas set whenever the channels exist; `create-vertical-canvases` leaves every unknown link as
an explicit TBD, and the link pass fills them along with every other surface. What the lateness does
NOT permit: letting writers start tasking first. Until step 10 runs, every cloned world still links
the OLD Vigil instructions doc, so writers silently read another vertical's instructions. **The doc
plus step 10 are a launch gate, not a setup gate.**

**`sweep-canvas-links` is no longer a step of its own.** It is surface 4 of the link pass, which
calls it. Running it separately at canvas-creation time is wasted, because the instructions doc does
not exist yet, and it is the reason the old order had the link swap before the canvases it rewrites.
One pass, after everything it consumes exists.

`clone-vertical-automations` is not in the order: it is superseded by
`provision-vertical-automations` for new verticals and kept only for one-off copies.

## Spinup skills (standing up a new vertical)

Ordered by the New Vertical Startup Playbook step they serve.

| Step | Skill | Purpose | Backup |
|---|---|---|---|
| 0 | `create-vertical-teams-project` | **BUILT 2026-07-29.** The Teams project everything else hangs off: project (`humandata` + `rl_studio`), one Writer role per expert profile plus the EPM role, auto-provision email ON, owners, milestone, test contract. Inventories before creating so it cannot split a roster, pins Sparta, carries the 6 canonical `function_id`s, and hard-blocks a role whose payable rate exceeds its billable. Records that the project id's last 4 chars name every Google group downstream. | mirrored here |
| 0a | `create-vertical-listing` | **BUILT 2026-07-29.** One listing per expert role, run before `create_role`. Pins `commitment=hourly` (the API defaults to full-time), reconciles the pay band against the role's payable rate, forces `validate_listing_description` to pass, and leads with the trap that `create_listing` publishes instantly with no draft state. Documents the private sourcing-funnel twin and what about it is unverified. | mirrored here |
| 1 | `clone-sparta-campaign` | **Adopt mode since 2026-07-29.** The human clones `[CLONE ME]` in the Studio UI, then this wires every gap: renames the `- copy` worlds to canonical, re-stamps the Taiga env (keeping the campaign's own env unless told otherwise), strips stale file pointers, repoints `base_world_id` and the consensus target (which `[CLONE ME]` aims at **Vigil**), verifier, `sparta_external_agent`, SER-Heal, tasking AutoQC (qc_specs + 22 hooks), builder 4-hook set, campaign-level configs. Inventories first, never creates worlds, so it cannot duplicate. Old create-and-clone path behind `--mode create`. | mirrored here |
| 1 | `clone-studio-world` | **Absorbed `provision-autoqc-hooks` and `insert-autoqc-hooks` 2026-07-29 (both deleted).** Clone one world (or a campaign subset) and make it actually RUNNABLE, in one skill: the canonical hook chain + qc_specs, re-stamp Taiga env, create the world-level Sparta verifier, repoint the default agent to `sparta_external_agent`, repoint `base_world_id`, scrub cross-campaign refs, re-sync the file bundle. Also the skill for a hook gap on a world that was spawned rather than cloned. Carries the HARD RULE: **22 hooks, never attach the 3 Prometheus ones** (they made Abacus double-run, and `canonical_hooks.json` still contains them), and the #1 gotcha: remap the hook PREDICATE, not just the payload. Hook mechanics in `references/autoqc-hooks.md`. | mirrored here, scripts included (not `spinup.env`) |
| 2 | `new-vertical-drive-folder` | Clone the `_CLONEME (New Vertical Template)` Drive tree and rename it for the vertical. Also produces the two expert-facing forms. | mirrored here |
| 2 | `replace-instructions-link` | Swap the writer-instructions Google Doc baked into world layouts. Cloned worlds inherit the OLD Vigil doc, so without this a new vertical silently points writers at Vigil. | mirrored here |
| 3 | `provision-vertical-slack-channels` | The canonical nine channels: rename the 3 the workspace ships (`general`/`random`/`help-desk`), create the 6 by hand, then verify live and audit Teams audience targets for names left stale by renames. No channel API exists, so it is a runbook plus checks. | mirrored here |
| 3 | `provision-vertical-teams-integrations` | Turns **a tag on a person** into actual access: creates the vertical-prefixed team tags, builds the canonical 10-audience set, attaches every Slack/Google/Insightful/Studio target, provisions Everyone into the all-hands channels, and turns on auto-provisioned @mercor.expert email. Verifies by resolving every target by channel id. | mirrored here |
| 4 | `create-vertical-canvases` | Clone the canonical Abacus 13-canvas set into a new vertical's workspace and adapt each one: title, domain wording, channel mentions, SVA + Insightful, vertical links left as explicit TBDs. | mirrored here |
| 4 | `editing-channel-canvases` | Operating manual for editing an existing canvas set, plus **the per-vertical canvas ID registry** (Abacus / Atria / Rampart / Cadre). The registry is the irreplaceable part. | mirrored here |
| 4 | `sweep-canvas-links` | **Invoked as surface 4 of `replace-instructions-link`, not as a standalone step** (2026-07-29). One pass over a vertical's whole canvas set: fill the TBD slots from live sources, point every instructions link at that vertical's own Google Doc labelled `<Vertical> Instructions`, and add the Studio access block (bare root + Okta route + Chrome) to the writer-facing canvases that lack it. Inventory first, never invents a URL, re-reads after writing, updates the canvas registry. | mirrored here |
| 4 | `add-vertical-calendars` | The two Google Calendars (Onboarding + Writer), shared to the vertical's tag-synced groups so access grants and revokes itself, links pasted into every canvas with a calendar slot. Also audits the other verticals for the 3 recurring defects. | mirrored here |
| 5 | `provision-vertical-automations` | Author the canonical 7-automation launch set (3 access, 3 comp, 1 EPM auto-tag) from parameterized templates that carry no source vertical's ids, confirm every comp number instead of inheriting it, install the bonus self-ID dedup guard as a two-phase write, then verify what is actually draft vs active. Onboarding emails and the 48hr stalled-task reminder are deliberately OUT of scope. Prefer this over cloning. | mirrored here |
| 5 | `clone-vertical-automations` | Replicate a vertical's Teams-platform automations onto another vertical, repointing every project/world/campaign/tag/job-title reference. Creates DRAFTS only; a human activates. **Superseded by `provision-vertical-automations` for new verticals**; keep for one-off copies. | mirrored here |
| 6 | `add-vertical-bots` | Studio Doctor (`/doc` + automation crons) and World File Upload bot, end to end. Wires both repos, writes both Slack app manifests, pauses for secrets and app creation, then checks the deploys. | mirrored here |
| all | `verify-vertical-spinup` | Read-only audit of one vertical against the whole playbook: **11 areas, 42 checks** (area K, numbers and candidate-facing copy, added 2026-07-29), live APIs over the Essentials sheet. Four verdicts including **BROKEN** for things that exist but do not function, which is what checklists miss. Writes nothing. | mirrored here |

## Campaign-ops skills (running a vertical, not spinning one up)

Kept separate on purpose. These are day-to-day Panacea/Sparta operations.

| Skill | Purpose |
|---|---|
| `start-task-iteration` | Entry point for picking up a task: verifies creds, prompts for ids, lays out the skill chain. |
| `upload-task-files-to-studio` | Full 8-step push of a `studio_export` folder to a Studio task, plus a sense-check for answer-file leakage. |
| `sync-to-external-storage` | Fire the world sync so Taiga mounts the right volume. Must run before `run-in-taiga`. |
| `run-autoqc` | Fire the "ML - Agentic QC" remix for a fast Studio-side sanity check. |
| `run-in-taiga` | Submit a task to Taiga (Run External Agent), monitor to completion. |
| `trigger-taiga-qc` | Trigger the Taiga `env_linter` QC report on a problem-version, monitor the job. |
| `fetch-taiga-qc-result` | Pull the QC findings back as JSON, filtered to the task's problem-version. |
| `panacea-unblock-running-agent-runner` | Unstick tasks parked in "Running Agent Runner & QC" by firing `mark_agent_run_as_done`. Never dispatches QC. |
| `panacea-resync-taiga-outputs` | Re-sync completed Taiga outputs into Studio when trajectories or deliverables do not show. |
| `panacea-taiga-delivery-tagger` | Bulk-tag problem-versions for delivery, resolving each task to the version that actually holds the work. |
| `panacea-reassign-owner-or-transition-task-status` | Temp-edge admin ops: reassign owner, move status, no rerun. |
| `panacea-workspace` | Query/analyse Studio data via the REST API for reports and exports the MCP tool cannot reach. |

---

## Gaps: setup steps with NO skill yet

This is the backlog. Playbook order.

| Step | Missing skill | Why it is worth one |
|---|---|---|
| ~~1~~ | ~~**Teams project setup**~~ | **BUILT 2026-07-29** as `create-vertical-teams-project`. Never run end to end yet. |
| ~~1~~ | ~~**Listing creation**~~ | **BUILT 2026-07-29** as `create-vertical-listing`, spec derived from the live Cadre / Abacus / Atria listings and roles. Never run end to end yet. |
| 1 | **Studio-to-Teams project link** | There is no `enable_project_integration` slug for Studio; the clone sets no project id. Undocumented manual step. |
| 1 | **Neon + SVA sync pipeline** | Optional, but nothing captures how to add a vertical to SVA. |
| 2 | **Instructions SSOT bootstrap** | **The writer instructions doc will NOT get a skill** (decided 2026-07-29; one was built and deleted the same day). Recasting it is domain judgment, and the link fan-out that used to justify the skill now lives in `replace-instructions-link`. Still genuinely open and worth a skill: the **instructions-hub DB entry** (the hub repo carries no per-vertical content yet) and the **reviewer guide**. |
| 5 | **EPM comp has no home** | The weekly base, throughput multiplier and monthly bonus are what an EPM is actually paid, and verified 2026-07-29 there is no Teams field, no skill and no section of the EPM Training doc that holds them. `create-vertical-teams-project` now asks (row 9b) and hands them back, which is a stopgap, not a home. |
| ~~4~~ | ~~**Maven setup**~~ | **CLOSED 2026-07-29.** Covered by the marketplace skill `mercor-skills-global:maven-provision`, which validates prerequisites, deploys, and connects announcement channels to Maven's search context. Do not build a Sparta-local one. |
| 4 | **Technical channel ticket workflow** | The emoji triage convention and the tech-EPM ownership model are documented in prose only. |
| ~~5~~ | ~~**Launch automations from scratch**~~ | **BUILT 2026-07-29** as `provision-vertical-automations`. Never run end to end yet. |
| ~~4~~ | ~~**Canvas link sweep**~~ | **BUILT 2026-07-29** as `sweep-canvas-links`. Never run end to end yet. |
| 6 | **SVA per-vertical tracking app** | Adding a vertical tab, crons, and dashboards to SVA. |
| 7 | **EPM + reviewer org structure** | Roles, per-role instruction docs, EPM training doc, EPM skills bundle. |
| ~~all~~ | ~~**`verify-vertical-spinup`**~~ | **BUILT 2026-07-29.** Never run end to end yet; the first real run is itself a test of the check specs. |

---

## Housekeeping, resolved 2026-07-28

**There are 13 spinup skills, not 3.** The `skills/` folder here only held 3, which
made it look like the rest were missing. They were all installed and working; only
the backup mirror was incomplete. Fixed: all are now mirrored into `new-project-spinup/skills/`, verified
byte-identical to installed. Count is 13 as of the teams-integrations skill.

**Nothing we authored was ever un-installed.** Every skill is live in
`~/.claude/skills`. The problems were all on the backup side:

1. **Five skills had no backup at all**, and `~/.claude` is not a git repo, so they
   existed in exactly one place: `clone-vertical-automations`,
   `create-vertical-canvases`, `editing-channel-canvases`,
   `new-vertical-drive-folder`, `replace-instructions-link`.
   `editing-channel-canvases` carries the per-vertical canvas ID registry, which is
   not reconstructible from anywhere else. Now mirrored.

2. **`clone-sparta-campaign`: the copy in `sparta-professionals-clone/` is STALE**,
   1636 bytes behind installed. It is missing the entire 2026-07-27 campaign-level
   block: the `world_remix_configs` `prometheus_sync` requirement,
   `campaign_settings.pipeline_autoqc` with `spec_world_id` pointing at the
   target's OWN GWB, and the note that Atria's wrongly points at Abacus's GWB. The
   good version is now mirrored here. Treat that other copy as dead.

3. **`panacea-resync-taiga-outputs`: the copy in `vigil-workspace/skills/` has a
   WRONG campaign id.** It labels `camp_863f41af2c71448ca85340e75630c7a2` as
   Panacea Consulting, but that is **Vigil's** campaign. Installed correctly says
   `camp_63e11a2d346e4454f6784532aaf0453a`, confirmed against memory and
   `RLS.CAMPAIGN_PROJECT_MAPPING`. It is an ops skill so it is not mirrored here;
   the installed copy is the correct one.

**Stale duplicate copies still on disk**, not authoritative, do not read from them:
`Desktop/MERCOR/sparta-professionals-clone/` (3 skills) and
`Desktop/MERCOR/vigil-workspace/skills/` (11 ops skills).

Rule going forward: **installed is the source of truth, `new-project-spinup/skills/`
is the backup.** Sync one way only, installed to backup.

**Exception observed 2026-07-29:** `add-vertical-bots` was rewritten in the MIRROR (the
three-sweep set, after four sweeps were retired) while installed still carried the stale
seven-sweep text naming `faga-sync` and `pref-sync`, the two that looped. The mirror was
promoted to installed that day. Diff both copies before trusting either; "installed wins" is
the default, not a guarantee. Re-run a recursive diff
before trusting any copy elsewhere under `Desktop/MERCOR/*/`.
