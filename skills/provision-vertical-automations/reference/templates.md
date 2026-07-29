# Canonical automation templates

Tokenized from the live Cadre set on 2026-07-29, which is the cleanest reference: dedicated
prefixed tags throughout, `contractorId` present, names matching triggers. Every
vertical-scoped id has been replaced with a `{{TOKEN}}`.

Constants deliberately left inline because they are shared across the entire Abacus clone
lineage and are NOT per-vertical:

- `company_AAABlLQjCsYYoXP4rsZKpY0y`, Sparta
- `98680cd3-d71e-4d74-9923-787ae8268ce9`, the World Created status
- `planning_done_pipeline`, the Spec Approved / Pipeline Running status
- Ready for Delivery is matched by NAME, `ILIKE 'ready for delivery%'`, because the id varies
  per world

Verify same-lineage before trusting them. See SKILL.md Step 1.

## Tokens

| Token | Example (Cadre) |
|---|---|
| `{{VERTICAL}}` | `Cadre` |
| `{{PROJECT_ID}}` | `proj_AAABn6Z-4irb63tDd_NNRr5G` |
| `{{CAMPAIGN_ID}}` | `camp_35e49895edea4ad7b822d8347dab6c4c` |
| `{{WB_WORLD_ID}}` | `world_f68670e0b59d4a13b4658a3e1ed2a6ee` |
| `{{JOB_TITLES}}` | `'Human Resources Expert'` (SQL list, quoted, comma-separated) |
| `{{TAG_ONBOARDING}}` `{{TAG_ACTIVE_WRITER}}` `{{TAG_POD_A}}` `{{TAG_WORK_TRIAL}}` `{{TAG_WORLD_BUILDER}}` `{{TAG_TASK_WRITER}}` `{{TAG_REVIEWER}}` `{{TAG_EPM}}` `{{TAG_STUDIO_ADMIN}}` | from `list_project_audiences` anchors |
| `{{HOURS_TIER1}}` `{{HOURS_TIER2}}` | operator-confirmed, e.g. `10`, `40` |
| `{{BONUS_AMOUNT}}` | operator-confirmed, e.g. `800` |
| `{{SELF_AUTOMATION_ID}}` | filled in phase 2, after create |

**`<<...>>` are text macros, not SQL.** Expand them inline before sending. Snowflake will
reject any payload that still contains a `<<` or a `{{`, and the leak check in SKILL.md Step 6
must also assert that no `{{TOKEN}}` survived into a created automation.

Reusable SQL fragment referenced below as `<<EPM_EXCLUDE>>`:

```sql
NOT EXISTS (SELECT 1 FROM ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.CONTRACTORTAGS ept JOIN ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.TAGS t ON t.TAGID=ept.TAGID AND COALESCE(t._FIVETRAN_DELETED,FALSE)=FALSE AND t.TYPE='team' AND t.NAME ILIKE '%epm%' WHERE ept.USERID=a.AUTHOR_USER_ID AND COALESCE(ept._FIVETRAN_DELETED,FALSE)=FALSE)
```

Reusable fragment `<<AUTHORS_IN_WB_AT_STATUS(status)>>`, the Studio-to-Mercor identity chain
used by every cron automation here. Attribution is by task AUTHOR, never the transitioner:

```sql
WITH eligible_tasks AS (
  SELECT DISTINCT TASK_ID FROM RAW_ANNOTATION_PLATFORM_DATA.RL_STUDIO_PUBLIC.TASKS
  WHERE WORLD_ID='{{WB_WORLD_ID}}' AND TASK_STATUS_ID='<status>' AND COALESCE(_FIVETRAN_DELETED,FALSE)=FALSE
),
authors AS (
  SELECT tv.AUTHOR_USER_ID FROM PROJECT_ANALYTICS.CENTRALIZED.TASK_VERSIONS tv
  JOIN eligible_tasks et ON et.TASK_ID=tv.TASK_ID WHERE tv.AUTHOR_USER_ID IS NOT NULL GROUP BY tv.AUTHOR_USER_ID
)
```

---

## 1. Grant Onboarding + Active Writer on contract active

