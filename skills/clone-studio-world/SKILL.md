---
name: clone-studio-world
description: >
  Clone an RL Studio world (or campaign subset) into a target campaign AND make it actually
  runnable. A plain config clone leaves the world unrunnable and carrying the SOURCE campaign's
  identity: no AutoQC hooks, no world-level verifier, the wrong default agent, the source's Taiga
  env, the source's base_world_id, and stale world files. This skill wires all of it, including the
  canonical 22-hook Sparta AutoQC chain and the qc_specs it fires (hooks are a separate entity that
  never clones and never inherits on spawn). Always Sparta: sparta_agentic_grading grader and
  sparta_external_agent, never Prometheus and never a loop_agent. Worlds it creates are TEST worlds,
  named and stamped so the Studio Doctor cron sweeps can never act on them. Use when cloning a
  campaign or world, standing up a test world from an existing one, debugging a cloned world that
  fails the Sparta runner preflight, or filling a hook/verifier/agent gap on any world whose tasks
  strand in "Running Task AutoQC" or whose QC never appears in the Studio panel.
user_invocable: true
---

# Clone an RL Studio world AND make it correct

**A config clone is necessary but NOT sufficient.** Cloning Abacus→Atria (and learning Abacus was
itself a Vigil clone) surfaced the full set of things a clone leaves wrong. Skip any and the world
silently strands tasks in "Running Task AutoQC", fails Run External Agent, grades against the wrong
campaign, or clones writer worlds from the wrong template.

This skill absorbed `provision-autoqc-hooks` and `insert-autoqc-hooks` on 2026-07-29. There is one
skill for "make this world correct", not three. Hook mechanics live in
`references/autoqc-hooks.md`; the essentials are inline below.

## HARD RULE 1: always Sparta. Never Prometheus, never a loop agent.
Three separate things have to say Sparta, and a clone gets any of them wrong:
- **Grader** = an `eval_configs` entry with `eval_defn_id == "sparta_agentic_grading"`. Prometheus is the retired backend (Vigil cut over mid-June 2026). Wiring it made Abacus **double-run** the agent and pulled env-linters from another environment.
- **World-level verifier** = one row, `task_id: null`, `eval_config_id` = `5502d234-7a43-4ae8-a8b6-75ce19a82186` (the Sparta grading config). Never cloned, so always created here.
- **Default agent** = an agent whose `agent_config.agent_config_id == "sparta_external_agent"`. A clone commonly carries a **`loop_agent`** (an APEX in-Studio agent); the runner rejects it with `no_sparta_external_agent`.

The scripts now **fail closed** on all three: `clone_and_wire_world.py` aborts if the world has no
Sparta grading config, if it finds more than one world-level verifier, or if the default agent is
not a sparta_external_agent and no correct id was supplied (it also verifies the id you supply
really is one, and re-reads after the PATCH). `wire_world.py` ports hooks through the campaign
engine's `drop_prometheus=True` path, so no Prometheus hook can be created.

## HARD RULE 2: a world this skill creates is a TEST world, and the automated sweeps must never touch it
Cloning is for testing. Production writer worlds are **spawned** by the builder flow, never cloned.
So a cloned world must stay out of scope for the Studio Doctor cron sweeps (`advance`,
`unclaim-reviews`, `nudge-writer-to-hand-off`), which advance tasks and fire agent runs for real.

Their in-scope rule (`lib/flow/world-scope.ts` in `panacea-cli-slack`) is:
`world_description LIKE 'Tasking world from builder task %'` **AND NOT** the name matching
`%donottouch%` / `%do not task%` / `%do_not_task%` / `%test%`.

**A plain clone copies `world_description`**, so cloning a real writer world inherits the builder
stamp and the sweeps would treat the test world as live writer work. Both guards are therefore
enforced by `clone_and_wire_world.py`:
1. the new world's **name must carry a test marker** (`test`, `donottouch`, `do not task`), and
2. the description is **rewritten** to a `[clone-test] config clone of <src_world_id>` lineage line that never begins with the builder stamp.

