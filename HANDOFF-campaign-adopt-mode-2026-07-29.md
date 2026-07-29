# Handoff: change `clone-sparta-campaign` to adopt a human-cloned campaign

## RESOLVED 2026-07-29, ~10:30am PT. Adopt mode is built, installed and mirrored.

Adopt is now the default mode; create-and-clone is behind `--mode create`. Dry run verified against
a real UI clone (`camp_77e47999`) and against Rampart. **The execute path has not been run yet**,
so the writes themselves are still unproven.

Four findings from live reads changed the design below, and two of them contradict it:

1. **Name matching as specified would have failed.** Cadre matched the canonical names exactly
   because Cadre was built by the ENGINE, not by a UI clone. A real UI clone suffixes every world:
   `[Live] Consensus Labeling- copy` on `camp_77e47999`, and ` - Copy` plus lowercase `test_t_1` on
   Rampart. Adopt matches through the suffix, then renames to canonical
   (`PATCH /worlds/{id}` with `world_name` returns 200, verified and reverted on the junk campaign).
2. **The hard abort on a missing world would have blocked the real cases.** Panacea, Vigil and
   Abacus have no `Test_T_1`; Rampart has no consensus world. Only GWB and tasking abort now.
3. **`[CLONE ME]` sends consensus labeling into Vigil.** Its tasking world's consensus remix
   `target_world_id` is `world_8c245e16...`, which is **Vigil's own** `[Live] Consensus Labeling`.
   Cadre inherited it. Name pairing cannot fix it because that id is not one of the four source
   worlds, so adopt repoints it explicitly.
4. **The Taiga env default was a foot-gun.** `SPARTA_TARGET_ENV_ID` defaulted to the shared Abacus
   env, so an adopt run on Rampart (which runs on `81d4c64c`) would have silently moved its runs to
   the wrong environment. Adopt now keeps an env the target already agrees on unless the operator
   sets the variable explicitly. The env also lives inside the QA_Results and Trigger Promo QC
   Report remixes, not just `world_custom_fields`, so it is re-stamped in both places.

## Scope narrowed, same session

Ryu: this only ever runs on a **new** campaign, never to repair an existing vertical. That reversed
two of the choices above:

- Findings 2 and 4 were solved for the wrong problem. **All four worlds are required again** (a
  fresh `[CLONE ME]` clone always has them, so a missing one means a botched clone), and the
  **Taiga env is always re-stamped to the operator's answer** rather than preserving what the
  campaign carried, because what a fresh clone carries is `[CLONE ME]`'s env, the very thing being
  corrected.
- Replaced with the guard that actually matters at this scope: **the target must be a fresh clone,
  zero hooks and zero qc_specs, else hard abort.** Without it, an operator could point the default
  mode at Panacea and it would rename worlds and patch campaign settings on a live 1022-world
  campaign. Verified: Panacea (4550 specs, 29 tasking hooks) and Rampart are both refused.
  `SPARTA_ALLOW_REWIRE=1` overrides, for resuming a run that died part way.