Name: `{{VERTICAL}}: Grant Onboarding + Active Writer on contract active`
Handler `tags`. Event. No `source_type`, no `sql`.
Set `idempotency_enabled: true`, `idempotency_recipient_keys: ["contractorId"]`.

```json
{
  "trigger_config": {"type":"event","triggerType":"contract.status_change","params":{"toValue":"active"}},
  "body": {
    "mode": "add",
    "jobId": "${jobId}",
    "tagIds": ["{{TAG_ACTIVE_WRITER}}", "{{TAG_ONBOARDING}}"],
    "companyId": "company_AAABlLQjCsYYoXP4rsZKpY0y",
    "contractorId": "${contractorId}"
  },
  "reasons": ["Onboarding / Training"]
}
```

This is the one automation that is already ACTIVE on all four spun-up verticals. If the target
already has an equivalent, do not create a second one.

---

## 2. Assign Pod A on World Created

Name: `{{VERTICAL}}: Assign Pod A on World Created`
Handler `tags`. Cron `0,15,30,45 * * * *`. `source_type: "snowflake"`.

Single pod, no A/B/C rotation. Idempotent via the `NOT EXISTS` on the Pod A tag, which must be
the SAME id as in `body.tagIds`.

```sql
<<AUTHORS_IN_WB_AT_STATUS('98680cd3-d71e-4d74-9923-787ae8268ce9')>>
SELECT j.JOBID AS "jobId", j.CONTRACTORID AS "contractorId", j.COMPANYID AS "companyId"
FROM authors a
JOIN ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.JOBS j
  ON j.CONTRACTORID=a.AUTHOR_USER_ID AND j.PROJECTID='{{PROJECT_ID}}'
  AND j.TITLE IN ({{JOB_TITLES}}) AND j.ISLATEST=1 AND COALESCE(j._FIVETRAN_DELETED,FALSE)=FALSE AND j.STATUS IN ('active','accepted','extended')
WHERE NOT EXISTS (SELECT 1 FROM ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.CONTRACTORTAGS ct WHERE ct.USERID=a.AUTHOR_USER_ID AND ct.TAGID='{{TAG_POD_A}}' AND COALESCE(ct._FIVETRAN_DELETED,FALSE)=FALSE)
QUALIFY ROW_NUMBER() OVER (PARTITION BY j.CONTRACTORID ORDER BY CASE WHEN j.STATUS='active' THEN 0 ELSE 1 END, j.UPDATEDAT DESC)=1
```

```json
{
  "body": {
    "mode": "add",
    "jobId": "${jobId}",
    "tagIds": ["{{TAG_POD_A}}"],
    "companyId": "company_AAABlLQjCsYYoXP4rsZKpY0y",
    "contractorId": "${contractorId}"
  }
}
```

---

## 3. Grant completed_work_trial on first World Created

Name: `{{VERTICAL}}: Grant {{VERTICAL}}_completed_work_trial on first World Created`
Handler `tags`. Event. No `source_type`, no `sql`.

`contractorId` is `${createdByUserId}` because this event exposes no `${contractorId}`, and
createdByUserId is the task AUTHOR. Omitting it, as Abacus and Rampart do, fails `TagsBody`
validation.

**The milestone is UNDECIDED.** World Created is what every vertical implements; the playbook
says Ready for Delivery. Name it for what it does and carry the question forward.

```json
{
  "trigger_config": {"type":"event","triggerType":"studio.task.status_change","params":{"fieldValues":{"taskStatusName":["World Created"]}}},
  "body": {
    "mode": "add",
    "jobId": "${jobId}",
    "tagIds": ["{{TAG_WORK_TRIAL}}"],
    "companyId": "company_AAABlLQjCsYYoXP4rsZKpY0y",
    "contractorId": "${createdByUserId}"
  }
}
```

---

## 4. Bump writer hours to tier 1 on spec doc approved

Name: `{{VERTICAL}}: Bump writer hours to {{HOURS_TIER1}} on spec doc approved (WB golden world)`
Handler `update_hours`. Cron `0,15,30,45 * * * *`. `source_type: "snowflake"`.

Raise-only: the `EXPECTED_HOURS < {{HOURS_TIER1}}` gate is also what makes it self-limiting, so
it needs no separate dedup guard.

