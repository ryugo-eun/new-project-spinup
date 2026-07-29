---
name: clone-vertical-automations
description: >
  Replicate a Sparta vertical's Teams-platform automations (the "Actions/Integrations" tab)
  onto another vertical, repointing every project/world/campaign/tag/job-title reference so
  they act on the target, not the source. Use for "copy the automations from <A> to <B>",
  "replicate <vertical>'s actions on <new vertical>", "clone the integrations-tab automations".
  Creates DRAFTS only; a human activates them.
---

# Clone Vertical Automations (Teams-platform Actions)

Copies the automations on one Sparta vertical's project (Teams platform → project →
**Integrations** tab) onto a target vertical, remapping all vertical-scoped ids. The canonical
source set is the Atria/Abacus vertical (6 automations). This is the Teams-automations step of
a new-vertical spinup; Studio worlds/hooks and Drive folders are separate skills
(`clone-sparta-campaign`, `new-vertical-drive-folder`).

## Golden rule

An automation is NOT self-contained. Its `body` and `sql` embed the source vertical's project
id, Studio world ids, campaign id, team-tag ids, and job title. Copied verbatim it acts on the
SOURCE. You must resolve the target's equivalents and substitute every one. **Always create as
DRAFT** and hand back for review; never activate.

## Inputs to collect

- **SOURCE project id** (`proj_...`) — the vertical to copy from (default Atria
  `proj_AAABn3FoIuB1-06gfllLl4Nq`).
- **TARGET project id** (`proj_...`) — the new vertical (from its Teams Integrations-tab URL).
- Company = Sparta `company_AAABlLQjCsYYoXP4rsZKpY0y` (same for all Sparta verticals).

## Step 1 — read the source automations

`list_automations(project_id=SOURCE, company_id=Sparta)` → for each, `get_automation(id)` to
get full `sql`, `body`, `trigger_config`, `handler_name`, `notes`. The canonical 6 (handlers):
1. Grant Onboarding + Active Writer on contract active — `tags`, EVENT `contract.status_change` toValue=active
2. Assign Pod A on World Created — `tags`, cron (WB world, status `98680cd3-...`)
3. Grant completed_work_trial — `tags`, EVENT `studio.task.status_change` on `taskStatusName='World Created'`. **Every vertical currently fires on World Created** (Abacus, Atria, Rampart all verified 2026-07-28). **Whether that is the RIGHT milestone is UNDECIDED** — Ryu, 2026-07-28. Abacus's NAME says 'first task Ready for Delivery' and the playbook's Step 5 repeats that, but nothing implements it. Rule: **name the clone for what it actually does** ('on first World Created') and carry the open question forward rather than resolving it in the name.
4. Bump hours 2→10 on spec doc approved — `update_hours`, cron (WB world, status `planning_done_pipeline`)
5. Bump hours 10→40 on first RFD — `update_hours`, cron (RFD-by-name across non-WB worlds)
6. Onboarding Complete Bonus $800 — `bonus`, cron (WB world, status `planning_done_pipeline`)

## Step 2 — resolve the TARGET's identifiers

| What | How to get it |
|---|---|
| Project id | given (TARGET) |
| Job/role title | `get_project(TARGET, include=['roles'])` → `role_title` (e.g. Atria `Healthcare Admin Expert`, Rampart `Insurance Expert`) |
| Studio campaign id | `studio GET /campaigns/` (headers `X-Company-Id: comp_2fa4115109d741cd94a3c409ed89e61f`, `X-Account-Id: acct_be8f7fcc2c554b33baa5a0c9d05496e3`) → find the campaign by vertical name. Output is huge — save to file and `jq` for the name. |
| WB golden world + tasking world ids | `studio GET /worlds/?campaign_id=<TARGET camp>` (same headers + `X-Campaign-Id`). WB = "[LIVE] Golden World Building..."; tasking = "[Live New Flow] Final Tasking World...". |
| Onboarding / Active Writer / Pod A tag ids | **Use the target's DEDICATED vertical-prefixed tags.** Read their ids out of `list_project_audiences(TARGET)` anchors, which is the reliable source (`list_tags` caps at 200 rows for Sparta). **Do NOT call `create_tags` with bare names** — it is idempotent on (company, name), so a bare `Onboarding` returns the EXISTING shared company tag (`created:false`) and the automation then acts across verticals. This is not hypothetical: Panacea and Rampart both have ACTIVE automations granting the same shared `tags_AAABnYiHKEtdOhtigt1IUIft`, found 2026-07-28. If the target has no prefixed tags yet, run `provision-vertical-teams-integrations` first. |
| completed_work_trial tag | **Use the target's OWN `<vertical>_completed_work_trial` tag, never the shared `tags_AAABn05fDkO2qNlPVB5HDoFI`.** Sharing it merges the verticals' work-trial rosters, which gate the Writer Calendar and the active roster. Abacus, Atria and Rampart all still point at the shared one (drafts); Cadre correctly uses its own. |
| Status ids (`98680cd3` World Created, `ba9f81f7` RFD, `planning_done_pipeline`) | **UNCHANGED** — shared across the Abacus clone lineage. VERIFY: the `/worlds/` response for the tasking world should list `ba9f81f7-...` in its Review custom-view filters. If absent, the target is NOT same-lineage — STOP and resolve real status ids before proceeding. |

