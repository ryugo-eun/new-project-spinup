---
name: create-smoke-test-task
description: >-
  Create and run the canonical Sparta smoke-test task on a campaign's Test_T_1 world, to prove the
  campaign can actually run a task end to end: the task reaches the runner, the world files mount
  in the container, and a trajectory comes back completed. Ships the fixed 52-file fixture bundle
  and the fixed prompt, identical on every vertical, so the campaign under test is the only
  variable. Preflights the world first, and its verdict requires proof from the container's own
  output that the files mounted, because a run against an empty volume also completes. Use for
  "run the smoke test on <vertical>", "create the smoke test task", "is the pipeline actually
  working", "prove the campaign runs", "the trajectory is not flowing".
metadata:
  author: ryugo-eun
  outbound_writes: true
---

# The Sparta smoke test

Script: `create_smoke_test_task.py` (Python 3, stdlib only, curl transport).
Fixture: `fixture/world_files.zip` (52 files) and `fixture/task.json` (the prompt).

A newly wired campaign looks finished long before it can run anything. The smoke test answers one
question and no others:

> Does a task written in this campaign reach the runner, mount its world files, and come back with
> a completed trajectory?

Everything about the test is held fixed: the same 52 accounting files, the same prompt, on every
vertical. That is the whole design. If the fixture varied per vertical, a failure would be
ambiguous between the campaign and the task. Held fixed, **a failure is always the campaign**.

## Run it

```bash
set -a; . ~/Desktop/MERCOR/.env.local; set +a          # RLS_API_KEY, write-scoped

python create_smoke_test_task.py --campaign camp_xxx --all
```

`--all` runs preflight, files, sync, task, run, watch, in that order, and exits non-zero on a
failed verdict. Each phase also runs alone:

| Flag | Does |
|---|---|
| `--preflight` | read-only. Every reason a task can fail to reach the runner |
| `--files` | upload the 52-file fixture bundle to the world snapshot |
| `--sync` | fire Sync to External Storage, wait for the stamp to advance |
| `--create-task` | seed the task (`--reuse-task` to reuse today's instead) |
| `--run` | fire the Sparta External Runner remix |
| `--watch` | poll trajectories and give the verdict (`--task task_xxx` to watch an old one) |

It resolves `Test_T_1` by name inside the campaign and refuses to guess. That is the guard that
keeps a smoke test out of a world real writers work in. `--world` overrides it and warns.

## The verdict is real

PASS requires **both**:

1. a trajectory in `completed`, and
2. a fixture filename appearing in that trajectory's own **tool output**, which is the container
   saying it listed the file.

Condition 2 exists because a run against an empty or wrong volume also returns 200 and also
completes. That is the exact failure this test is for, and a status-only check would call it green.

## What preflight checks, and what each failure means

| Check | If it fails |
|---|---|
| world not locked / new tasks allowed | `world_settings` blocks the import; nothing can be seeded |
| `taiga_environment_id` set | runs have no environment. See `restamp-taiga-env` |
| default agent is `sparta_external_agent` | a clone left a `loop_agent`; runner errors `no_sparta_external_agent` |
| Sparta External Runner remix present | nothing to fire. The campaign was never wired |
| hooks attached | **zero hooks means the task strands in "Running Task AutoQC" and never reaches the runner.** The most common dead smoke test. See `clone-studio-world` |
| campaign has Sync to External Storage | the file sync cannot fire |

Two things are deliberately reported rather than failed on:

- **World-level verifiers.** `GET /verifiers/world/{id}` under-reports, documented in
  `clone-sparta-campaign` and confirmed on Delphi, whose runner works fine while the endpoint
  returns a count that does not match. A hit proves presence; a miss proves nothing.
- **The sync stamp.** See below.

## Sync to External Storage is required, always

The runner mounts what that step copied into the environment's storage. Skip it, or run it against
a pointer left behind by a previous environment, and the container comes up with an empty or wrong
volume. So this skill **aborts** if the sync stamp does not advance, rather than continuing: a run
on an empty volume still returns 200 and still completes, so proceeding would hand you a green
result that means nothing.

Whenever the environment changes, the sync has to be re-run before the next test, because the copy
lands per environment.

A note on how this section got written, since it is a trap worth marking: on 2026-07-31 the world
carried no `prometheus_*` keys at run time (they had been stripped an hour earlier during an env
re-stamp) and the run still mounted all 52 files, which was briefly read as proof the sync is
optional. It is not proof. The world's own `updated_at` and the container's file timestamps both
sit in the two minutes before the run, which is what a sync firing right beforehand looks like.
**Absence of those keys is not evidence that no sync ran.** Do not infer the sync was skipped from
a missing pointer.

Result on Delphi 2026-07-31: 9 completed trajectories, all 52 files mounted, on Abacus's Taiga env.

## Endpoints, all verified live 2026-07-31

| Step | Call |
|---|---|
| world files, current | `GET /snapshots/world/{world_id}` |
| world files, replace | `POST /snapshots/world/{world_id}/update`, multipart, field `files`, multipart filename = target path, no Content-Type header |
| backup bytes | `GET /worlds/{world_id}/download-zip` returns a presigned url |
| sync config | `GET /world-remix/campaign/{campaign}/configs`, take `world_remix_implementation_id == "prometheus_sync"` |
| fire sync | `POST /world-remix/world/{world_id}/remix` `{world_remix_config_id}` |
| task schema | `GET /worlds/{world_id}/task-import-schema` |
| create task | `POST /worlds/{world_id}/import-tasks` `{"tasks":[BulkImportTask]}` |
| fire runner | `POST /task-remix/{task_id}/in-place` `{"remix_config_id", "remix_runtime_field_values": null}` |
| trajectories | SQL querier, `POST /querier/unstructured`. There is **no `hooks` table** ("not available for querying"), so hooks come from `GET /hooks/world/{id}` |

## Gotchas

- **Existing world files are not overwritten.** If the world already carries files the upload is
  skipped unless `--replace-files` is passed. A smoke test must never quietly destroy a world's
  content.
- **Import is all or nothing** and rate-limited to 5 requests a minute.
- **Duplicate smoke tasks** are allowed but announced. `--reuse-task` reuses the newest instead.
- The task lands in the world's first status (`Task Writing`); you cannot set the status on import.

## Related

- `restamp-taiga-env` when preflight shows the wrong or a missing environment
- `clone-studio-world` for the hooks, verifier and default agent
- `clone-sparta-campaign` for a campaign that was never wired at all
