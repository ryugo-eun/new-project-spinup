---
name: provision-vertical-automations
description: >
  Author the canonical Sparta launch automation set on a new vertical from parameterized
  templates (not by cloning another vertical's live automations), confirm every comp number
  with the operator instead of inheriting it, install the self-ID dedup guard that clones
  keep dropping, and finish with a verification pass that reports what is actually active
  versus draft. Use during a new-vertical spinup, or for "set up the automations for
  <vertical>", "author the canonical automations", "which automations is <vertical> missing",
  "verify the automations on <vertical>". For copying one vertical's set onto another, use
  `clone-vertical-automations`; this skill exists because cloning keeps leaking source ids.
---

# Provision Vertical Automations (canonical set, authored fresh)

Stands up a new Sparta vertical's Teams-platform automations (project to **Integrations**
tab) from templates that carry no other vertical's identifiers, then verifies. Every
automation is created as a **DRAFT**. A human activates in the UI. This skill never
activates anything.

Templates and per-automation SQL: `reference/templates.md`.
Live per-vertical identifier tables: `reference/verticals.md`.

## Why this is not `clone-vertical-automations`

Cloning has produced a defect on every run, because a clone is only as clean as its
substitution list, and the substitution list has been wrong three separate ways:

| Defect | Where | Consequence |
|---|---|---|
| Bare shared tags reused instead of dedicated ones | Rampart (active), Atria, Abacus | Verticals' rosters merge; Panacea and Rampart still share `tags_AAABnYiHKEtdOhtigt1IUIft` on two ACTIVE automations |
| `contractorId` omitted from a `tags` body | Abacus, Rampart | Fails `TagsBody` validation, so the automation could never have run |
| Source automation id left inside the bonus self-ID guard | Cadre | Guard 2 is inert. Verified 2026-07-29: Cadre's guard names `auto_AAABn2MyfUVjGwE2gp5Hvob6`, which belongs to Abacus `proj_AAABn0Um0Wr19Gj_ql9JHKSh`. Atria and Rampart never installed guard 2 at all |

Templates fix the class, not the instance: there is no source vertical, so there is nothing
to leak. The only ids in a template are `{{TOKENS}}` and the four genuinely shared constants
listed below.

## The canonical set: 7 automations in 3 tiers

| # | Tier | Automation | Handler | Trigger |
|---|---|---|---|---|
| 1 | Access | Grant Onboarding + Active Writer on contract active | `tags` | event `contract.status_change` toValue=active |
| 2 | Access | Assign Pod A on World Created | `tags` | cron `0,15,30,45 * * * *` |
| 3 | Access | Grant `<v>_completed_work_trial` on first World Created | `tags` | event `studio.task.status_change` |
| 4 | Comp | Bump writer hours to tier 1 on spec doc approved | `update_hours` | cron `0,15,30,45 * * * *` |
| 5 | Comp | Bump writer hours to tier 2 on first task Ready for Delivery | `update_hours` | cron `0,15,30,45 * * * *` |
| 6 | Comp | Onboarding Complete Bonus Payment | `bonus` | cron `0 * * * *` |
| 7 | Ops | Grant all role tags to EPMs on contract active | `tags` | cron `0,15,30,45 * * * *` |

All seven are templated in `reference/templates.md`.

**Out of scope, deliberately** (Ryu, 2026-07-29). These exist as Teams automations on Atria but
are NOT part of the vertical launch set, so do not create them here and do not report a vertical
as incomplete for lacking them:

- the 24hr / 72hr / 168hr onboarding emails
- the 48-hour stalled-task reminder (Plan or Spec Drafting past 2 days)

They are separately owned, their copy is a per-vertical editorial decision reviewed by a named
DRI, and they are driven by whoever owns comms for that vertical rather than by the spinup.

Live coverage as of 2026-07-29, all Sparta verticals:

| Vertical | Canonical 7 present | Active | Note |
|---|---|---|---|
| Cadre | 7 | 1 | complete |
| Abacus | 7 | 1 | complete |
| Atria | 7 | 2 | plus 4 out-of-scope comms automations |
| Rampart | 7 | 1 | complete, but its active one grants SHARED tags |