```sql
<<AUTHORS_IN_WB_AT_STATUS('planning_done_pipeline')>>
SELECT j.JOBID AS "jobId", j.CONTRACTORID AS "contractorId", j.COMPANYID AS "companyId"
FROM authors a
JOIN ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.JOBS j
  ON j.CONTRACTORID=a.AUTHOR_USER_ID AND j.PROJECTID='{{PROJECT_ID}}'
  AND j.TITLE IN ({{JOB_TITLES}}) AND j.ISLATEST=1 AND COALESCE(j._FIVETRAN_DELETED,FALSE)=FALSE AND j.STATUS IN ('active','accepted','extended')
WHERE COALESCE(j.EXPECTED_HOURS,0) < {{HOURS_TIER1}}
  AND <<EPM_EXCLUDE>>
QUALIFY ROW_NUMBER() OVER (PARTITION BY j.CONTRACTORID ORDER BY CASE WHEN j.STATUS='active' THEN 0 ELSE 1 END, j.UPDATEDAT DESC)=1
```

```json
{
  "body": {
    "jobId": "${jobId}",
    "companyId": "company_AAABlLQjCsYYoXP4rsZKpY0y",
    "projectId": "{{PROJECT_ID}}",
    "contractorId": "${contractorId}",
    "maxHoursValue": "{{HOURS_TIER1}}",
    "maxHoursStrategy": "custom"
  }
}
```

---

## 5. Bump writer hours to tier 2 on first task Ready for Delivery

Name: `{{VERTICAL}}: Bump writer hours to {{HOURS_TIER2}} on first task Ready for Delivery`
Handler `update_hours`. Cron `0,15,30,45 * * * *`. `source_type: "snowflake"`.

RFD is resolved by NAME across all the campaign's worlds EXCEPT the WB golden world, because
the status id differs per world.

**Known edge case, decide before activating:** the gate is `EXPECTED_HOURS < {{HOURS_TIER2}}`,
so a writer who reaches RFD without ever passing tier 1 jumps straight from their starting
hours to tier 2, skipping the ladder. That is probably intended, since RFD is the later
milestone, but it is not enforced anywhere. If the ladder must be strict, add
`AND COALESCE(j.EXPECTED_HOURS,0) >= {{HOURS_TIER1}}`.

```sql
WITH rfd_status AS (   -- (world, status_id) whose NAME is a Ready-for-Delivery variant, excluding the WB golden world
  SELECT WORLD_ID, sid FROM (
    SELECT w.WORLD_ID, f.value:status_id::string AS sid, f.value:status_name::string AS sname,
           ROW_NUMBER() OVER (PARTITION BY w.WORLD_ID, f.value:status_id::string ORDER BY w._FIVETRAN_SYNCED DESC NULLS LAST) rn
    FROM RAW_ANNOTATION_PLATFORM_DATA.RL_STUDIO_PUBLIC.WORLDS w,
         LATERAL FLATTEN(input => w.STATUS_CONFIG:status_defns) f
    WHERE w.CAMPAIGN_ID = '{{CAMPAIGN_ID}}'
      AND COALESCE(w._FIVETRAN_DELETED, FALSE) = FALSE
      AND w.WORLD_ID <> '{{WB_WORLD_ID}}'
  ) WHERE rn = 1 AND sname ILIKE 'ready for delivery%'
),
eligible_tasks AS (
  SELECT DISTINCT t.TASK_ID
  FROM RAW_ANNOTATION_PLATFORM_DATA.RL_STUDIO_PUBLIC.TASKS t
  JOIN rfd_status rs ON rs.WORLD_ID = t.WORLD_ID AND rs.sid = t.TASK_STATUS_ID
  WHERE COALESCE(t._FIVETRAN_DELETED, FALSE) = FALSE
    AND t.WORLD_ID <> '{{WB_WORLD_ID}}'
),
authors AS (
  SELECT tv.AUTHOR_USER_ID FROM PROJECT_ANALYTICS.CENTRALIZED.TASK_VERSIONS tv
  JOIN eligible_tasks et ON et.TASK_ID=tv.TASK_ID WHERE tv.AUTHOR_USER_ID IS NOT NULL GROUP BY tv.AUTHOR_USER_ID
)
SELECT j.JOBID AS "jobId", j.CONTRACTORID AS "contractorId", j.COMPANYID AS "companyId"
FROM authors a
JOIN ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.JOBS j
  ON j.CONTRACTORID=a.AUTHOR_USER_ID AND j.PROJECTID='{{PROJECT_ID}}'
  AND j.TITLE IN ({{JOB_TITLES}}) AND j.ISLATEST=1 AND COALESCE(j._FIVETRAN_DELETED,FALSE)=FALSE AND j.STATUS IN ('active','accepted','extended')
WHERE COALESCE(j.EXPECTED_HOURS,0) < {{HOURS_TIER2}}
  AND <<EPM_EXCLUDE>>
QUALIFY ROW_NUMBER() OVER (PARTITION BY j.CONTRACTORID ORDER BY CASE WHEN j.STATUS='active' THEN 0 ELSE 1 END, j.UPDATEDAT DESC)=1
```

