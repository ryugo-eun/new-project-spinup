---
name: port-vertical-dashboards
description: >-
  Copy a Sparta vertical's RL Studio dashboards (saved-SQL custom query views) onto another
  vertical, repointing campaign and world ids. Use when a vertical has no Studio dashboards.
metadata:
  author: ryugo-eun
  outbound_writes: true
---

# Port a vertical's Studio dashboards onto another vertical

You are the operator standing up a new Sparta vertical's Studio surface. A cloned campaign
brings its worlds, statuses and automations, but it brings **no dashboards**, so the vertical's
reviewers open Studio and see an empty sidebar while the source vertical has a full
pipeline-stage set. This skill copies that set over and repoints everything vertical-specific.

Script: `port_vertical_dashboards.py` (Python 3, stdlib only, dry-run by default).

## What a Studio "dashboard" actually is

A **custom query view** (`cqview`): one saved SQL query rendered as a table, stored per
campaign. The canonical set is one view per pipeline stage (Task Writing, Task AutoQC Review,
Failure Analysis, Preference Labels, In First Human Review, Ready For Delivery, Delivered, In
QC …) plus a few stall-catchers (`> 1 hour in Running Trajectories`, `AutoQC >1 hour`, `Held in
First Review (by reviewer)`).

Do not confuse it with two other things that also get called dashboards:

| Thing | Where it lives | Can you copy it? |
| --- | --- | --- |
| **Custom query view** | per campaign, `/campaigns/{id}/custom-query-views` | Yes, this skill |
| `customer_views` | React components in the rl-studio repo, attached via `workspace_settings.customer_views` | No, code change |
| Hex project | Hex workspace, separate SQL | No, duplicate in the Hex UI |

## Endpoints

| Operation | Method | Path |
| --- | --- | --- |
| List a campaign's views | GET | `/campaigns/{campaign_id}/custom-query-views` |
| Replace a campaign's views | PUT | `/campaigns/{campaign_id}/custom-query-views` |

There is **no create-one and no delete-one route.** Both facts below follow from that, and
both can silently destroy a vertical's dashboards if you miss them.

- **PUT replaces the campaign's ENTIRE set.** The body is `{custom_query_views_config: [...]}`
  and whatever you send becomes the campaign's whole set. Send the complete desired final
  state, never a delta. The script prints anything the replace would delete before writing.
- **GET is filtered by the caller's role.** A `campaign_admin` sees every view; anyone else
  sees only what passes `conditional_render_filter`. Read the source set as an admin or you
  will copy a truncated set and then overwrite the target with it.

## Run order

```bash
set -a; . ~/Desktop/MERCOR/.env.local; set +a     # RLS_API_KEY, never echoed

# 1. what does the source have, and what does the target have to lose?
port_vertical_dashboards.py list <source_campaign_id>
port_vertical_dashboards.py list <target_campaign_id>

# 2. dry run. Read the output, especially the DELETED warning and the world-scoped line.
port_vertical_dashboards.py port <source_campaign_id> <target_campaign_id> <target_name>

# 3. write
port_vertical_dashboards.py port <source_campaign_id> <target_campaign_id> <target_name> --apply
```

`list` labels each view `admin-only` / `role-gated` and `tight-excl` / `LOOSE-EXCL` /
`world-scoped`, so it doubles as an audit of a vertical that already has views.

## What gets repointed, and what is a verbatim clone

Task status ids are shared across every Sparta vertical, so the great majority of a view
ports byte-for-byte. Only three things carry source-specific values:

1. **In-SQL campaign id.** Views that join `iam_roles_campaign` to show an owner's subrole
   hardcode the campaign id. The script rewrites every occurrence.
2. **A world-scoped view.** A view filtering `world_id = '...'` (the Pipeline Fixes view) is
   repointed at the target's own `[LIVE] Golden World Building`. See the gate below.
3. **Descriptions naming the source vertical.** These render in the target's UI, so leaving
   them is a visible defect. The script rewrites them.

The script refuses to PUT if any source reference survives the transform, so a missed case
fails loudly instead of shipping a dashboard that reads another vertical's data.

## The world-scoped gate

A view pinned to one `world_id` cannot be ported blind: point it at a world that lacks the
status it filters on and it renders an empty table forever, which looks like "no work in this
stage" rather than "this dashboard is broken". So before repointing, the script requires that
the target's `[LIVE] Golden World Building` world exists **and** that its
`status_config.status_defns` actually contains the status id the SQL filters on. If either
check fails it **skips that one view** and ports the rest.

When you see the skip:

- **Target has no `[LIVE] Golden World Building`** — expected on a vertical whose Studio
  campaign is not fully wired yet. Finish the campaign wiring (see `clone-sparta-campaign`),
  then re-run; the port is idempotent.
- **World exists but lacks the status** — the world was built from a different template. Fix
  the world's `status_config` first (see `studio-world-config`), or leave the view off.

A world-scoped view needs no world-name exclusions, because a single world id is stricter than
any name filter. Do not "fix" it by adding them.

## World-name exclusions

Every non-world-scoped view should exclude test and staging worlds with the four-clause filter:

```sql
AND w.world_name NOT ILIKE '%test%'
AND w.world_name NOT ILIKE '%golden%'
AND w.world_name NOT ILIKE '[LIVE]%'
AND w.world_name NOT ILIKE '[OLD]%'
```

Hand-made views often carry a looser hardcoded list instead (`NOT IN ('golden_world_MAV', …)`),
which lets new test worlds leak into a reviewer's queue. `list` flags those as `LOOSE-EXCL`;
porting over them is the fix.

## Visibility

`conditional_render_filter` decides who sees a view. **A null filter means ADMIN-ONLY, not
"everyone"** — this reads backwards and is easy to get wrong when explaining the change to
someone. A vertical whose views are all null-filtered shows its reviewers nothing, which is
indistinguishable from having no views at all. Porting a source set that gates on
`subrole_preset_reviewer` is usually what actually makes dashboards appear for the people who
need them.

## Verify with data, not just config

A clean write only proves the config landed. Confirm at least the world-scoped view resolves
against real rows, because that is the one whose scope you changed:

```sql
SELECT count(*) AS n FROM tasks
WHERE world_id = '<target golden world id>'
  AND task_status_id = '<status the view filters on>'
  AND archived_at IS NULL
LIMIT 1
```

Run it through `POST /querier/unstructured` with the target's headers. Zero is not
automatically wrong, but on a vertical with active work it means look again.

## Gotchas

- World statuses live at `status_config.status_defns`, **not** `.statuses`. Reading the wrong
  key returns an empty list, which looks exactly like a world with no statuses.
- `GET /worlds/` requires a `?campaign_id=` query param, and its response is not reliably a
  bare array. The script accepts the wrapped shapes.
- `GET /worlds/{id}` returns **403** for a world outside the campaign in your headers, not 404.
  A 403 here means wrong campaign, not missing permissions.
- Omit `created_at` / `updated_at` / `created_by` / `updated_by` from the payload; the server
  stamps them, and sending them makes diffs unreadable.
- `cqview_id` is yours to choose. Use `cqview_<vertical>_<slug>` so a re-run overwrites rather
  than duplicating, and so a stray id immediately shows which vertical it came from.

## Related

- `clone-sparta-campaign` — wire the campaign these dashboards read from.
- `studio-world-config` — fix a world's `status_config` when the world-scoped gate fails.
- `verify-vertical-spinup` — the read-only audit that should report dashboards as present.