## Guardrails, all of them load-bearing

1. **DRAFT only.** `create_automation` always returns `draft`. Never activate. Hand back ids
   and the Integrations link.
2. **Never inherit a number.** Bonus amount and both hour tiers must be confirmed for THIS
   vertical against its own onboarding doc before the automation is written. `$800`, `2 to 10`
   and `10 to 40` are Abacus's, and every other vertical is carrying them marked UNCONFIRMED.
   If the operator cannot supply the number, write the automation with the placeholder left in
   the NAME as `[AMOUNT UNCONFIRMED]` and say so in the handback.
3. **Dedicated vertical-prefixed tags only.** Read ids from `list_project_audiences(<project>)`
   anchors. Do NOT call `create_tags` with a bare name: it is idempotent on (company, name), so
   `Onboarding` returns the existing shared Sparta tag and the automation then acts across
   verticals. If the vertical has no prefixed tags, run `provision-vertical-teams-integrations`
   first and stop here.
4. **Judge tag ownership by id against audience anchors, never by name.** Abacus, Atria and
   Rampart all have genuinely distinct tags named bare `Active Writer`. A name match proves
   nothing.
5. **A tag id lives in two places**: `body.tagIds` AND the SQL `NOT EXISTS` dedup guard.
   Repoint both or the guard checks the wrong tag and the automation re-grants every tick.
6. **The bonus self-ID guard is a two-phase write.** See Step 5.

## Step 1: resolve the vertical's identifiers

Fill every token. Do not proceed with a token unresolved.

| Token | How to resolve | Verify |
|---|---|---|
| `{{VERTICAL}}` | Project name, e.g. `Cadre` | |
| `{{PROJECT_ID}}` | given, `proj_...` | `get_project` returns it |
| `{{JOB_TITLES}}` | `get_project(id, include=['roles'])` to `role_title`. SQL list form: `'Human Resources Expert'` or `'Accounting Expert','General Accountant'` | must match `JOBS.TITLE` exactly, check with a `SELECT DISTINCT TITLE` |
| `{{CAMPAIGN_ID}}` | `camp_...` from the vertical's Studio campaign | |
| `{{WB_WORLD_ID}}` | the `[LIVE] Golden World Building` world | `GET /worlds/?campaign_id=` |
| `{{TAG_*}}` (9) | `list_project_audiences({{PROJECT_ID}})` anchors | each id must appear as an anchor on THIS project and no other |
| `{{HOURS_TIER1}}` `{{HOURS_TIER2}}` | **ask the operator**, cite the vertical's onboarding doc | |
| `{{BONUS_AMOUNT}}` | **ask the operator**, cite the vertical's onboarding doc | |

**Shared constants, do NOT tokenize** (identical across the whole Abacus clone lineage):
`company_AAABlLQjCsYYoXP4rsZKpY0y` (Sparta), `98680cd3-d71e-4d74-9923-787ae8268ce9`
(World Created status), `planning_done_pipeline` (Spec Approved), and Ready for Delivery
matched by NAME `ILIKE 'ready for delivery%'` because its id varies per world.

**Same-lineage check before you rely on those constants.** The tasking world's `/worlds/`
response must list a `ready for delivery%` status in `STATUS_CONFIG:status_defns`, and the
WB world must have `98680cd3-...`. If either is absent the vertical is not same-lineage:
STOP and resolve its real status ids.

## Step 2: confirm the comp numbers with the operator

Ask in one message, do not proceed on assumption:

- Onboarding bonus amount, and the milestone that earns it.
- **First-world bonus amount, or an explicit no.** Abacus carries a `$300` "First World Created
  Bonus" marked UNCONFIRMED / DO-NOT-ACTIVATE, and it is in no playbook. Cadre deliberately did not
  clone it (2026-07-28). Ask, so the answer is a decision instead of an omission, and if the answer
  is no, say so in the handback rather than leaving silence.
- Starting weekly hours, tier 1 cap, tier 2 cap.
- **The weekly-hours commitment the vertical promises writers**, and which document states it.
- Whether the vertical's onboarding doc actually states them (get the doc id).

If the operator says "same as Abacus", that is a decision and it is fine, but record it in the
`notes` as an explicit decision with the date rather than as an inheritance.

