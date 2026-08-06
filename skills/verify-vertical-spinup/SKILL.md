---
name: verify-vertical-spinup
description: >
  Read-only audit of one Sparta vertical against the whole New Vertical Startup Playbook.
  Queries live APIs (Teams, Studio, Slack, Drive, Vercel) rather than trusting the Essentials
  checklist sheet, which has been wrong in both directions, and reports per check what is
  genuinely done, genuinely missing, or silently broken. Writes nothing. Use for "is <vertical>
  actually set up", "audit the spinup", "what is <vertical> missing", "verify the vertical
  against the playbook", "the Essentials sheet says X, is that true", or as the final gate
  before a vertical launches.
---

# Verify Vertical Spinup (read-only audit)

Answers one question: **is this vertical actually set up, or does a checklist just say it is?**

**This skill writes nothing.** No create, no update, no activate, no tag grant, no channel
change. If a check fails, report it and name the skill that fixes it. Fixing is a separate,
explicitly requested act.

Check specs, exact calls and per-area gotchas: `reference/checks.md`.

## Why it exists

On 2026-07-28 the Cadre Essentials checklist disagreed with live state on **9 rows, in both
directions**. It claimed RL Studio, Insightful and four tag rows were not done when they were
live, and claimed pod auto-assignment and the welcome DM/email were done when the project had
exactly one automation. Both error directions are dangerous: the first wastes a rebuild, the
second launches a vertical whose writers get no access and no comms.

**Rule: the live API is the truth. The sheet is a claim.** Where they disagree, report the
disagreement explicitly rather than silently siding with either.

## Inputs

Minimum: the vertical name. Resolve the rest and say so if any cannot be resolved.

| Need | Resolve with |
|---|---|
| Project id | `list_projects(company_id=Sparta, query=<vertical>)` |
| Studio campaign id | `studio GET /campaigns/` filtered by name |
| Slack workspace name | the workspace NAME, e.g. `Hr - sparta vertical`, NOT the vertical name |
| Drive folder id | search `<Domain> (Project <Vertical>)` under Sparta drive `1ZkXpFKOl4EbL7w06EMb64LHEnSF9p3PC` |

Company is always Sparta `company_AAABlLQjCsYYoXP4rsZKpY0y`.

## The audit: 11 areas, 42 checks

Run every area. A skipped area is reported as SKIPPED with the reason, never as passing.

| # | Area | Checks | Fixed by |
|---|---|---|---|
| A | Teams project | project exists; roles defined; **auto-provision email ON**; project owner set | `provision-vertical-teams-integrations` |
| B | Tags | the 9 role tags exist, vertical-prefixed, and **no id anchors another project's audiences** | `provision-vertical-teams-integrations` |
| C | Audiences | canonical audience set present; **every audience has at least one target**; Slack targets resolve by channel id | `provision-vertical-teams-integrations` |
| D | Slack channels | all 9 present; the 3 renamed ones no longer carry default topics; announcements is plural | `provision-vertical-slack-channels` |
| E | Canvases | **15** canvases exist and are shared into channels (13 core + Reviewer Roster in `#<v>-reviewers` + Weekly Availability in `#<v>-epms`); count remaining TBD links; instructions link is this vertical's | `create-vertical-canvases`, then `replace-instructions-link` surface 4 |
| F | Calendars | Onboarding + Writer calendars exist; shared to tag-synced groups; not world-readable; owner is not a contractor alias | `add-vertical-calendars` |
| G | Studio campaign + worlds | campaign exists; per tasking world: **hooks present**, world-level verifier exists, default agent is `sparta_external_agent`, taiga env is this campaign's, `task_schema` field count matches the source world, `prometheus_gcs_path` contains this world's id, instructions link is not the old Vigil **or Abacus** doc; **campaign-level: the pipeline dashboards exist** (see G-dash below) **and the sync remix's env matches the worlds' env** (see G-env below) | `clone-studio-world`, `replace-instructions-link`, `port-vertical-dashboards`, `restamp-taiga-env` |
| H | Automations | the canonical 7; state per automation; **no foreign ids**; tag guard pairs match; bonus self-ID guard resolves to itself | `provision-vertical-automations` |
| I | Bots | Studio Doctor deployed and responding; World File Upload bot deployed; cron switches | `add-vertical-bots` |
| J | Drive + docs | folder tree cloned and renamed; **top folder shared to the `<v>-core-team` Google group as `writer`**; `Expert Facing` shared `reader` to the writer groups; both expert forms exist with response sheets linked; **the writer instructions doc exists, sits in `Expert Facing` not `[INT]`, and its BODY is this vertical's** (read it; a correct filename over a source-vertical body is the K7 failure mode again, and the doc is hand-recast so there is no skill guaranteeing it) | `new-vertical-drive-folder`, then a human for the instructions doc |
| K | Numbers + candidate copy | the 7 live checks below (K6 retired). Every one of them is a promise to a real person, so a FAIL here is not cosmetic | `create-vertical-listing`, `create-vertical-teams-project`, `provision-vertical-automations` |