```json
{
  "body": {
    "jobId": "${jobId}",
    "companyId": "company_AAABlLQjCsYYoXP4rsZKpY0y",
    "projectId": "{{PROJECT_ID}}",
    "contractorId": "${contractorId}",
    "maxHoursValue": "{{HOURS_TIER2}}",
    "maxHoursStrategy": "custom"
  }
}
```

---

## 6. Onboarding Complete Bonus Payment

Name: `{{VERTICAL}}: Onboarding Complete Bonus Payment (${{BONUS_AMOUNT}}, spec doc approved)`
Handler `bonus`. Cron `0 * * * *`. `source_type: "snowflake"`.
Append `[AMOUNT UNCONFIRMED]` to the name if the operator could not confirm the figure.

**Two-phase write. `{{SELF_AUTOMATION_ID}}` is filled after create.** See SKILL.md Step 5.

Three guards, all required:
1. any prior onboarding / spec-doc / work-trial bonus on this project, matched on reason text
2. any bonus already paid by THIS automation, matched on its own id
3. EPM exclusion

The bonus handler queues for manual approval, so this does not pay silently. That is not a
reason to skip guard 2.

```sql
<<AUTHORS_IN_WB_AT_STATUS('planning_done_pipeline')>>
SELECT
  j.JOBID        AS "jobId",
  j.UID          AS "jobUid",
  j.CONTRACTORID AS "contractorId",
  j.PROJECTID    AS "projectId",
  j.COMPANYID    AS "companyId",
  u.NAME         AS "ownedByName"
FROM authors a
JOIN ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.JOBS j
  ON j.CONTRACTORID=a.AUTHOR_USER_ID AND j.PROJECTID='{{PROJECT_ID}}'
  AND j.TITLE IN ({{JOB_TITLES}}) AND j.ISLATEST=1 AND COALESCE(j._FIVETRAN_DELETED,FALSE)=FALSE AND j.STATUS IN ('active','accepted','extended')
LEFT JOIN ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.MERCORUSERS_NEW u
  ON u.USERID = j.CONTRACTORID AND COALESCE(u._FIVETRAN_DELETED, FALSE) = FALSE
WHERE NOT EXISTS (                                    -- guard 1: any prior onboarding/spec-doc/work-trial bonus on the project
    SELECT 1 FROM ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.BONUS b
    WHERE b.CONTRACTORID = j.CONTRACTORID
      AND b.PROJECTID = '{{PROJECT_ID}}'
      AND COALESCE(b._FIVETRAN_DELETED, FALSE) = FALSE
      AND (b.REASON ILIKE '%spec doc approved%' OR b.REASON ILIKE '%work trial%' OR b.REASON ILIKE '%completing onboarding%')
  )
  AND NOT EXISTS (                                    -- guard 2: any bonus already paid by THIS automation
    SELECT 1 FROM ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.BONUS b
    LEFT JOIN ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.PROJECTAUTOMATIONRUNS par
      ON par.RUNID = SPLIT_PART(b.SOURCE, ':', 3)
    WHERE b.CONTRACTORID = j.CONTRACTORID
      AND b.PROJECTID = '{{PROJECT_ID}}'
      AND par.AUTOMATIONID = '{{SELF_AUTOMATION_ID}}'
      AND b._FIVETRAN_DELETED IS DISTINCT FROM TRUE
  )
  AND <<EPM_EXCLUDE>>
QUALIFY ROW_NUMBER() OVER (PARTITION BY j.CONTRACTORID ORDER BY CASE WHEN j.STATUS='active' THEN 0 ELSE 1 END, j.UPDATEDAT DESC)=1
```