**Do not treat Abacus as one consistent source, because it is not.** Verified 2026-07-29, Abacus
states its own weekly commitment three different ways: the writer onboarding doc says 15 to 20
hours, the EPM Training doc says 15 to 30, and the canvases say 15. Its office hours disagree the
same way, 9am and 3pm PT in the EPM Training doc against a live calendar series at 9am and 4pm PT.
So "same as Abacus" is not by itself an answer to the commitment or office-hours question. Make the
operator name the number, then say which document you took it from.

## Step 3: the open milestone question

**`completed_work_trial` fires on World Created on every vertical. Whether that is the right
milestone is UNDECIDED** (Ryu, 2026-07-28). The startup playbook's Step 5 still says "first
task Ready for Delivery", which nothing implements.

Rule: **name the automation for what it does.** Default the template to World Created, name it
`on first World Created`, and carry the open question into the handback. Do not silently settle
it, and do not name it for a milestone it does not implement.

## Step 4: create each automation as a draft

Use `create_automation`. Per-automation payloads are in `reference/templates.md`.

Traps, every one hit on a real run:

- `trigger_config` on create takes **`triggerType`** camelCase, even though `get_automation`
  echoes it back as `trigger_type`.
- Cron automations: `source_type:"snowflake"` plus `sql`. Event automations: omit both.
- A `tags` body **requires `contractorId`**.
- `studio.task.status_change` exposes **no `${contractorId}`**. Use `${createdByUserId}`, the
  task AUTHOR, which is the writer and not the transitioner. Its available fields are
  `campaignId, createdByEmail/Name/UserId, jobId, ownedByEmail/Name/UserId,
  previousStatusId/Name, projectId, qualifiesDone, taskId/Name/StatusId/StatusName/TagIds/Url,
  transitionedAt/ByEmail/ByName/ByUserId, version, worldId/Name`.
  **Still unverified: whether that event's `${jobId}` is the author's job or the
  transitioner's.** Flag it in the handback every time until someone confirms it.
- Payout evidence takes `formula` and `valueCents` **flat on `evidence`**, beside
  `rationale`/`variables`/`kind`. Nesting under `evidence.payout` is rejected `extra_forbidden`.
- The evidence judge rejects thin rationales on `tags`. State that `${...}` are per-recipient
  template placeholders, that recipients come from the project-scoped SQL, and that this is a
  draft.
- Automation #1 only: `idempotency_enabled:true`, `idempotency_recipient_keys:["contractorId"]`.
- `"SQL returned 0 rows"` is **expected** on a vertical with no writers yet. Not an error.
- `update_automation`'s `evidence` is a discriminated union and REQUIRES `kind`
  (`tag`/`update_hours`/`payout`) or it fails `union_tag_not_found`. `create_automation`
  infers it. This matters in Step 5.

## Step 5: install the bonus self-ID guard (two-phase, mandatory)

The bonus SQL's guard 2 blocks paying a contractor twice by checking
`PROJECTAUTOMATIONRUNS.AUTOMATIONID` against **this automation's own id**, which does not
exist until after creation. So:

1. Create the bonus automation with the literal placeholder `{{SELF_AUTOMATION_ID}}` still in
   the SQL.
2. Read the returned `automation_id`.
3. `update_automation` replacing `{{SELF_AUTOMATION_ID}}` with that id. Include
   `evidence.kind = "payout"` plus flat `formula` and `valueCents`.
4. `get_automation` and assert the SQL now contains the automation's own id and contains no
   other `auto_` literal.

**Do not skip step 4.** Skipping it is exactly how Cadre ended up with Abacus's id and how
Atria and Rampart ended up with no guard at all.

## Step 6: verify, and report honestly

Re-read every automation with `get_automation` and assert:

1. **No foreign ids.** The `sql`, `body` and `trigger_config` of each contain zero `proj_`,
   `camp_`, `world_`, `tags_` or `auto_` literal that is not this vertical's own. Build the
   allowed-id set from Step 1 plus the automation's own id. Do **not** scan `notes`, which
   legitimately names sources for provenance. **Include `auto_` in this scan.** Omitting it is
   the exact reason Cadre shipped with Abacus's automation id inside its bonus guard.
