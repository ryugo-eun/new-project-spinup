# AutoQC hooks: the canonical set, and how this skill applies it

**Hooks are a separate `/hooks` entity.** Not a field on the world, not part of the world-config
clone bundle, and not inherited when the builder spawns a writer world. So a freshly cloned campaign
or a freshly spawned tasking world has the statuses and the remix configs but **zero hooks**: nothing
fires the AutoQC pipeline, tasks strand in "Running Task AutoQC", and QC never writes back to the
panel.

## The implementation rule

**A single cloned world must end up with the same hooks and configs a CAMPAIGN clone produces.**
So this skill does not carry its own hook logic. `wire_world.py` imports
`clone-sparta-campaign/clone_sparta_campaign.py` (the current engine, adopt mode 2026-07-29) and
calls its own `fork_campaign_specs()`, `port_hooks()` and `wire_runner_worlds()` against one target
world. If the campaign engine changes, this skill changes with it, by construction.

**The hook set is read LIVE** from the source campaign's `[Live New Flow] Final Tasking World`,
which is exactly what a campaign clone ports from. It is never read from a file. The old
`canonical_hooks.json` capture (Abacus, 2026-07-13) drifted to **18 of 22 hooks** and was deleted on
2026-07-29 along with `provision_hooks.py` and `insert_hooks.py`, which were the second and third
implementations of this same job.

```
export RLS_API_KEY=...                    # must reach BOTH campaigns
export SPARTA_SRC_CAMPAIGN=camp_...       # default: the [CLONE ME] template
python3 wire_world.py --campaign camp_TARGET --world world_TARGET            # dry run
python3 wire_world.py --campaign camp_TARGET --world world_TARGET --execute
python3 wire_world.py --campaign camp_TARGET --world world_TARGET --builder --execute
```

## HARD RULE: do not wire Prometheus

New Sparta campaigns are Sparta-chain only. Chain B (Prometheus) is the legacy backend; Vigil cut
over around 16-17 June 2026. Attaching the three Prometheus remixes to Abacus made the agent
**double-run** and made env-linters pull from a different environment, which engineers flagged.
`port_hooks(..., drop_prometheus=True)` drops any hook whose target remix is one of:

| Remix id | Prometheus hook |
|---|---|
| `04c87e48-f3d5-40b7-8375-7c1c3fc78284` | Taiga QA Finishes |
| `6652e121-4c2f-4669-9480-592148e2fc4a` | External Agent Finishes |
| `5aaaf11a-1857-41f2-9800-df3fc242a63c` | Running Agent Runner |

Verified live 2026-07-29: the `[CLONE ME]` tasking world carries **none of them**.

## The canonical 22, captured live

`GET /hooks/world/world_640451310b5140bbbc861140079e58d6` in
`camp_4040aadecd0544a6ab7f9a97780b809f` ([CLONE ME] Sparta Professionals Campaign), read
**2026-07-29**. Every hook was created 2026-07-22. This table is a **checklist to verify against**,
never a source to copy from: re-read the world.