```json
{
  "body": {
    "jobUid": "${jobUid}",
    "reason": "{{BONUS_AMOUNT}} for completing onboarding (first spec doc approved)",
    "companyId": "${companyId}",
    "projectId": "${projectId}",
    "reasonCode": "performance",
    "contractorId": "${contractorId}",
    "payableAmount": "{{BONUS_AMOUNT}}",
    "billableAmount": "{{BONUS_AMOUNT}}"
  }
}
```

Guard 1 keys off the reason TEXT, so if you change the `reason` wording you must change guard
1's `ILIKE` patterns to match, or the guard silently stops catching repeats.

Evidence on create and on the phase-2 update: `kind: "payout"`, with `formula` and
`valueCents` FLAT alongside `rationale` and `variables`.

---

## 7. Grant all role tags to EPMs on contract active

Name: `{{VERTICAL}}: Grant all {{VERTICAL}} role tags to EPMs on contract active`
Handler `tags`. Cron `0,15,30,45 * * * *`. `source_type: "snowflake"`.

Cron plus Snowflake rather than an event, because the role condition needs `JOBS.TITLE` and the
event trigger cannot filter on role.

Role match is deliberately TIGHT: exact `EPM` or containing `Expert Project Manager`. It does
NOT use the broader Team Lead / Project Lead / Project Consultant regex (Ryu, 2026-07-28).

`STATUS = 'active'` is deliberate and was NOT widened to `accepted`/`extended`: the automation
fires when a contract turns active. That is precisely why a one-off backfill is always needed
alongside it, since an EPM on an `extended` contract is never caught.

Drop `{{TAG_STUDIO_ADMIN}}` from the list if the vertical has no Studio Admin tag. Exclude
operational or cohort tags such as Abacus's `Sprint`; those track a work cycle, not access.

```sql
-- {{VERTICAL}}: contractors on this project whose ROLE is EPM / Expert Project Manager,
-- with an ACTIVE contract, who do not yet carry the {{VERTICAL}} EPM marker tag.
SELECT j.JOBID AS "jobId", j.CONTRACTORID AS "contractorId", j.COMPANYID AS "companyId"
FROM ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.JOBS j
WHERE j.PROJECTID = '{{PROJECT_ID}}'
  AND j.ISLATEST = 1
  AND COALESCE(j._FIVETRAN_DELETED, FALSE) = FALSE
  AND j.STATUS = 'active'
  AND (UPPER(TRIM(j.TITLE)) = 'EPM' OR j.TITLE ILIKE '%Expert Project Manager%')
  AND NOT EXISTS (
    SELECT 1 FROM ANALYTICS_DATABASE.AURORA_MERCOR_PRODUCTION.CONTRACTORTAGS ct
    WHERE ct.USERID = j.CONTRACTORID
      AND ct.TAGID = '{{TAG_EPM}}'
      AND COALESCE(ct._FIVETRAN_DELETED, FALSE) = FALSE)
QUALIFY ROW_NUMBER() OVER (PARTITION BY j.CONTRACTORID ORDER BY j.UPDATEDAT DESC) = 1
```

```json
{
  "body": {
    "mode": "add",
    "jobId": "${jobId}",
    "tagIds": [
      "{{TAG_ONBOARDING}}", "{{TAG_WORLD_BUILDER}}", "{{TAG_TASK_WRITER}}",
      "{{TAG_WORK_TRIAL}}", "{{TAG_ACTIVE_WRITER}}", "{{TAG_POD_A}}",
      "{{TAG_REVIEWER}}", "{{TAG_EPM}}", "{{TAG_STUDIO_ADMIN}}"
    ],
    "companyId": "company_AAABlLQjCsYYoXP4rsZKpY0y",
    "contractorId": "${contractorId}"
  }
}
```

The marker tag in the SQL guard MUST be the same `{{TAG_EPM}}` the body grants, or the
automation re-grants on every tick.