If you clone by hand or through the Studio UI, do both yourself, then confirm with
`isGwbTaskingWorld` / the SQL in that file that the world is out of scope. Renaming a test world to
look production is what puts crons back on it.

## The invariant: what a correct, runnable tasking world has
1. `world_custom_fields.taiga_environment_id` = **the TARGET campaign's** Taiga env (NOT the source's).
2. **Exactly one** world-level verifier: `verifiers` row with `task_id = null`, `eval_config_id` = the Sparta grading config (`sparta_agentic_grading`, canonical id `5502d234-7a43-4ae8-a8b6-75ce19a82186`).
3. Grader is **Sparta, never Prometheus** (`eval_configs[].eval_defn_id == "sparta_agentic_grading"`).
4. `default_agent_ids` contains the **`sparta_external_agent`** (an agent whose `agent_config.agent_config_id == "sparta_external_agent"`), NOT a `loop_agent`. A clone can carry a `loop_agent` default (e.g. an APEX in-Studio agent); the Sparta external runner preflight rejects it (`no_sparta_external_agent`). Fix: `PATCH /worlds/{id}` `{"default_agent_ids": ["<sparta_external_agent id>"]}` (full-replace list).
5. **22 AutoQC hooks** on a tasking world (4 on the Golden World Building world), each pointing at a qc_spec that exists **in the target campaign**. Hooks are a `/hooks` entity: not a world field, not in the clone bundle, not inherited when the builder spawns a writer world.
6. The **`sparta_create_tasking_world`** remix's `base_world_id` points at **the target campaign's own `[Live New Flow] Final Tasking World`** (not the source's).
7. **No cross-campaign references** anywhere (source env id, source campaign id, source world ids), and especially the ones baked into remix `remix_world_field_values`.
8. **`task_schema` field parity with the source world.** A hand-built clone can silently drop a field. Delphi's hand-built sample world came out with 40 fields where every other live runner world (Panacea, Abacus, Atria, Rampart, and Delphi's own canonical worlds) has 41+, the missing one being the hidden `prometheus_submission_history` (`field_8c482d232e034b3296e9a9b614d040cc`). Diff the field ids against the source and fail loudly on a missing one; `PATCH /worlds/{id}` full-replaces `task_schema`, so repair is GET-append-PATCH-verify.
Plus the **world file bundle** (the data the agent runs against), which lives outside the config bundle and must be re-synced per world (step 7).

**Campaign-level, not per world:** the campaign's `world_remix_configs[*].world_remix_world_field_values.prometheus_environment_id` (the Sync to External Storage remix) must match the worlds' `taiga_environment_id`. A split here is invisible on every world page: Studio shows the right env on all 5 worlds while the file sync writes into the OTHER environment's bucket. Delphi sat split from 2026-07-31 to 2026-08-02. Use `restamp-taiga-env --inventory`, which reports the campaign reference alongside the world ones.

## Runner preflight fails in a fixed ORDER: fix all of these before you test-run
With zero hooks the task never even reaches the runner: it strands in "Running Task AutoQC". Once
hooks fire, `Run External Agent` preflights and rejects the world one reason at a time, so you fix
one and immediately hit the next. Establish ALL of them up front. The observed sequence (from a real
Abacus clone, 2026-07-21):
1. `must have exactly one Sparta grading world-level verifier (task_id IS NULL). Found 0` → invariant 2 (create the verifier).
2. `World has no sparta_external_agent configured in its default agents. configured_agent_config_ids=['loop_agent']` → invariant 4 (repoint the default agent).
3. trajectory goes to `error` with an empty volume → world files never synced (step 7).