### Area G-env: the campaign's sync remix env must match the worlds'

The Taiga env id is not one field. Beyond every world's `world_custom_fields.taiga_environment_id`
and the two `*_environment_id` values inside each runner world's remixes, there is **one at campaign
level**: `world_remix_configs[*].world_remix_world_field_values.prometheus_environment_id`, on the
Sync to External Storage remix.

```
python3 ~/.claude/skills/restamp-taiga-env/restamp_taiga_env.py --campaign camp_xxx --inventory
```

FAIL when the printed `env id totals` shows more than one env id. **Every per-world check can pass
while this is wrong**, and the failure is silent in the worst way: Studio renders the correct env on
all five world pages, and the file sync copies into the *other* environment's bucket, so the runner
mounts a volume that does not exist. Delphi sat split this way from 2026-07-31 to 2026-08-02
(11 references on its own env, 1 on Abacus's) and no existing check in this audit caught it.

Fix is `restamp-taiga-env --to <the-worlds-env> --execute`, then re-run Sync to External Storage on
any world you intend to test.

### Area G-dash: the pipeline dashboards

`GET /campaigns/{camp_id}/custom-query-views`. **Run it as a `campaign_admin`** — the endpoint
filters by the caller's role, so a non-admin read under-reports and makes a healthy vertical
look empty.

FAIL when the count is far below the source vertical's set. A cloned campaign inherits **zero**
custom query views, so this is the default state of every new vertical, and nothing else in the
audit notices: the worlds, hooks, verifier and agent can all be perfect while every reviewer
opens Studio to an empty sidebar and concludes there is no work.

Two softer findings worth reporting rather than failing on:

- **Every view has a null `conditional_render_filter`.** Null means ADMIN-ONLY, not "everyone",
  so a vertical in this state shows its reviewers nothing. Indistinguishable from having no
  views at all, from a reviewer's seat.
- **A view still carries the loose world-name filter** (`NOT IN ('golden_world_MAV', …)` rather
  than the four `NOT ILIKE` clauses). New test worlds leak into reviewers' queues.

Also check any **world-scoped** view (one filtering a single `world_id`) points at THIS
vertical's world and that the world carries the status the SQL filters on. A view aimed at a
world without that status renders an empty table forever, which reads as "no work in this
stage". Fixed by `port-vertical-dashboards`.

### Area K in full

Cheap to run, all read-only, and every one has been found broken on a live vertical.

| # | Check | How | Why |
|---|---|---|---|
| K1 | Onboarding doc is not the platform placeholder | `get_project_onboarding_doc`. FAIL on the exact string "currently being prepared" | Cadre shipped this to 33 signed experts. The doc record EXISTS, so a checklist ticks it. This is the canonical BROKEN |
| K2 | No role pays more than it bills | `get_project(include=['roles'])`, FAIL any role with `expected_payable_hourly > expected_billable_hourly` | Atria's expert bills 50 and pays 85; Abacus's EPM bills 55 and pays 90. Both live. The role loses money every hour it is worked |
| K3 | The weekly commitment reaches the candidate somehow | `get_listing` `hoursPerWeek`. **Null is the Sparta norm, NOT a defect**: null on Abacus's flagship Accounting Expert and on both Cadre listings (checked 2026-07-29). Report it, then check the commitment is stated somewhere a candidate actually sees before signing. FAIL only if it appears nowhere | A candidate should not have to guess the commitment, but flagging the field itself would fail every live vertical including the most mature one, and a check that cries wolf gets ignored |
| K4 | Every listing with auto-reject ON has a rejection template | `get_listing`, FAIL when `automaticRejectionsOn` is true and `rejectionTemplateBody` is null | Cadre's flagship Expert listing auto-rejects at 7 days with no template. Rejected candidates get platform default copy |
| K5 | The rejection template names THIS vertical's role | read the subject and body | Abacus's says "An Update To Your Accounting Expert Application". Copy that listing to a new vertical and you reject insurance candidates as accountants |
| K6 | ~~Instant offer text~~ **RETIRED 2026-07-29, do not reinstate** | nothing to check | This check was wrong. `offerExtendedText` is null on EVERY Sparta listing checked, including Abacus's flagship Accounting Expert, because **the instant offer email is shared platform-wide and needs no per-vertical work** (Ryu, confirmed against live listings). Flagging null would have failed the most mature vertical. Note there is a separate PROJECT-level `offer_extended_text` on `edit_project`; no available tool reads it back, so nothing can be verified about it and nothing should be asserted |
| K7 | The EPM Training doc is this vertical's | **READ the body** of the doc in `[INT] Project <Vertical>`. FAIL on any mention of another vertical, the wrong domain, or Abacus doc ids `1u-Go8Cr` / `1x6WJoAT`. Checking the Drive filename is NOT this check | The Drive filename is renamed by the clone and the body is not, so the filename PASSES while the doc sends EPMs to another vertical. Cadre's read `Cadre EPM Training` in Drive with an Abacus body underneath. **Root cause was the `_CLONEME` template's own copy being Abacus's document verbatim; TOKENIZED 2026-07-29**, so verticals cloned after that date inherit tokens. Abacus, Atria and Rampart were all cloned BEFORE it, so check them |
| K8 | The weekly commitment is the same number everywhere | compare the onboarding doc, the EPM Training doc, the canvases, and the listing `hoursPerWeek` | Abacus says 15 to 20 in the onboarding doc, 15 to 30 in the EPM Training doc, and 15 in the canvases. Its office hours disagree too, 9am/3pm PT in the doc against a 9am/4pm PT live calendar. Three sources, three promises |

K2 and K5 are the two that reach a stranger. Rank them first in the scorecard when they fail.

## Output

One scorecard table, most broken first. Nothing else at the top.

```
| Area | Check | Expected | Actual | Verdict |
```

Verdicts are exactly four: **PASS**, **FAIL**, **BROKEN** (present but non-functional, the
worst kind because a checklist reads it as done), **SKIPPED** (with the reason).

Then, and only if non-empty:

1. **BROKEN items**, expanded. These are the point of the skill.
2. **Sheet disagreements**: rows where the Essentials checklist and live state differ, with the
   direction of each.
3. **Blocking for launch**: the subset that stops writers working or stops them being paid.
4. **Next actions**, each naming the skill that fixes it.

Give a confidence rating per area, not one for the whole audit. An area where an API was
unreachable is low confidence and must not be reported as passing.

## The failure modes this skill exists to catch

Every one of these has actually happened and every one reads as "done" on a checklist.

| Symptom | Why a checklist misses it |
|---|---|
| Audience exists with **zero targets** | Atria's `Onboarding`. The audience is present, so the row ticks, but the tag confers nothing |
| Automation grants a tag **no audience anchors** | Widespread before 2026-07-28. Silent dead end: the writer never gets the Slack channel or Google group |
| Automation exists but is **draft** | Cadre has 1 of 10 active. `list_automations` returns it either way; only `state` tells you |
| Tag id **shared with another vertical** | Names match, ids differ, or worse names differ and ids match. Judge by id against audience anchors |
| SQL guard points at a **different tag** than the body grants | Re-grants on every cron tick. Rampart's Pod A, fixed 2026-07-28 |
| Bonus self-ID guard names **another vertical's automation** | Cadre, found 2026-07-29. Guard is inert; a checklist sees "guard installed" |
| World has **zero hooks** | Tasks strand at "Running ... AutoQC". The world exists and looks configured |
| World carries the **source campaign's taiga env** | Clones leak it. Runs go to the wrong environment |
| World layout links the **old Vigil instructions doc** | Writers silently read another vertical's instructions |
| `slack_search_channels` returns **2 of 9** | It defaults to public-only and 7 of the 9 are private. Looks like nothing was built |
| Renamed channel leaves a **stale Teams target name** | `externalId` is still correct, so resolving by name fails while access works, or the reverse |
| Onboarding doc exists and says **nothing** | Cadre, found 2026-07-29. The record is present and `get_project_onboarding_doc` returns 200, so every checklist and every sheet reads it as done. It said "your onboarding document is currently being prepared" to 33 signed experts |
| Cloned doc keeps the **source vertical's whole body** | Cadre's EPM Training doc is titled `Abacus EPM Training`. The Drive clone renames the FILE, not the content, so the file listing looks right and the reader gets another vertical's links |
| A number is right in one place and **wrong in the next** | Abacus's weekly commitment is 15 to 20, or 15 to 30, or 15, depending which document you open. No single check catches this; only comparing the surfaces does |
| Drive folder tree built but **shared to nobody** | Creating the `<v>-core-team` Google group is a Teams step; sharing the folder to it is a separate Drive step. The tree exists and the group exists, so both rows tick, and every EPM but the creator still gets "Request access" |

## Non-negotiable method rules

1. **Never use `preview_audience_members` to establish a population.** It undercounts: 12 vs a
   true 13 on Abacus, 1 vs 2 on Cadre. It drops people with no job on the project and missed a
   live EPM on an `extended` contract. Query `CONTRACTORTAGS` joined to `JOBS`.
2. **An audience's `memberCount` is not evidence either, and a 0 is not a finding on its own.**
   Westwood's Onboarding audience read 0 while 46 active people held its exact tag. Confirmed
   2026-08-06 as a PLATFORM bug, not a misconfiguration; this audit reported it as a vertical-level
   FAIL and was wrong to. Before writing up any zero: (a) `filter_project_team(tags_included=[<tag
   name>])` for the real holder count, and (b) compare sibling audiences whose tags the same people
   hold. If the siblings count fine, the wiring is not what differs, so it is not this vertical's
   defect. Report it as a platform issue or leave it out.
3. **Always pass `channel_types="public_channel,private_channel"`** to `slack_search_channels`.
4. **Judge tag ownership by id against audience anchors, never by name.**
5. **`list_tags` caps at 200 rows for Sparta**, so a new tag can be invisible through it. Use
   audience anchors or the Teams UI.
6. **Read `state`, not existence**, for every automation, cron and bot switch.
7. **`CREATEDAT` is `TIMESTAMP_TZ` in UTC.** Never classify recency with a date-string prefix.
   Use `DATEDIFF(minute, CREATEDAT, CURRENT_TIMESTAMP())`.
8. **Do not scan `notes` fields for foreign ids.** They legitimately name sources for provenance.
9. **Read Drive shares with `drive.permissions.list` + `supportsAllDrives: true`.** The plain
   `get_file_permissions` tool HIDES group and inherited permissions and shows only you as
   owner, so a correctly shared folder reads as shared with nobody. Confirmed on all four new
   verticals 2026-07-29 (PT): Abacus `abacus-core-team-HKSh`, Atria `atria-core-team-l4Nq`,
   Cadre `cadre-core-team-Rr5G`, Rampart `rampart-core-team-zZi7`, each `writer` on the top folder.
10. **An unreachable API is SKIPPED, never PASS.**
10. Report times in Pacific, labelled.

## Scope note

This audits **one** vertical. To compare all six, run it per vertical and diff the scorecards;
do not try to shortcut with a cross-vertical query, because several checks (audience anchors,
tag ownership) are only meaningful relative to a single project.