| # | Hook name | On | Predicate | Fires | Enabled |
|---|---|---|---|---|---|
| 1 | Run Scrub File Metadata (Task AutoQC) | task_state_change | status `55cc7e0c` (Running Task AutoQC) | remix `2d97472f` (metadata scrub) | yes |
| 2 | Scrub Done → Run Task AutoQC (AQC) | remix_finished | remix `2d97472f` | autoqc **Task AutoQC** | yes |
| 3 | Run Task AutoQC (AQC) | task_state_change | status `55cc7e0c` | autoqc **Task AutoQC** | **no** |
| 4 | Task AutoQC Finishes | autoqc_finished | spec **Task AutoQC** | remix `02f101b5` (mark done) | yes, foreground |
| 5 | Run on Run Agent and QC | task_state_change | status `7cf3bb3e` (Running Agent Runner & QC) | remix `dfd1a1ce` (Sparta External Runner) | yes |
| 6 | Run on Agent Completion | remix_finished | remix `dfd1a1ce` | remix `4e2078da` (External QA Run) | yes |
| 7 | Run External Agent Finishes | remix_finished | remix `dfd1a1ce` | autoqc **Trajectory AutoQC** | yes |
| 8 | Run Trajectory AutoQC (AQC) | task_state_change | status `896ecc57` | autoqc **Trajectory AutoQC** | **no** |
| 9 | Run when Taiga Env Linter finishes | remix_finished | remix `4e2078da` | remix `2d46e4a7` | yes |
| 10 | Run on Agent Completion (SER Heal) | remix_finished | remix `45eb4adf` (SER-Heal) | remix `4e2078da` | yes |
| 11 | Run External Agent Finishes (SER Heal) | remix_finished | remix `45eb4adf` | autoqc **Trajectory AutoQC** | yes |
| 12 | Run Failure Analysis AutoQC (AQC) | task_state_change | status `f76bccb0` | autoqc **FA & Grader Analysis** | yes |
| 13 | Failure Analysis AutoQC Done | autoqc_finished | spec **FA & Grader Analysis** | remix `69e8f78b` | yes, foreground |
| 14 | Run Preference Labels AutoQC (AQC) | task_state_change | status `fa506399` | autoqc **Preference Labels** | yes |
| 15 | Preference Labels AutoQC Done | autoqc_finished | spec **Preference Labels** | remix `cf7828c6` | yes, foreground |
| 16 | Preference Labels Sync Done | remix_finished | remix `397f4a07` (Submit Preference Labels) | remix `cf7828c6` | yes |
| 17 | Auto-sync on ready for preference labels | task_state_change | status `c521d090` | remix `92bde9c8` | yes |
| 18 | Auto-sync on ready for preference labels | task_state_change | status `c521d090` | remix `a361c02b` | yes |
| 19 | Auto-sync on ready for delivery | task_state_change | status `ba9f81f7` | remix `a5cef9a0` (Send envlinter responses) | yes |
| 20 | Auto-sync on ready for delivery | task_state_change | status `ba9f81f7` | remix `397f4a07` (Submit Preference Labels) | yes |
| 21 | Auto-sync on ready for delivery | task_state_change | status `ba9f81f7` | remix `a361c02b` | yes |
| 22 | Auto-sync on ready for delivery | task_state_change | status `ba9f81f7` | remix `92bde9c8` | yes |