**Do NOT use `platform_has_environment` as the mount test.** It reads `False` on healthy Sparta-Env
trajectories too, verified on a fully successful Delphi run 2026-08-02 whose container listed all 52
files. Same for `final_answer`, which stays `None` on a good run because the External Fetcher writes
into `trajectory_messages` / `trajectory_output` instead. The only trustworthy mount evidence is the
**container's own `ls` output inside `trajectory_messages`**, showing the files under `/tmp/world/`
with non-zero byte sizes. A freshly created trajectory is an empty shell until Taiga's results sync
back, so re-read it a minute or two after the job reports success before judging.

So the full make-runnable set is: **hooks + qc_specs + verifier + sparta_external_agent + env +
files** (and `base_world_id`/scrub for the spawn pipeline). None of these come with the config clone.

**A world wired here must come out identical to one a CAMPAIGN clone wires.** So there is exactly
one implementation and this skill does not own it: `wire_world.py` imports
`clone-sparta-campaign/clone_sparta_campaign.py` (the current engine, adopt mode 2026-07-29) and
calls its own `fork_campaign_specs()`, `port_hooks()` and `wire_runner_worlds()` on the one target
world. The hook set is read **live** off the source campaign's `[Live New Flow] Final Tasking World`,
which is what a campaign clone ports from. The older `provision_hooks.py`, `insert_hooks.py` and the
`canonical_hooks.json` capture were **deleted** 2026-07-29: the capture had drifted to 18 of the 22
hooks, which is exactly what a second implementation costs. When a whole campaign is in play, run
`clone-sparta-campaign` itself.

## What a clone does / does NOT carry
| Thing | Cloned? | Action |
|---|---|---|
| Config: flow, statuses, task_schema, remix configs, eval_configs (defs), scoring, world_settings, task_spec_config (AutoQC spec), world_custom_fields | ✅ | keep |
| Tasks / golden responses / trajectories / grades | ❌ (content) | leave out |
| **Hooks** (the `/hooks` router chain) | ❌ | **create (step 4).** Skip and the task strands in "Running Task AutoQC" forever |
| **qc_specs** (what the AutoQC hooks fire) | ❌ (`{"specs": []}` on a fresh campaign) | **fork per campaign (step 4)**, then remap every hook's id |
| **Verifier instances** (world-level Sparta grader) | ❌ | **create explicitly** (step 3) |
| **Default agent** (`default_agent_ids`) | ⚠️ may be a `loop_agent`, not `sparta_external_agent` | **verify + PATCH to sparta_external_agent** (step 3b) |
| **World file bundle** | ❌ (carries a STALE `prometheus_gcs_path` → the SOURCE world) | **re-sync per world** (step 7) |
| `taiga_environment_id` value | ✅ but = SOURCE's | **re-stamp to target** (step 2) |
| `base_world_id` in Create Tasking World remix | ✅ but = SOURCE's world | **repoint to target's own [Live New Flow]** (step 5) |
| Baked-in env in QA remix `remix_world_field_values` | ✅ but = SOURCE's env | **re-stamp** (step 6) |

## The two ways worlds get created, and which needs manual wiring
- **Spawned via the builder flow** (`sparta_create_tasking_world` remix on the world-building world): the remix **auto-wires** env (inherited from `base_world_id`'s `world_custom_fields`) AND creates the world-level Sparta verifier atomically on spawn. **Proven** (fresh Vigil spawns: env + 1 verifier created ~1s after the world). But **hooks do NOT come with a spawn either.** A freshly spawned writer world still needs step 4. For the *ongoing pipeline*, the durable config fix is step 5 (point `base_world_id` at the target's own wired `[Live New Flow]`).
- **Directly cloned** (this skill): nothing auto-wires; do steps 2–7 yourself on the cloned world.