- Dropped the duplicate-spec and excess-hook warnings, which only mattered for adopting a mess.
- **The Taiga env now has NO default and is required.** Every project needs its own; the engine
  aborts and hands the operator Erick Chen's walkthrough
  (https://www.loom.com/share/d040799ec8ab43e9ac4aa39795fdce91) plus the source thread
  (https://64f4423488df355.slack.com/archives/C0BMAC5BX4G/p1785286576111299?thread_ts=1785286398.426639&cid=C0BMAC5BX4G).
  The old default was Abacus's env, which is how **Cadre ended up running on Abacus's env**.

Damage on existing verticals is therefore explicitly out of scope and left recorded, not fixed:
Rampart has 46 qc_specs with 5 names duplicated eight times over, 44 hooks on `test_t_1` and no
consensus world; Cadre points consensus at Vigil. Repairing a live vertical is a separate job.

Original design and premortem below, kept for the reasoning.

---

## What Ryu asked for

Change the flow. Today the skill creates the campaign and clones the four worlds itself.
Ryu wants: **the person clones from `[CLONE ME] Sparta Professionals Campaign` themselves, then
the skill writes in everything the clone leaves broken.**

## The blocker, verified

`clone_sparta_campaign.py` **always clones the four worlds**. `SPARTA_TARGET_CAMPAIGN` only
skips campaign *creation* (line 179 to 193); the world-clone loop at line 200 to 225 runs
unconditionally. Point it at an already-cloned campaign and you get **four duplicate worlds**.

The SKILL.md line "to resume onto a campaign that already exists, also export
`SPARTA_TARGET_CAMPAIGN=camp_...`" is misleading and should be corrected regardless of whether
adopt mode gets built.

## What makes adopt mode feasible

Read live from Cadre `camp_35e49895edea4ad7b822d8347dab6c4c` on 2026-07-29. A real cloned
campaign carries **exactly the four canonical worlds under their exact canonical names**:

| World | Cadre id |
|---|---|
| `[LIVE] Golden World Building` | `world_f68670e0b59d4a13b4658a3e1ed2a6ee` |
| `[Live New Flow] Final Tasking World` | `world_585c8fd8aff14903916f4a279d5b9735` |
| `Test_T_1` | `world_bd4558c95f7b4311b6632d6dedc0b8e2` |
| `[Live] Consensus Labeling` | `world_88e29da239c749d796fedfd28b210588` |

So **name matching is a sound adoption key.** The engine's existing `WORLDS_TO_CLONE` list
already uses these exact names.

Caveat: `GET /worlds/?campaign_id=` returns a SUBSET of each world. It does NOT include
`world_custom_fields`, `default_agent_ids` or `eval_configs`. Adopt mode must `GET /worlds/{id}`
per world to see the Taiga env, the agent and the file-sync pointer. Do not build the inventory
off the list endpoint alone.

## The three things that silently stop happening in adopt mode

These run *inside* the world-clone loop today, so removing the loop removes them. Each must
become its own explicit step or the campaign looks wired and is not.

1. **Taiga env re-stamp.** Line 218 to 222 sets `world_custom_fields.taiga_environment_id` to
   the target env on every cloned world. A UI clone will carry the SOURCE's env. Symptom: runs
   go to the wrong Taiga environment.
2. **Stripping `prometheus_*` runtime keys.** Line 219 drops them. A UI clone keeps the source's
   `prometheus_gcs_path`, so the runner mounts the SOURCE world's files. Symptom:
   `platform_has_environment=False`, empty or wrong trajectories. This is the nastiest one
   because everything else looks correct.
3. **The `src_to_new` map.** Built at line 224 while cloning, and the scrub pass at step 3
   depends on it to repoint `base_world_id` and any consensus `target_world_id`. In adopt mode
   there is no such map. **Rebuild it by pairing source world name to target world name**, which
   the finding above makes safe.

## Premortem: how adopt mode breaks

| Failure | Guard to build in |
|---|---|
| Duplicate worlds if someone runs the old path on a cloned campaign | **Refuse to clone if the target already has any of the four worlds.** Make this a hard abort, not a warning |
| A world is missing from the clone | Abort and list what IS present. Never wire a partial set |
| Two worlds share a canonical name | Abort. Ambiguous adoption is worse than no adoption |
| Names drift in a future Studio version | Fail loudly on no-match rather than falling back to fuzzy matching |
| Run twice, duplicate hooks or verifiers | `port_hooks` already skips existing. **Verifier creation does not** and needs a presence check that is not `GET /verifiers/world` (it under-reports). Prefer catching the POST result |
| Human cloned from something other than `[CLONE ME]` | Verify lineage before wiring: the tasking world should carry a `ready for delivery%` status and the source hook chain should be ~22 |
| Campaign-level configs absent | They never clone anyway, even from `[CLONE ME]`. Step 7 already handles this and is unchanged |

## Recommended shape

Make the engine's default mode **adopt**, and inventory before writing:

1. **Input:** target campaign id (already cloned by the human) plus the target Taiga env.
   No campaign name needed any more, and no `POST /campaigns/`.
2. **Inventory.** `GET /worlds/{id}` per world. Report a table: what is present, what is stale,
   what is missing. Show it before any write. This doubles as the fix for the fact that nothing
   currently tells you what a clone actually carried.
3. **Wire the gaps**, idempotently: env re-stamp, strip prometheus keys, scrub with the rebuilt
   name-paired map, verifier, `sparta_external_agent`, SER-Heal remix, tasking hooks and specs,
   the builder four-hook set, then the campaign-level configs.
4. **Verify** using the existing step 4 checks, unchanged.
5. **Report the Teams project link reminder** (already added as section 6, keep it).

Keep the old create-and-clone path behind an explicit flag rather than deleting it, in case the
UI clone is ever unavailable.

## State of everything else, 2026-07-29

Done this session, all installed in `~/.claude/skills` and mirrored to
`new-project-spinup/skills/` (16 spinup skills, byte-identical, verified):

- `provision-vertical-automations` (new)
- `verify-vertical-spinup` (new)
- `sweep-canvas-links` (new)
- `clone-sparta-campaign` gained section 6, the Teams campaign-link reminder

Live fixes, all drafts, none activated:

- Cadre bonus guard 2 repointed to its own id, 9:12am PT
- Atria bonus guard 2 installed, 9:18am PT
- Rampart bonus guard 2 installed, 9:19am PT

Decisions taken this session:

- Canonical automation set is **7**, not 10. Onboarding emails and the 48hr stalled-task
  reminder are explicitly out of scope.
- Canvas instructions link points at the **per-vertical Google Doc**, not the Instructions Hub.
- Canvases should gain a Studio access block; Panacea's proven form is the bare root plus the
  Okta route plus "Chrome, not Safari". No campaign-scoped Studio landing URL is known to exist.

## Next up after this

The **Teams new project spinup skill**, which is the largest remaining gap in the playbook:
project, roles, listing, auto-provision email (ships OFF, every live vertical needs it ON),
owner, test contract. Not started.

## Known and still unfixed

- `new-project-spinup/skills/` is **not backed up**. Not a git repo, no parent repo. One disk
  loss takes all 16 spinup skills.
- `clone-sparta-campaign/SKILL.md` has em dashes in its pre-2026-07-29 sections.
- Bonus amounts and both hour ladders are Abacus's numbers on every other vertical, unconfirmed.
