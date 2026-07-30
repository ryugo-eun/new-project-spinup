---
name: clone-sparta-campaign
description: >-
  Wire a Sparta RL-Studio campaign so it actually runs. The human clones
  "[CLONE ME] Sparta Professionals Campaign" in the Studio UI, then this skill writes in
  everything that clone leaves broken: world names, hooks, verifiers, qc_specs, the Taiga env,
  base_world_id, the consensus target, and the campaign-level configs. Interactive, inventories
  before it writes, dry-run by default. Use for "clone a Sparta campaign", "spin up a new
  vertical", "wire the campaign I just cloned", "create an RLS campaign".
---

# Wire a cloned Sparta RL-Studio campaign (interactive)

A Studio UI clone of a campaign comes up **unrunnable and with no AutoQC**. This skill adopts the
campaign a human already cloned and fixes every gap. Engine: `clone_sparta_campaign.py`
(curl transport, bodies over stdin, dry-run default).

**Default mode is `adopt`.** It never creates worlds, so it cannot produce duplicates. The old
create-and-clone path is still there behind `--mode create` for when the UI clone is unavailable.

## What a UI clone actually carries

Measured on a real UI copy of `[CLONE ME]` (campaign `camp_77e47999`) on 2026-07-29. Do not take
this on trust from a checklist; the engine re-reads it every run and prints an inventory.