## Procedure
1. **Create/resolve target campaign.** `POST /campaigns/ {campaign_name, company_id, account_id}`. NOTE: the campaign object has no `settings`/`environment`/`domain` keys (only `campaign_settings`), so don't spread non-existent keys.
2. **Clone config, then re-stamp env.** `GET /worlds/{src}` → `POST /worlds/ {world_name, campaign_id, world_description, domain}` (name carries a test marker, description is the `[clone-test]` lineage line, NEVER the copied builder stamp: see HARD RULE 2) → `PATCH /worlds/{new}` with the CLONE_KEYS bundle. Sanitize `world_custom_fields`: keep `taiga_environment_id` **set to the TARGET env**, drop `prometheus_*` runtime keys.
3. **Create the world-level Sparta verifier** (only on worlds that run the Sparta runner: tasking worlds, NOT world-building/labeling worlds): `POST /verifiers/ {world_id, task_id: null, eval_config_id: <sparta cfg>, verifier_values: {}, verifier_index: 0}`. Confirm exactly one via `GET /verifiers/world/{id}`. (Caveat: `GET /verifiers/world/{id}` and the Snowflake `VERIFIERS` mirror both under-report; they returned empty even on a known-good world; trust the runner's DB check / the `POST` 201, and just ensure you created exactly one.)
3b. **Verify the default agent is `sparta_external_agent`.** `GET /worlds/{id}` → `default_agent_ids`; for each, `GET /agents/{id}` → `agent_config.agent_config_id`. If it is `loop_agent` (or anything else), `PATCH /worlds/{id}` `{"default_agent_ids": ["<the sparta_external_agent id>"]}` (copy the id from a known-good tasking world in the same campaign). Full-replace list. **`clone_and_wire_world.py` automates this**: set `SPARTA_EXTERNAL_AGENT_ID` and it PATCHes any runner world whose cloned default isn't a sparta_external_agent; left unset, it WARNs instead of silently shipping a broken world.
4. **Fork the qc_specs and attach the hooks, via the campaign engine.** `python3 wire_world.py --campaign camp_TARGET --world world_TARGET` (dry run; add `--execute`, or `--builder` for the Golden World Building 4-hook set). It forks the campaign-scoped qc_specs by name, ports the live hook set with the payload AND predicate remap, drops Prometheus, skips hooks whose target remix is absent from the world, then wires the verifier, the sparta_external_agent and the SER-Heal remix. It verifies the final count is 22 (4 on the builder) and exits non-zero if short. Full detail: `references/autoqc-hooks.md`.
5. **Repoint `base_world_id`** on the world-building world's `sparta_create_tasking_world` remix → the target campaign's own `[Live New Flow] Final Tasking World`. (Read task_remix_configs, change the one field, PATCH the FULL list back, which is a replace.)
6. **Scrub cross-campaign refs.** Scan every config column for the SOURCE env id, SOURCE campaign id, and SOURCE world ids; re-stamp/remove. Especially QA remixes that bake env into `remix_world_field_values` (`taiga_qa_pull`, `taiga_job_sync`, `taiga_preference_fetch` [`prometheus_environment_id`], `taiga_qa_create_finding`, `taiga_qa_trigger`).
7. **Re-sync the world file bundle.** A clone inherits a STALE `world_custom_fields.prometheus_gcs_path` that still points at the SOURCE world's files (e.g. a cloned Abacus world pointed at `world_15775aee…`), so the runner mounts the wrong/empty volume and the trajectory errors. Fire **Sync to External Storage**: `POST /world-remix/world/{id}/remix` `{"world_remix_config_id": "<Sync to External Storage remix id>", "world_remix_runtime_field_values": null}` (synchronous, up to ~600s; may return async with a `job.job_wrx_id` to poll; needs CAMPAIGN_ADMIN). Or trigger it from the Studio UI, or run `sync-to-external-storage`. Verify: `GET /worlds/{id}` → `prometheus_gcs_path` now contains THIS `world_id` with a fresh timestamp, and `prometheus_synced_at` is recent.
8. **Verify:** `GET /hooks/world/{id}` == 22 (tasking) / 4 (builder), no duplicates; `GET /verifiers/world/{id}` == 1 Sparta verifier; querier `world_custom_fields->>'taiga_environment_id'` == target env; the `sparta_external_runner` remix is present in the tasking world's `task_remix_configs`; the cross-campaign scan (step 6 query) returns clean; then a live Run External Agent test creates a Taiga job and QC auto-dispatches.

## AutoQC hooks: the canonical 22 and the rules that cost the most
The full live-captured inventory, every remap, the chain walkthrough: **`references/autoqc-hooks.md`**.

- **The set is 22 on a tasking world, 4 on the Golden World Building world, and they never mix.**
  Verified live on the `[CLONE ME]` tasking world (`world_640451310b5140bbbc861140079e58d6` in
  `camp_4040aadecd0544a6ab7f9a97780b809f`) on 2026-07-29: 22 hooks, **2 of them deliberately
  disabled** (`Run Task AutoQC (AQC)` and `Run Trajectory AutoQC (AQC)`, the non-scrub-gated
  variants) and **6 sharing 2 names** (4x `Auto-sync on ready for delivery`, 2x `...preference
  labels`) differing only in target remix.
- **HARD RULE: do not wire Prometheus.** New Sparta campaigns are Sparta-chain only (Vigil cut over
  mid-June 2026). Drop the three hooks whose target remix is `04c87e48…` (Taiga QA Finishes),
  `6652e121…` (External Agent Finishes) or `5aaaf11a…` (Running Agent Runner). Attaching them to
  Abacus made the agent **double-run** and made env-linters pull from a different environment, which
  engineers flagged. The template carries none of them.
- **Read the set live, never from a file.** A stored capture drifts, which is how the deleted
  `canonical_hooks.json` ended up 18 of 22. The table in the reference doc is a checklist for
  verifying a result, not a source to create from.
- **Remap the `hook_source_predicate[].value` too, not just `hook_target_payload`.** Predicates gate
  hooks on a `qc_spec_id` or `remix_id`. Remap only the payload and the hook silently never fires:
  QC runs and the task never advances, which is a confusing half-working state.
- **qc_specs are campaign-scoped and do not clone**, so they are forked by NAME first. The four the
  tasking hooks fire are Task AutoQC, Trajectory AutoQC, Failure Analysis & Grader Analysis AutoQC,
  Preference Labels AutoQC (the template campaign holds nine campaign-scoped specs in all).
- **`port_hooks()` dedupes by hook NAME**, and 6 hooks share 2 names, so a re-run after a partial
  failure silently skips the duplicates it still needs. `wire_world.py` checks the final count and
  fails loudly instead.

## Auth
An RLS key is scoped to **one campaign**. The shared `studio` MCP tool and the panacea-workspace key
403 with "not scoped to the requested campaign" on a new vertical, so for a new campaign the
operator supplies **that campaign's own key** (Studio → Campaign Settings → API).

- **Never put the key in chat, a CLI arg, or the transcript.** It goes in `spinup.env` (gitignored)
  next to the scripts, which read it and never print it.
- Company and account are per-campaign: take them from `GET /campaigns/`, which carries `company_id`
  and `account_id`. Do not assume the shared Sparta pair.
- **Use `curl`, never Python `urllib`.** The Studio API sits behind Cloudflare, which returns error
  1010 "Access denied" (403) to urllib's default user agent. Every write failed until this was
  switched. (Same reason `replace-instructions-link` sends a browser UA.)

## Cross-campaign scan query (run per world, in the target campaign)
```sql
SELECT world_id, world_name,
  blob ILIKE '%<SOURCE_ENV_ID>%'   AS src_env,
  blob ILIKE '%<SOURCE_CAMPAIGN>%' AS src_camp
FROM (SELECT world_id, world_name,
  coalesce(task_remix_configs::text,'')||coalesce(eval_configs::text,'')||coalesce(world_settings::text,'')
  ||coalesce(world_custom_fields::text,'')||coalesce(bundle_configs::text,'')||coalesce(task_spec_config::text,'')
  ||coalesce(flow_config::text,'')||coalesce(default_agent_ids::text,'')||coalesce(default_judge_ids::text,'') AS blob
  FROM worlds WHERE is_latest AND archived_at IS NULL) w;
```
(Verifiers and hooks are NOT visible to the querier, its campaign CTE joins through tasks, dropping
`task_id IS NULL` rows. ALWAYS read verifiers via `GET /verifiers/world/{id}` and hooks via
`GET /hooks/world/{id}`.)

## Hard-won gotchas
- **Verifiers can't be inherited.** They are separate rows, not in the clone bundle. This is the #1 cause of `Found 0 world-level verifier(s)` preflight failures.
- **Hooks can't be inherited either**, not by clone and not by spawn. A world can look completely configured and have zero hooks.
- **qc_specs do not clone.** A fresh campaign has `{"specs": []}`; fork them or every `autoqc_invoke` hook fires against a spec that does not exist.
- **A cloned world inherits the SOURCE campaign's identity.** Env, `base_world_id`, and baked-in env refs all point back at the source. Abacus (cloned from Vigil) was spawning writer worlds from *Vigil's* base and would have used Vigil's env. Always run step 6.
- **`base_world_id`** in Create Tasking World is a hardcoded world id; clones point at the source's, so repoint to the target's own `[Live New Flow]`.
- **World files never clone.** Config only.
- **A `prometheus_sync_trigger` remix is NOT a Prometheus grader.** It's the world-file sync; the grader guard checks `eval_configs`, not remixes.
- **PATCH replaces lists/objects** (`task_remix_configs`, `world_custom_fields`, `world_settings`): read-modify-write the full value, and build the merged array with a script, never by hand (15-18KB, hand-editing risks truncation).
- **`GET /qc-specs` 307-redirects** to `http://` and strips auth. Call `/qc-specs/` with the trailing slash and `?campaign_id=`.
- **The workbench `lib.api.api_post` has no `method=` arg and only POSTs.** Use a real PATCH (see the script's `api_patch`). RLS keys are campaign-scoped, so a workbench key won't reach another campaign; you need Okta-forwarded creds or a broad-access path.
- **Big world configs (~500KB)** can't be pushed inline through a JSON MCP tool; run the script with proper auth.
- **Campaign-level clone tools** (the "rehome custom field files" UI flow) copy config + optionally file assets and append a suffix to world names (e.g. "…Atria"): dedupe/prune extras and rename after. They still do NOT create verifiers, hooks, or repoint `base_world_id`; run steps 3–6 afterward.
- **Only canonical-flow worlds take the canonical hooks.** Flag an old-flow world (a "Golden" world with `grader_feedback`, or a different scrub id) for a Studio-team re-sync rather than hand-patching it.
- **New tasking worlds cloned or spawned later inherit the same gaps.** The durable fix is for the Studio team to fold hooks, the full remix set and the env re-stamp into their clone/spawn. Re-run this skill on any new live tasking world until then.

## OPT-IN: the claim flow (central tasking). Off by default.

Default Sparta assumes **the writer creates their own task**, so creator == owner and every
permission gates on `and_actor_created_required`. Some verticals want **central tasking**: an SPL
seeds tasks, a writer claims one. As of 2026-08-02, **5 of 5 live verticals do NOT use this**
(Panacea, Abacus, Atria, Rampart, and Delphi's own canonical worlds), so it stays off unless asked
for. The nearest precedent in the wild is Vigil's `[Live] Consensus Labeling`, which has an
`Available` entry status for pool-claiming.

Modelled on `Delphi · Sample World 1` (`world_48aed704fcc94a698c66d7a0ff2d5e49`), hand-built by an
engineer 2026-07-30. `test_add_claim_flow.py` asserts our generated edge matches theirs field for
field, so there is one dialect, not two.

```bash
python3 add_claim_flow.py            # dry run
python3 add_claim_flow.py --apply
python3 fix_claim_gating.py --apply  # MANDATORY, not optional, see below
```

**Four changes, and a subset leaves the world broken:**

1. An `Available for Claim` status where seeded tasks wait.
2. A `claim_sample_task` edge out of it into `Task Writing`, `to_owned_by: actor` and
   `and_actor_not_created_required: true`, so the claimant becomes the owner. **Never owner-gate this
   edge** — the claimant does not own the task yet, so owner-gating makes it permanently unclaimable.
3. `world_settings.annotator_visibility_require_assignment = false`. Without it the writer cannot
   **see** an unclaimed task, so the Claim button never renders and the flow looks broken with every
   other part correct. This is the likeliest half-done state.
4. `fix_claim_gating.py`. Everything downstream gates on `created`, which is now false for the
   claimant: they would see the Claim button, press it, and then be unable to edit what they claimed.

**Do NOT widen the `task_edit_content` grant's `from_status_ids`.** Delphi's sample world went 7 → 14
by adding the five `awaiting_*_fixes` sendback statuses plus Needs QC Revision and Running Preference
Labels AutoQC. That was checked and rejected: **Panacea** (oldest, highest-volume) also runs 7, and
every `Needs ... Fixes` status there has a `Start ... Fixes` edge into one of those same 7 editable
statuses. The Needs-Fixes status is a deliberate non-editable waiting room with a one-click door back
in, not a lockout. Widening makes tasks editable inside the waiting room.

## Files
- `wire_world.py`: **step 4.** Wires one world through the campaign engine's own functions, so the result matches a campaign clone. Dry run by default, `--execute` to write, `--builder` for the GWB 4-hook set. Requires `clone-sparta-campaign` to be installed alongside; it aborts if the engine is missing.
- `clone_and_wire_world.py`: steps 1 to 3b + 5 to 6 (config clone, test-world naming and description, env re-stamp, verifier, agent, base_world_id, scrub) plus verification.
- `fix_claim_gating.py`: creator-gated → owner-gated, on the 5 review-claim edges AND the two `task_edit_content` grants. **Mandatory after `add_claim_flow.py`**; optional otherwise. Never widens the edit grant's `from_status_ids` (see below). Tests: `test_fix_claim_gating.py`.
- `add_claim_flow.py`: **OPT-IN, off by default.** Converts a world to central tasking, see the section below. Tests: `test_add_claim_flow.py`.
- `test-fixtures/`: real flow/status configs pulled from live Delphi, Panacea and the hand-built sample world on 2026-08-02, used by both test files. Re-pull them if Studio changes the canonical flow; a stale fixture makes both suites lie.
- `references/autoqc-hooks.md`: the live-captured 22-hook inventory, the qc_spec map, every remap, the chain and verification.
- `spinup.env.example` → copy to `spinup.env` (gitignored, never printed).
- **Deleted 2026-07-29:** `provision_hooks.py`, `insert_hooks.py`, `references/canonical_hooks.json`. They were a second and third implementation of the hook port, and the JSON capture had drifted to 18 of 22 hooks.

Established on Abacus (`camp_930d4d8b84d2436497b2f3fcf79d483c`) 2026-07-13/21; sources Panacea
(`camp_63e11a2d…`) and Vigil (`camp_863f41af…`). `insert-autoqc-hooks` and `provision-autoqc-hooks`
were merged into this skill 2026-07-29 and deleted, not archived. Mirrored to
`~/Desktop/MERCOR/new-project-spinup/skills/clone-studio-world/` (scripts included, **not**
`spinup.env`) by the `sync-skills.sh` Stop hook, which commits and pushes to
`ryugo-eun/new-project-spinup` — so that mirror IS a git repo and IS the backup. The live
`~/.claude/skills` copy is not under version control.
