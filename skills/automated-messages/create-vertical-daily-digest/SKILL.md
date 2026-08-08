---
name: create-vertical-daily-digest
description: >
  Stand up the Daily Digest DM (tasking) automation on a Sparta vertical: the 6am PT Slack DM
  that tells each writer which of their tasks are On Time and which are Past Due, with working
  Studio deep links, plus their metrics and the expectations they are measured against. Authored
  from a parameterized template rather than cloned, because every clone of this automation so far
  has kept the source vertical's campaign id, account id or pod channel and silently reported the
  wrong campaign's work. Preflights the four things that make the digest render empty or wrong,
  creates it as a DRAFT, and verifies against the live preview. Use during a new-vertical spinup,
  or for "set up the daily digest for <vertical>", "add the writer status DM", "the digest is
  sending an empty list", "port the daily digest to <vertical>".
---

# Create Vertical Daily Digest DM (tasking)

Authors one automation on a Sparta vertical's Mercor Teams project: a cron DM, 6am Pacific, to
every writer who has at least one active task. Reference implementation is Atria
`auto_AAABn9-WMOmIgfuVwDRHrp3_`; Abacus `auto_AAABn965JRje-0Vkc2tCtJIh` is the same template with
a different cfg block and a locally diverged Expected block.

**Created as a DRAFT. A human activates it in the UI. This skill never activates anything.**

## What the writer receives

```
Hi Sheri,

*Atria Daily Status: Saturday, August 8*

You have 3 active tasks (Admin Healthcare).

*:white_check_mark: On Time*
- <link|Task 1c07aac3> - Ready for Agent Runner & QC Review - 1 day in stage
- <link|Task l3ijb113> - Running Task AutoQC - entered today - waiting on the pipeline, nothing for you to do

*:alarm_clock: Past Due*
- <link|Task abd66168> - Failure Analysis - 6 days in stage

*:bar_chart: Your metrics*
Total clocked time: 29.3h on this project
Tasks ready for delivery: 0
Avg iterations per task: 2.0 (times sent back from a human review)
Pass rate: 0% (passes / submissions to first or final human review)

*:dart: Expected*
Time in a stage: move to the next stage within 3 days
Avg iterations per task: 2 or fewer
Pass rate: above 50%

If you have any blockers please reach out to your pod lead in #atria-pod-a!
```

## Inputs

Gather all of these BEFORE writing anything. Nine go into the cfg block, one is the cron.

| Input | Where it comes from | Notes |
|---|---|---|
| `campaign_id` | `list_campaigns`, or the Studio URL | `camp_...`. The single most common thing a clone leaks |
| `project_id` | `list_projects` | `proj_...`. Must be the SAME vertical as the campaign |
| `vertical_name` | the operator | Display name, e.g. `Atria` |
| `domain_label` | the operator | What the writers do, e.g. `Admin Healthcare`, `Accounting` |
| `past_due_days` | default `3` | Days in a stage before a task is Past Due |
| `max_lines` | default `12` | Tasks per section before "and N more" |
| `exp_iterations` | the operator | Iteration expectation. `2` on the older verticals |
| `exp_pass_pct` | the operator | Pass-rate expectation. `50` on the older verticals |
| `pod_channel` | the operator | e.g. `#atria-pod-a`. Plain text, not a channel link, unless you resolve the id |
| cron | default `0 6 * * *` | Pacific |

**`account_id` is the same on every Sparta campaign**: `acct_be8f7fcc2c554b33baa5a0c9d05496e3`,
verified against `RL_STUDIO_PUBLIC.CAMPAIGNS.ACCOUNT_ID` across all nine. Confirm it for a new
campaign rather than assuming, it is one query.

**Never ask the operator to confirm a number you can look up, and never invent one they did not
give.** `exp_iterations` and `exp_pass_pct` set what writers are told they are failing; both were
inherited from Vigil and have never been recalibrated per vertical. Say so when you ask.

## Preflight

Run all four. Each one has shipped a broken digest when skipped.

**1. The world name filters actually exclude this vertical's non-tasking worlds.**

```sql
SELECT DISTINCT WORLD_NAME FROM PROJECT_ANALYTICS.RLS.TASKS_BASE
WHERE CAMPAIGN_ID='<campaign_id>' AND ARCHIVED_AT IS NULL ORDER BY 1
```

The template drops names matching `%golden%`, `%test%`, `Template -%`, `[OLD]%` and `% - Copy`.
Atria's WB world is `[LIVE] Golden World Building` and its test world is `Test_T_1`, so both are
caught. If this vertical named them differently, the digest will report world-building tasks to
writers as if they were tasking work. Fix the filter, do not fix the world names.

**2. Writers bridge from Studio to Mercor.** The join is Studio email prefix to
`USERMETADATA.EXTERNALID`. If it returns far fewer people than the campaign has writers, the
digest will silently DM almost nobody.

```sql
WITH em AS (SELECT ru.USER_ID, SPLIT_PART(LOWER(ru.EMAIL),'@',1) extid
  FROM RAW_ANNOTATION_PLATFORM_DATA.RL_STUDIO_PUBLIC.USERS ru
  WHERE COALESCE(ru._FIVETRAN_DELETED,FALSE)=FALSE AND ru.EMAIL IS NOT NULL)
SELECT COUNT(DISTINCT t.AUTHOR) AS authors_in_campaign,
       COUNT(DISTINCT m.USERID) AS bridged_to_mercor
FROM PROJECT_ANALYTICS.RLS.TASKS_BASE t
LEFT JOIN em ON em.USER_ID=t.AUTHOR
LEFT JOIN ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.USERMETADATA m ON LOWER(m.EXTERNALID)=em.extid
WHERE t.CAMPAIGN_ID='<campaign_id>' AND t.ARCHIVED_AT IS NULL
```