| Thing | UI clone state | Adopt mode |
|---|---|---|
| World names | suffixed `- copy` (Rampart's variant is ` - Copy`, and `test_t_1` lowercase) | matched through the suffix, then renamed to canonical |
| Hooks | **zero on all four worlds** | ports 22 + 22 + the 4 builder hooks |
| Verifiers | **zero** | creates the world-level Sparta verifier |
| qc_specs | **`[]`**, nothing clones | forks all 9 including `AutoQC` |
| Campaign configs | `world_remix_configs []`, `pipeline_autoqc` null | provisions both |
| `base_world_id` | points at the **source** tasking world | repointed to the target's own |
| Consensus target | points at **Vigil's** consensus world | repointed to the target's own |
| Taiga env | inherited, and it also lives inside remixes | re-stamped everywhere |
| Default agents | correct on a `[CLONE ME]` clone | verified, fixed if a loop_agent |
| SER-Heal remix | present on the runner worlds | verified, added if absent |

**The consensus leak is a defect in `[CLONE ME]` itself.** Its tasking world sends consensus
labeling into `world_8c245e163f334de9bde7c59e84904b27`, which is **Vigil's** own
`[Live] Consensus Labeling` world (confirmed 2026-07-29). Every clone inherits it, Cadre
included. Name pairing cannot fix it because the id is not one of the four source worlds, so
adopt mode repoints it explicitly.

## Audit of `[CLONE ME]` itself, 2026-07-29 (PT)

Full read of `camp_4040aadecd0544a6ab7f9a97780b809f`. **The template is current on the mechanics
and stale on the content.** What is genuinely right:

- All four canonical worlds present: tasking `world_640451310b5140bbbc861140079e58d6`, GWB
  `world_1dedc88b08c4419cbab3ef77c751db41`, consensus `world_59788f93f9ea474e933fe85cedff51f2`,
  `Test_T_1` `world_ea71166083724b87b516a0bb45019f70`.
- Tasking world carries **22 hooks**, all created 2026-07-22 and untouched since. Two are
  deliberately disabled (`Run Task AutoQC`, `Run Trajectory AutoQC`) because the enabled
  scrub-first path `Scrub Done → Run Task AutoQC` supersedes them. Do not "fix" those.
- 17 tasking remixes including **SER Heal**; GWB has its 4 (`Create Tasking World`,
  `Sync Trigger`, `Mark World as Created`, `Send for Pipeline Fixes`).
- **`base_world_id` is correct on the template**: the GWB points at the template's OWN tasking
  world. It only becomes wrong on a clone.
- `prometheus_gcs_path` is null, so there is no stale file pointer to inherit.
- No cross-campaign world ids anywhere except the consensus one below.

**Five defects live in the template, so every clone inherits them:**

| # | Defect | Evidence |
|---|---|---|
| 1 | **Taiga env is Abacus's.** `taiga_environment_id` = `2a931db7-ee3f-42d4-8125-9ff4361ed755` on BOTH the tasking world and the GWB. A clone whose operator skips the env question runs into Abacus's environment. Highest risk of the five | `world_custom_fields` on both worlds |
| 2 | **Old Vigil instructions doc**, `1nvj9D-IW7dBQyn-lOaXTINZoxVEJJ1R4GwzNgMOUi7U`, hard-coded **10x in the tasking world and 6x in the GWB** | `module_layout` + `module_layout_draft` |
| 3 | **Consensus points at Vigil** while the template's OWN consensus world sits unused | `consensus labeling` remix |
| 4 | **The GWB links a doc literally titled `[Outdated] Onboarding Document`** (`1PLYPvK3R5jwQHVE1cyLZLXi_UwId5fuD2lg-6mBk94o`, owned by erickchen@, last modified 2026-06-05) | GWB `world_settings` |
| 5 | **`campaign_settings` is `{}`.** No `pipeline_autoqc`, no `world_remix_configs`, no `analytics_config`. Clones start with zero campaign-level config | `GET /campaigns/` row |

Also noted, not a defect but a risk: the GWB links `world_spec_writer_template.docx`
(`10GQbLMWxpfnVw429uPluLL6eRiJ9ctxf`) **owned by a contractor alias**
(`marigold.terebellum.buna@mercor.expert`), who can delete or rewrite it. Same class as the
contractor-alias calendar owner defect.

**Adopt mode already repairs 1, 2, 3 and 5 on the target**, so a spinup that runs this skill is
safe. Fixing them **in the template** would make every future clone correct without the repair,
and items 2 and 4 are one-line link swaps. That is worth doing and is not done yet.

## 0. Prereqs

- `RLS_API_KEY` must reach the TARGET and the SOURCE campaign. Use a BROAD / Okta-forwarded key,
  never a single-campaign key. It lives in `~/Desktop/MERCOR/.env.local`; load with
  `set -a; . ~/Desktop/MERCOR/.env.local; set +a` and never print it.
- Confirm the key works: `GET /campaigns/` returns rows. A 403 means the key is scoped, so stop.
- **The human must have cloned the campaign already.** Adopt mode has nothing to adopt otherwise,
  and it will tell you so.

## 1. Interview the operator (AskUserQuestion)

Only the target campaign has no default.

| # | Question | Env var | Default |
|---|---|---|---|
| 1 | Which campaign did you clone? (required) | `SPARTA_TARGET_CAMPAIGN` | none |
| 2 | Source to wire from? Must be a COMPLETE Sparta campaign. | `SPARTA_SRC_CAMPAIGN` | `[CLONE ME]` `camp_4040aadecd0544a6ab7f9a97780b809f` |
| 3 | Taiga environment for THIS vertical? (required) | `SPARTA_TARGET_ENV_ID` | none, and there never will be one |

**Always ask question 3. Never supply a default, never reuse another vertical's env.** Every project
needs its OWN Taiga environment. The engine aborts when it is unset rather than guess, because a
fresh clone inherits `[CLONE ME]`'s env, so leaving it alone silently points the new vertical's runs
at another vertical's environment. The env is re-stamped in all four worlds AND inside **every remix that
carries an env id of its own**.

**Match the KEY, never a list of remix names.** Re-stamp any key matching `*_environment_id` inside
`remix_world_field_values`, on every remix, in every world. Remixes observed carrying one (Abacus's
`[Live] Golden Final Tasking World`, 2026-07-30): `QA_Results`, `Trigger Promo QC Report`,
`Taiga Job Sync`, `Taiga QA Create Finding`, and `Fetch Preference Labels` — that last one under
`prometheus_environment_id`, not `taiga_environment_id`. Treat that list as a sample, not the set: it grew
from two to five the first time anyone looked past the two that were known.

**If the vertical has no Taiga env yet, it has to be created first.** Give the operator these:

- How to create one, Erick Chen's walkthrough: https://www.loom.com/share/d040799ec8ab43e9ac4aa39795fdce91
- The Slack thread it came from: https://64f4423488df355.slack.com/archives/C0BMAC5BX4G/p1785286576111299?thread_ts=1785286398.426639&cid=C0BMAC5BX4G

That thread is where this rule comes from. Ryu asked Carlota Armero Saura how to create a Taiga env
for a new project, saying "I've been cloning abacus' and was unaware that each project needed a new
env"; Carlota passed it to Erick Chen, who answered with the Loom. **Cadre still runs on Abacus's
env (`2a931db7-ee3f-42d4-8125-9ff4361ed755`) because of that earlier assumption**, so treat any new
vertical pointed at `2a931db7` as wrong unless it really is Abacus.

Resolve the campaign id if the operator names a vertical: `GET /campaigns/` and match by name.
Do not skip the interview and assume the default source.

## 2. Run it

```bash
set -a; . ~/Desktop/MERCOR/.env.local; set +a
export RLS_COMPANY_ID=comp_2fa4115109d741cd94a3c409ed89e61f RLS_ACCOUNT_ID=acct_be8f7fcc2c554b33baa5a0c9d05496e3
export SPARTA_TARGET_CAMPAIGN="<answer 1>" SPARTA_TARGET_ENV_ID="<answer 3, required>"
python3 clone_sparta_campaign.py --dry-run     # inventory + every write, touches nothing
# after the operator has read the inventory and confirmed:
python3 clone_sparta_campaign.py --execute
```

Always dry-run first and show the operator the inventory. The inventory is the deliverable even
when nothing needs fixing, because nothing else tells you what a clone actually brought across.

Legacy path, only when the UI clone is unavailable:
`python3 clone_sparta_campaign.py --mode create --execute`, with `SPARTA_TARGET_NAME` set.

## 3. Scope: NEW campaigns only

This skill wires a campaign that was **just cloned**. It is not a repair tool for existing
verticals. It renames worlds and patches campaign settings, so pointing it at a live campaign would
be real damage, and the guards below exist to make that impossible rather than merely unlikely.

Guards, all verified to fire on 2026-07-29:

- **The target must be a fresh clone: zero hooks and zero qc_specs.** Anything else aborts. Verified
  against Panacea (4550 specs, 29 hooks on its tasking world) and Rampart, both correctly refused.
  Override with `SPARTA_ALLOW_REWIRE=1` ONLY to resume a run that died part way through.
- **All four canonical worlds must be present.** A fresh `[CLONE ME]` clone always carries them, so
  a missing one means the clone did not finish. Never wire a partial campaign.
- **Ambiguous adoption aborts.** Two worlds mapping onto one canonical name is a hard stop, because
  guessing which to wire is worse than not wiring.
- **Source lineage is checked first.** The source needs ~22 tasking hooks, 4 builder hooks and an
  `AutoQC` spec, else abort. A broken source wires a broken campaign.
- **Target equal to source aborts.**
- **Create mode refuses a campaign that already has any canonical world.** This is the fix for the
  old danger: `SPARTA_TARGET_CAMPAIGN` used to skip only campaign creation while the world-clone
  loop ran unconditionally, so pointing the old engine at an already-cloned campaign created
  **four duplicate worlds**.
- **Everything is idempotent.** Hooks and specs skip by name, so a second run is safe.

## 4. What it wires, in order

1. **Inventory** every world via `GET /worlds/{id}`. The list endpoint returns a SUBSET with no
   `world_custom_fields`, `default_agent_ids` or `eval_configs`, so never inventory off it.
2. **Rename** the worlds to canonical names. `PATCH /worlds/{id}` with `world_name` returns 200
   (verified). This matters because `clone-studio-world`, `replace-instructions-link` and
   this engine's own re-runs all resolve worlds by exact canonical name.
3. **Re-stamp the Taiga env to the operator's answer** in `world_custom_fields` AND inside
   `task_remix_configs` — every key matching `*_environment_id` in every remix's
   `remix_world_field_values`, not a named list (see the env section above; at least five remixes carry
   one, and stamping only the custom field leaves them all on the old environment). `task_remix_configs`
   is an ARRAY, so PATCH replaces it wholesale: read it, change only the matched keys, write the full array
   back, and verify the remix COUNT is unchanged afterwards rather than trusting the response.
   Also **strip `prometheus_*` runtime keys**
   when `prometheus_gcs_path` names another world. A stale path makes the runner mount the source
   world's files (`platform_has_environment=False`, empty or wrong trajectories) while everything
   else still looks correct.
4. **Repoint world references:** `base_world_id` to the target's own tasking world, the consensus
   `target_world_id` to the target's own consensus world, and anything else naming a source world
   by canonical-name pairing. Any foreign world id left over is reported, never guessed at.
5. **Per runner world:** create the world-level **Sparta verifier** (`task_id:null`, eval_config
   `5502d234...`), ensure `default_agent_ids` holds a **`sparta_external_agent`** (not a loop_agent),
   ensure the **SER-Heal remix** `45eb4adf` is present.
6. **Tasking AutoQC:** fork the source's qc_specs and port the tasking hook chain, remapping
   qc_spec ids in BOTH `hook_target_payload` AND `hook_source_predicate`.
7. **Builder AutoQC (the part everyone forgets):** the GWB world clones with **zero hooks**. Add
   the canonical 4-hook builder set (`Finalize After Publish`, `Sync After Publish`,
   `Pipeline AutoQC Completed` with its predicate remapped to the target's own forked `AutoQC`
   spec, `HelloWorld -> Send for Pipeline Fixes` whose `cprc_520906...` predicate is a SHARED
   canonical id copied verbatim). Without this, world building never finalizes or syncs and
   plan/spec AutoQC never advances.
8. **Campaign-LEVEL configs** via `PATCH /campaigns/{id}` (a partial merge, so `campaign_metadata`
   survives; there is no public create route for world-remix configs, `/world-remix` is GET-only):
   - **`world_remix_configs` -> `prometheus_sync` "Sync to External Storage"**, env-stamped to the
     target. This is the file to Taiga-storage sync, NOT the Prometheus grader Sparta drops.
     Without it, Sync to External Storage cannot fire and the world upload bot aborts, so the
     `Test_T_1` test and every world file replace are dead.
   - **`campaign_settings.pipeline_autoqc`**: enabled, the shared-canonical `cprc_c02f653e...`,
     `dimension_tags [world-quality, world-files]`, and **`spec_world_id` = the target's OWN GWB**.
     (Atria's is a known bug: it points at Abacus's GWB. Do not copy it.)
   - Plus `analytics_config`, `file_chat_enabled`, `qc_subrole_labels` to match the Abacus baseline.
9. **Verify** by re-reading from the API. Never report success off what the script meant to write.

## 5. What the verify pass asserts

Hook counts (22 per runner world, 4 builder hooks), builder predicates pointing at the target's own
specs, 9+ qc_specs including `AutoQC`, canonical names, env stamped, no foreign world refs,
`pipeline_autoqc.spec_world_id` equal to the target's own GWB, and `prometheus_sync` present on the
target env.

**Verifier presence is deliberately not asserted:** `GET /verifiers/world` under-reports, so a
clean read is not evidence. Step 5 reports the POST result, which is.

## 6. Manual validation (there is no world-file clone)

World FILES never clone. Do not auto-run. `Test_T_1` is the manual test bed: upload files to a
`Test_T_1` task, fire **Sync to External Storage**, then run the task. That exercises the runner,
AutoQC and heal without bringing the source's task files across.

## 7. LAST STEP, ALWAYS: put the campaign link in the Teams project

Campaign setup is NOT finished until the new Studio campaign is linked on the vertical's Mercor
Teams project. Nothing in this skill does it, and there is no `enable_project_integration` slug for
Studio, so **it is a manual step in the Teams UI and it is the one people forget.**

Report it explicitly at the end of every run, with both values filled in:

> Studio campaign `camp_<target>` is wired. **Now add its link to the Teams project**
> `https://team.mercor.com/company_AAABlLQjCsYYoXP4rsZKpY0y/projects/<proj_id>` so the project
> points at the campaign. This is manual and it is not done yet.

Do not report the campaign as done without this line, even when every check passed. A campaign that
works perfectly but is not linked looks finished and is not.

`talent_success_get_project_annotation_platform` would be the natural way to verify the link, but it
is **access-restricted** and returns `Access denied` for Ryu's account (confirmed 2026-07-29), so
the link cannot be confirmed through mercor-mcp. Check it by eye in the Teams UI and treat
"unverified" as not done.

## Hard-won gotchas (all baked into the engine)

- **`GET /worlds/` returns `{"worlds":[...]}`**, not a bare list, and it is a SUBSET of each world.
- **The UI clone suffixes world names** two different ways: `<name>- copy` and `<name> - Copy`.
  Match through the suffix, case-insensitively, then rename.
- **The Taiga env lives in more than one place, and the list of places keeps growing.** Re-stamping only
  `world_custom_fields` leaves every env-carrying REMIX on the old environment. Match `*_environment_id`
  by key across all remixes; do not trust a list of remix names.
- **AUDIT the verticals that already exist, not only the clone you are making.** This rule postdates
  Atria, and nobody went back, so Atria ran for weeks with `world_custom_fields.taiga_environment_id`
  correct on all 8 worlds and BOTH remixes wrong on all 6 that have them — 12 values, including the
  `[Live New Flow] Final Tasking World` every new writer world spawns from. Fixed 2026-07-30. Cadre is
  still entirely on Abacus's env at world level; it has no spawned worlds yet, which makes now the
  cheapest moment to fix it.
- **A wrong remix env does not fail loudly, it produces confident wrong answers.** On Atria it read as a
  PIPELINE fault, not a config one: Taiga reads for Atria tasks resolved into Abacus's environment, found
  nothing, and reported zero rollouts — which the advance sweep answers with a RE-DISPATCH. Live
  2026-07-30: `task_33deae46` had 10 finished trajectories that were Fable-blocked (restricted topic, must
  never be re-run) and `atria-advance` proposed re-running it, because the guard that detects blocked runs
  reads the FAILED rollouts and there were none visible. Wrong env → empty read → destructive advice.
- **Never carry the clone's inherited env forward, and never default it.** What a fresh clone
  carries is `[CLONE ME]`'s env. Every project needs its own; the engine aborts with the Loom link
  rather than guess.
- **qc_spec forks must be file/stdin based**, never through a shell variable: spec bodies contain
  control characters that corrupt a `$var` round trip and post a garbage predicate. The engine
  sends every body over `curl -d @-`.
- **Remap the hook PREDICATE, not just the payload**, else scrub and stage-advance hooks silently
  never fire.
- **SER-Heal (`45eb4adf`)**: the 2 heal hooks clone but the heal remix does not. Without it on every
  runner world the hooks are dead and auto-retry is off.
- **Builder GWB carries 0 hooks on a clone** (and on Abacus/Atria until fixed). Never skip step 7.
- **`GET /verifiers/world` under-reports.** Do not use it to decide presence.
- **Transport is curl, not urllib.** Studio's Cloudflare 403s non-browser user agents.
- **Existing verticals carry damage this skill will not touch.** Rampart has 46 qc_specs with 5
  names duplicated eight times over, 44 hooks on `test_t_1`, and no consensus world at all; Cadre
  points consensus at Vigil. The freshness guard refuses all of them on purpose. Repairing a live
  vertical is a separate job, not this one.

## Reversal

Additive throughout, except the world rename. To undo: delete created hooks
(`DELETE /hooks/{id}` returns 204), rename the worlds back, archive the campaign, or PATCH a
world's `task_remix_configs` to remove the heal remix.