## Step 3 — substitute and create each as a draft

In every `sql` and `body`, replace SOURCE→TARGET for: project id, `j.TITLE IN ('<source title>')`
→ target title, WB world id, tasking world id, campaign id, and the three team-tag ids. Leave
status ids, `companyId`, and the `${...}` placeholders alone. Then `create_automation` with:
- `project_id=TARGET`, `company_id=Sparta`, `name` = source name with the vertical prefix swapped.
- `trigger_config`: for EVENT automations use `{"type":"event","triggerType":"contract.status_change","params":{...}}` — note **`triggerType`** (camelCase) on create, even though `get_automation` echoes it back as `trigger_type`.
- cron automations: `source_type:"snowflake"` + `sql`. Event automations: OMIT `source_type`/`sql`.
- `handler_name`, `body` (substituted), `notes` (carry the source note + "replicated <date> from <source auto id>", flag reused shared tags + UNCONFIRMED amounts), `description`.
- `evidence`: `tag` for tag handlers, `update_hours` for hours, `payout` (with `formula` + `valueCents`) for bonus.
- Event automation #1: set `idempotency_enabled:true`, `idempotency_recipient_keys:["contractorId"]`.
- `create_automation` always returns state `draft`. A `"SQL returned 0 rows"` warning is EXPECTED on a fresh vertical (no writers/tasks yet) — not an error.

**`update_automation` trap:** its `evidence` is a discriminated union, so it REQUIRES a `kind` field (`tag` / `update_hours` / `payout`) or it fails with `union_tag_not_found`. `create_automation` infers it; update does not.

**`create_automation` validation traps, all hit on the Cadre run 2026-07-28:**
- **A `tags` body REQUIRES `contractorId`.** The Abacus completed_work_trial source omits it, so that automation could never have run on Abacus either. Rampart's copy has the same defect. Add `"contractorId": "${contractorId}"`.
- **`studio.task.status_change` exposes NO `${contractorId}`.** Its fields are `campaignId, createdByEmail/Name/UserId, jobId, ownedByEmail/Name/UserId, previousStatusId/Name, projectId, qualifiesDone, taskId/Name/StatusId/StatusName/TagIds/Url, transitionedAt/ByEmail/ByName/ByUserId, version, worldId/Name`. Use `${createdByUserId}`, the task AUTHOR, which is the writer — not the transitioner.
- **Payout evidence takes `formula` and `valueCents` FLAT on `evidence`**, alongside `rationale`/`variables`/`kind`. Nesting them under an `evidence.payout` object is rejected with `extra_forbidden`.
- **The evidence judge rejects thin rationales on `tags` handlers.** State explicitly that `${jobId}`/`${contractorId}` are template placeholders resolved per recipient, that recipients come from the substituted target-scoped SQL, and that the automation is created as a draft.
- **Leak-check before sending.** Assert the substituted `sql`, `body` and `trigger_config` contain no source-vertical fragment (project id, campaign id, world id, job title, tag ids). Do NOT leak-check `notes`, which legitimately names the source for provenance. `Abacus` also survives inside SQL comments; swap it in prose since no Snowflake object name contains it.

## Step 4 — hand back

Report the 6 new ids + link `https://team.mercor.com/<company>/projects/<TARGET>?tab=integrations`.
Flag before activation: (a) UNCONFIRMED $ and hour ladders (bonus $800, 2→10, 10→40) — confirm the
target vertical's real numbers; (b) the bonus needs its self-ID dedup guard added; (c) whether the
reused shared tags should be swapped for dedicated ones. Do NOT activate — the operator does that in the UI.

## Reference — first real run (Rampart ← Atria, 2026-07-23)

- Source Atria `proj_AAABn3FoIuB1-06gfllLl4Nq`; target Rampart `proj_AAABn4DXkl4vJRwM1aBAzZi7`.
- Rampart: title `Insurance Expert`; campaign `camp_596be6524ff340dba995563562d4ec41`;
  WB world `world_83dcee872482470b84943a7cd8c49bb3`; tasking world `world_84be26debbe146be880e04cbbc2b77c0`.
- Tags used (all returned existing/shared, not dedicated): Onboarding `tags_AAABnZflw34wRQLVfGVEa7yt`,
  Active Writer `tags_AAABnYiHKEtdOhtigt1IUIft`, Pod A `tags_AAABnrTml_cT7vtGQh1N05q1`.
- New draft ids: `auto_AAABn40grBa_GSbm8pJNgIuV`, `auto_AAABn40g6WC87yjAjzZGXrPI`,
  `auto_AAABn40hKF7kPyNYaaJMtYA8`, `auto_AAABn40haPSKnmqZ3RpG3okj`, `auto_AAABn40h5aCElBaU1YRK2rdo`,
  `auto_AAABn40jP2qeKZOWQsJBqJRr`.