Notes on the table, so nothing here reads as more certain than it is:
- **Two hooks ship DISABLED** (#3 and #8). They are the non-scrub-gated variants of Task AutoQC and Trajectory AutoQC. Copy them **disabled**; enabling them double-fires QC.
- Remix names are given only where verified. `2d46e4a7`, `69e8f78b`, `cf7828c6`, `92bde9c8` and `a361c02b` are recorded by id only, because their display names have not been confirmed.
- **Six hooks share two names** (4x "Auto-sync on ready for delivery", 2x "...preference labels"), differing only in target remix. See the dedupe caveat below.
- The 2 SER-Heal hooks (#10, #11) gate on `sparta_external_runner_heal` (`45eb4adf`). `wire_runner_worlds()` attaches that remix, so they can fire. Rampart lacks it by design; that is not a bug.

## The qc_specs, verified live in the same campaign

qc_spec ids are **campaign-scoped**, so every port remaps them by NAME. The four the tasking hooks
fire, with the template campaign's ids:

| Spec name | Template id |
|---|---|
| Task AutoQC | `qcspec_3109b815b13ff294c8e0a17a` |
| Trajectory AutoQC | `qcspec_4ce87fd501203fe72042a941` |
| Failure Analysis & Grader Analysis AutoQC | `qcspec_384201bd8fbff182598aae7d` |
| Preference Labels AutoQC | `qcspec_416fba6ea9613d757513b9c4` |

The campaign carries **nine** campaign-scoped specs in total (the four above plus AutoQC, World
Files QC, Spec Document QC, Plan Document QC, Taiga QA Feedback AutoQC). `fork_campaign_specs()`
forks all of them by name and is idempotent, so a target that already has a spec of that name is
reused, not duplicated.

## The remaps `port_hooks()` applies

Per hook: keep only `hook_name`, `hook_enabled`, `hook_source_event`, `hook_source_predicate`,
`hook_target_event`, `hook_target_payload`, `hook_run_in_background`; set `world_id` to the target;
then

- remap `hook_target_payload.qc_spec_id` through the fork map;
- **remap `hook_source_predicate[].value` too. This is the number one gotcha.** Six of the 22 gate
  on a `qc_spec_id` or a `remix_id`. Remap only the payload and the hook silently never fires: QC
  runs and the task never advances, which is a confusing half-working state;
- **preserve `hook_enabled`** (see #3 and #8 above);
- **skip a hook whose target remix is absent** from the target world, because that create 400s;
- **drop the 3 Prometheus targets.**

Remix ids are mostly shared canonical across Sparta verticals and copy straight, with one known
exception: **scrub / `metadata_scrub`** is `e6512217…` on Panacea but
`2d97472f-c5a4-4722-adbf-657876bc01a7` everywhere else (Vigil, Abacus, Atria, the template).
Sourcing from Panacea means remapping scrub in both payload and predicate.

## Known caveat: dedupe is by hook NAME

`port_hooks()` skips a hook whose name already exists on the target. Six of the 22 share two names.
On a **fresh** world that is harmless: the existing-name set is read once, before anything is
created, so all 22 land. On a **re-run after a partial failure** it is not: one surviving
"Auto-sync on ready for delivery" makes it skip the other three, and the run reports "skipped"
rather than a gap. `wire_world.py` therefore verifies the final count against 22 and **exits
non-zero** if it is short, instead of printing success. Fixing the dedupe key itself (name plus
predicate plus target payload) belongs in the shared engine and has not been done.

## The chain, so you can sanity-check it

- Task enters "Running Task AutoQC" → `Run Scrub File Metadata` → on finish `Scrub Done → Run Task AutoQC` (predicate = the scrub remix id) invokes the **Task AutoQC** spec → `Task AutoQC Finishes` (predicate = that spec id) advances the stage.
- Task enters "Running Agent Runner & QC" → `Run on Run Agent and QC` fires the **Sparta External Runner** (`dfd1a1ce`).
- Runner finishes → `Run External Agent Finishes` invokes the **Trajectory AutoQC** spec, and `Run on Agent Completion` fires **External QA Run** (`4e2078da`), which dispatches the QC preset (env_linter, data_quality, claudescope, reward_hacking) and later pulls results into the panel.
- `start_task_autoqc_review`, `start_agent_run_review` and `run_agent_run` are **annotator or UI transitions with no hook**. A human or a cron fires them. The hooks drive the compute and the `…Finishes` transitions, not these.

## The builder set (4 hooks)

`[LIVE] Golden World Building` takes a different set: Finalize After Publish, Sync After Publish,
Pipeline AutoQC Completed, HelloWorld to Send for Pipeline Fixes. Identical across Panacea and
Vigil; its 3 remix ids (`0021c265`, `786f6e4f`, `bb8e90ff`) come with the clone. Run
`wire_world.py --builder`. **Do not mix the two sets.**

## Verify

- `GET /hooks/world/{target}` → **22** on a tasking world, **4** on the builder, no duplicates beyond the six intentional shared names, and the enabled flags mirroring the reference (2 disabled).
- Re-scan every predicate and payload for a leftover source-campaign qc_spec id or the Panacea scrub id. Must be zero.
- A live "Run External Agent" then confirms QC auto-dispatches (Datadog `service:rl-studio-remix` shows `4e2078da` firing on its own around when the run completes) and the panel populates.

## Gotchas

- **Remap the predicate, not just the payload.** The single most expensive mistake here.
- **qc_specs do not clone.** A fresh campaign has `{"specs": []}`; fork them or every `autoqc_invoke` hook fires against a spec that does not exist.
- **`GET /qc-specs` 307-redirects** to `http://` and strips auth. Call `/qc-specs/` with the trailing slash and `?campaign_id=`.
- **Remix configs are world-scoped.** Attach before hooking, and `PATCH` is full-replace of `task_remix_configs`: GET, append, assert, PATCH, verify.
- **Hooks are invisible to the SQL querier.** Read them only via `GET /hooks/world/{id}`.
- **Never wire from an empty reference.** `wire_world.py` aborts if the source world returns 0 hooks, because that means the wrong campaign, the wrong world, or a key that cannot read it.
- **A newly spawned writer world has the same gap.** Hooks do not inherit on spawn either, so re-run this on any new live tasking world until the Studio team folds hooks into their clone and spawn.