2. **No unexpanded template syntax.** No `{{` and no `<<` survives anywhere in `sql` or `body`.
2. **Tag ownership.** Every `tags_` id in every `body.tagIds` and every SQL guard appears as an
   audience anchor on THIS project. Cross-check against the other five verticals: no id may
   anchor two projects' audiences.
3. **contractorId present** in every `tags` body, and equal to `${createdByUserId}` on the
   `studio.task.status_change` one.
4. **Guard pairs.** For each tag automation, the id in `body.tagIds` matches the id in its SQL
   `NOT EXISTS` guard.
5. **Bonus self-ID guard** resolves to its own id.
6. **State.** Every automation is `draft`. Report the count, not an assumption.

Then report: the table of name / id / handler / state, the Integrations link
`https://team.mercor.com/company_AAABlLQjCsYYoXP4rsZKpY0y/projects/{{PROJECT_ID}}?tab=integrations`,
and a **BEFORE ACTIVATING** block listing every unconfirmed number, the open milestone
question, and the unverified `${jobId}` attribution.

## If someone asks for the onboarding emails anyway

They are out of the canonical set, but they exist and the request is reasonable. Do not template
them; clone from Atria and get the copy re-reviewed for the target vertical.

| Automation | Atria id | Window |
|---|---|---|
| 24hr Welcome | `auto_AAABn6k8DDekDwGiunBDJaOZ` | `DATEADD` -1470 to -1440 min |
| 72hr Check-In | `auto_AAABn6k8REecqu3Nar5K9Lba` | -4350 to -4320 min |
| 168hr One-Week | `auto_AAABn6k8hFsFRTnVZ0BIuZ_g` | -10110 to -10080 min |
| 48hr stalled-task reminder | `auto_AAABn6lDE17_FN9GckpMxaG_` | -2880 to -2910 min |

All cron `*/15`, gated on the contractor STILL holding the vertical's Onboarding tag so each
fires at most once, with a `CREATEDAT` floor at the vertical's real contract-cohort start.
Substitute: project id, Onboarding tag id, `CREATEDAT` floor, sender, and the copy.
**The window is in MINUTES, not hours.** 48 hours is 2880, not 48.

## Verification counter-checks

- **`preview_audience_members` UNDERCOUNTS. Never use it to establish a population.** It
  reported 12 for Abacus and 1 for Cadre when the truth was 13 and 2, dropping people with no
  job on the project and missing a live EPM on an `extended` contract. Query
  `CONTRACTORTAGS` joined to `JOBS` instead.
- **`list_tags` caps at 200 rows for Sparta**, so new tags are invisible through it. Use
  audience anchors, or the Teams UI.
- **`CREATEDAT` is `TIMESTAMP_TZ` in UTC.** Do not classify recency with a date-string prefix;
  during a PT evening it compares against the wrong UTC date. Use
  `DATEDIFF(minute, CREATEDAT, CURRENT_TIMESTAMP())`.
- The EPM auto-tag's dedup guard is the vertical's own EPM marker tag, which it also grants, so
  **existing EPMs are never picked up.** A one-off backfill via
  `add_contractor_tag(tag_id, user_ids[])` is always required alongside it. That driver is
  idempotent, needs no evidence block, and one call per tag with the whole user list is the
  efficient shape.
- **The EPM tag is not a proxy for "is an EPM."** Cross-check holders against `JOBS.TITLE` and
  contract status before granting; that check found four non-EPMs on the 2026-07-28 backfill.

## Known open items, carry these forward

- Which milestone should grant `completed_work_trial`. Undecided.
- Whether `studio.task.status_change`'s `${jobId}` is the author's or the transitioner's job.
- Panacea and Rampart share `tags_AAABnYiHKEtdOhtigt1IUIft` on two ACTIVE automations. Ryu
  chose to leave the active ones alone 2026-07-28. Repointing Rampart needs a backfill decision.
- Rampart has no EPM role and no Studio Admin tag, so its EPM automation grants 8 not 9 and is
  inert until an EPM role exists.
- Atria's `Onboarding` audience has ZERO targets, so granting that tag confers nothing.