**3. Job titles.** Recipients are writers, so the template excludes titles matching
`%Project Manager%`, `%Team Lead%` and exactly `EPM`. Titles differ per vertical (Abacus alone has
nine), so list them and confirm nothing reviewer-shaped slips through and no writer is excluded.

```sql
SELECT TITLE, COUNT(*) FROM ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.JOBS
WHERE PROJECTID='<project_id>' AND STATUS='active' AND COALESCE(_FIVETRAN_DELETED,FALSE)=FALSE
GROUP BY 1 ORDER BY 2 DESC
```

**4. Recipient count is not zero.** Run the finished SQL through `execute_sql` before creating the
automation. A digest that returns no rows creates cleanly, runs green forever, and DMs nobody. On
Abacus this preflight read 27 writers and 62 active tasks.

## Build

1. Read `reference/digest-template.sql`. Replace the ten placeholders in the cfg block. **Change
   nothing below cfg.** Every line under it is deliberate and the reasons are in the comments.
2. Run the finished SQL through `execute_sql` and read one rendered `MESSAGE_BODY` end to end.
   Check the headers carry their `*` (Slack bold), the emoji render as `:name:` shortcodes, and a
   task link opens.
3. `create_automation` with:
   - `handler_name`: `send_slack_message_as_bot`
   - `body`: `{"mode":"dm","jobId":"${JOBID}","message":"${MESSAGE_BODY}"}`
   - `trigger_config`: `{"type":"cron","cron":"0 6 * * *"}`
   - `state`: draft
   - name: `<Vertical>: Daily Digest DM (tasking) - writer task status`
4. `get_automation` and read the returned `sample_row` and `preview`. The write response echoes
   your own write; only a fresh read proves the final state.

## Verify

- `preview.valid` is `true` and `preview.errors` is empty.
- The sample message names THIS vertical and links THIS campaign id. Grep the rendered body for
  the source vertical's campaign id; a leaked id is the failure this skill exists to prevent.
- Recipient count matches preflight 4.
- State is `draft`.
- Report the automation URL and the rendered sample to the operator, and say plainly that it is a
  draft and will not fire until a human activates it.

## Gotchas

**Bot DM delivery has never been proven on a new vertical.** A test send to Ryu's own Atria
contract on 2026-08-07 executed successfully and never arrived. Both live Vigil Studio-sourced
cron DMs have failed 100% of their runs while the non-Studio bonus cron succeeds. On Abacus the
digest ran green five times on 2026-08-08 with no matching row in `ACTIONSQUEUE`. **A successful
run does not mean a delivered message.** Send one test and get the human to confirm receipt in
Slack before anyone activates this.

**The annotator link needs both query params.** `…/annotator/tasks/<id>/` alone returns page not
found. The working form is `…/annotator/tasks/<id>/?accountId=<acct>&campaignId=<camp>`. The bare
form is still live in the Vigil and Panacea WB event DMs, so do not copy a link from those.

**`TASKS_BASE` is version-per-row.** Every row is one transition. `rn=1` is the current state and
the full set is the history. `TASK_TRANSITION_EVENTS` is empty and is not the log.

**The Studio task-writing timer is empty on every vertical except Vigil.** `TASK_PRODUCTION_
DURATION_HOURS_STUDIO` is 0.000000 on all rows (checked: 0 of 234 on Atria, 0 of 445 on Abacus),
so "Total clocked time" is ALL hours on the project, including onboarding, reading and meetings.
Do not add a per-task AHT target on top of it without saying so: Vigil's 12h figure comes from a
timer that actually works, and the comparison is not like for like.

**Hours cannot be attributed to a task.** Insightful's `TIMELOG` records which timer was running,
never which Studio task; its `TASKID` column holds the Insightful timer id. There is no per-task
hours figure available anywhere, so any per-task time metric must come from elapsed transition
timestamps, not clocked time.

**`LISTAGG` over an all-NULL group returns empty string, not NULL**, which printed a bare "Past
Due" heading with nothing under it. That is what the `NULLIF` wrapper is for.

**The platform has no concurrent-edit protection.** A UI save from a browser tab opened before
your API write silently reverts it, with no warning and no conflict error. Reload before saving,
and re-read after writing if a human might have the page open. `version` and `updated_at` are the
tell.

**The evidence judge rejects contradictions.** If the rationale you submit disagrees with the
payload, the write is refused. State plainly what changed and why; do not describe an intention
the SQL does not carry out.

**The SQL validator keyword-scans comments.** The words COPY INTO, PUT, GET, REMOVE, CALL and
EXECUTE IMMEDIATE are rejected even inside a `--` comment. Reword rather than deleting the comment.

## Per-vertical divergence, on purpose

Abacus dropped pass rate from both the metrics and the Expected block on 2026-08-08, and replaced
the flat iteration target with three bands (on track 3 or fewer, at risk 4 to 5, off track 6 or
more) plus a closing line naming the pause consequence. Atria deliberately still carries pass
rate. **Read the vertical you are copying from before assuming the two are the same**, and copy
the cfg block only.
