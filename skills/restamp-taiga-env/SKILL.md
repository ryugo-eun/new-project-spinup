---
name: restamp-taiga-env
description: >-
  Change the Taiga environment id everywhere in an RL Studio campaign, in one pass. The env id is
  not one field: it lives in every world's custom fields, inside two task remixes per runner world,
  and in the campaign's Sync to External Storage remix, and changing only the obvious one leaves
  runs pointed at the old environment while every UI surface looks correct. Also strips the file
  sync pointers, which point into the OLD env's storage bucket and would make the runner mount a
  volume that does not exist. Inventories first, dry-run by default, backs up every object, verifies
  by re-reading, and can roll the whole thing back. Use for "point <vertical> at its own Taiga env",
  "flip the env back to Abacus to test", "the trajectories run against the wrong environment",
  "give this campaign a new Taiga env", "which env is <vertical> on".
metadata:
  author: ryugo-eun
  outbound_writes: true
---

# Re-stamp a campaign's Taiga environment

Script: `restamp_taiga_env.py` (Python 3, stdlib only, curl transport, dry-run by default).

Every project needs its **own** Taiga environment. Reusing another vertical's sends this
vertical's runs into that vertical's environment. This skill is how the id gets changed, whether
that is giving a new vertical its own env for the first time, correcting a vertical that inherited
one from a clone, or deliberately flipping a vertical onto a known-good env as a diagnostic.

## The whole point: the id is in more than one place

Measured live on Delphi 2026-07-31, and the same shape holds on Abacus, Vigil and Cadre.

| Where | Path | Count on a 5-world campaign |
|---|---|---|
| Every world | `world_custom_fields.taiga_environment_id` | 5, one per world |
| Runner worlds' remixes | `task_remix_configs[*].remix_world_field_values.taiga_environment_id` | 2 per world that has them (QA_Results, Trigger Promo QC Report) |
| The campaign | `world_remix_configs[*].world_remix_world_field_values.prometheus_environment_id` | 1, the Sync to External Storage remix |

Delphi came to 12 references. **Change only `world_custom_fields` and the remixes still fire into
the old environment**, which is the failure this skill exists to prevent: Studio shows the new env
on the world, and the run goes somewhere else.

The remix indexes are NOT stable across worlds (they were 14/15 on the runner worlds and 15/16 on
the hand-built sample world), so never write them by index. The script matches on any key ending
in `environment_id`, at any depth, and only when the current value is exactly the `--from` id.

## Flipping the env invalidates the file sync

`world_custom_fields.prometheus_gcs_path` looks like:

```
gs://.../biome/environment_files/<ENV_ID>/prometheus_clean/<world_id>/<timestamp>/world
```

The env id is **in the path**. After a flip, that path points into the old environment's bucket,
so the runner mounts a volume that does not exist in the new one. The symptom is empty or missing
trajectories, with every config looking correct, and it is the nastiest defect in this area.

So by default the script **strips all `prometheus_*` sync keys** on any world whose env it changed
(there were 14 on Delphi's `Test_T_1`). That converts a silent wrong-volume mount into a loud
"nothing synced". **Sync to External Storage has to be re-run afterwards**, on the world being
tested, before any trajectory run means anything. `--keep-sync` opts out, and is almost always
wrong.

## Run it

```bash
set -a; . ~/Desktop/MERCOR/.env.local; set +a     # RLS_API_KEY, write-scoped

# 1. what is it on now
python restamp_taiga_env.py --campaign camp_xxx --inventory

# 2. what would change
python restamp_taiga_env.py --campaign camp_xxx --to <new-env-uuid> --dry-run

# 3. do it (backs up, patches, then re-reads to verify)
python restamp_taiga_env.py --campaign camp_xxx --to <new-env-uuid> --execute

# 4. undo, exactly
python restamp_taiga_env.py --campaign camp_xxx --restore taiga_env_backup_camp_xxx_<stamp>.json --execute
```

`--campaign` is required and has **no default**, so the script cannot be pointed at the wrong
campaign by forgetting a flag.

`--from` is inferred when the campaign holds exactly one env id. When it holds more than one the
script **aborts and prints the counts** rather than guessing. Abacus, for example, is 72 references
on its own env plus 5 on a different one, so it needs `--from` given explicitly, once per id.

## Guardrails, and why each is there

- **Reads everything before it writes anything.** A world that fails to GET aborts the run rather
  than producing a half-stamped campaign.
- **Backup before the first PATCH.** Every world's `world_custom_fields` and `task_remix_configs`
  plus the campaign's `world_remix_configs`, as they were. `--restore` replays it verbatim.
- **Partial-write reporting.** If a PATCH fails mid-run it says how many worlds were written and
  prints the exact `--restore` command. This is not theoretical: a read-only key gets 403 on the
  first PATCH.
- **Verifies by re-reading.** After writing it re-inventories and asserts zero remaining references
  to the old id. It reports its own failure rather than claiming success.
- **Touches only `*environment_id` keys.** Not a blanket string replace, so an env id that appears
  inside some other value cannot be clobbered by accident.
- **Covers every world in the campaign, canonical or not.** The `clone-sparta-campaign` adopt path
  only knows the 4 canonical worlds, so it silently skips hand-built ones. On Delphi that would
  have left 3 of the 12 references on the old env.

## Key scope, checked 2026-07-31

Write access is the thing that bites. Verified against Delphi:

| Key | Result |
|---|---|
| `~/Desktop/MERCOR/.env.local` `RLS_API_KEY` | **works, read + write** |
| `~/Desktop/MERCOR/SVA/.env.local` `RLS_API_KEY` | reads fine, 403 on PATCH: `This API key has 'read' access; this endpoint requires 'write'` |
| `panacea-cli/.env`, `panacea-cli/studio-rls.env`, `panacea-workspace/.env` | 403 on GET, campaign-scoped elsewhere |
| `Sparta Verticals/Studio Bulk Updates/studio_write_key.env` | 401, expired |

## Known env ids

| Vertical | Taiga env |
|---|---|
| Abacus | `2a931db7-ee3f-42d4-8125-9ff4361ed755` |
| Rampart | `81d4c64c-aa1b-482f-9a2f-7a8db14fdcb7` |
| Delphi | `908203df-f23e-4b12-8934-c91a53d3ca6e` |
| Cadre | still on **Abacus's**, which is a defect |

Creating a new one is not scriptable: Erick Chen's walkthrough,
https://www.loom.com/share/d040799ec8ab43e9ac4aa39795fdce91

## The diagnostic use

Flipping a new vertical onto a **known-good** env (Abacus's) isolates the fault. If trajectories
flow there, every other campaign config is proven correct and the problem is the vertical's own
environment. If they still do not flow, the env was never the issue. Flip back with `--restore`,
or by running `--to` in the other direction, once the question is answered.

Done on Delphi 2026-07-31 6:11pm PT: 12 references moved `908203df` to `2a931db7`, verified live.

## Related

- `clone-sparta-campaign` stamps the env as part of wiring a fresh clone. Use that one during a
  spinup. Use this one for any later change, and for any campaign with non-canonical worlds.
- `sync-to-external-storage` is the follow-up step this skill's output tells you to run.
