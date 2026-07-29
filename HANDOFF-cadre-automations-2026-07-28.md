# Cadre automations: DONE 2026-07-28, plus a cross-vertical audit

**All 5 remaining launch automations were created on Cadre as DRAFTS.** Cadre now has
6 automations: 1 active (the pre-existing contract-active tag grant) + 5 new drafts.
Nothing fires until a human activates it in the Teams UI.

| Automation | New Cadre id | Handler |
|---|---|---|
| Assign Pod A on World Created | `auto_AAABn6tVaIC_eunggJxFW5M_` | tags |
| Grant cadre_completed_work_trial on first World Created | `auto_AAABn6tXWwPDBobEHThMp7Zv` | tags |
| Bump writer hours 2 to 10 on spec doc approved | `auto_AAABn6tULhcvD3U8s41JAJKI` | update_hours |
| Bump writer hours 10 to 40 on first task RfD | `auto_AAABn6tUZ8c-KQFj7TJDcpuS` | update_hours |
| Onboarding Complete Bonus $800 **[AMOUNT UNCONFIRMED]** | `auto_AAABn6tXcR9LSaiyxntOxrQH` | bonus |

Teams: `https://team.mercor.com/company_AAABlLQjCsYYoXP4rsZKpY0y/projects/proj_AAABn6Z-4irb63tDd_NNRr5G?tab=integrations`

Every payload was substituted Abacus-to-Cadre and then **asserted free of Abacus
identifiers** before sending (project, campaign, WB golden world, job title, tag ids).
The build script is `build_cadre_automations.py` in the session scratchpad; it runs
`dry` to print the substitutions and the residue check, `go` to create.

## BEFORE ACTIVATING

**One must-fix: the $800 bonus and both hour ladders (2 to 10, 10 to 40) are Abacus's
numbers.** The playbook guardrail says confirm comp per vertical, never inherit. Confirm
Cadre's real numbers first.

**The "trigger mismatch" label is gone, but the milestone question is OPEN.** It was
created as `[TRIGGER MISMATCH]` because the Abacus source is named "on first task Ready
for Delivery" while firing on `World Created`. All three siblings (Abacus, Atria,
Rampart) fire on `World Created` and Rampart is named for it. **Which milestone is
CORRECT is still undecided** (Ryu, 2026-07-28) — do not treat World Created as settled
intent. Ryu's rule: the name must describe what it does now. Renamed to `Cadre: Grant
cadre_completed_work_trial on first World Created`; **no trigger change was made**, and
the milestone decision is still owed.

**Playbook follow-up:** Step 5 still reads "Grant completed_work_trial on first task
Ready for Delivery", which NO vertical implements. Update the master and Cadre playbooks
to say World Created.

## Three defects found in the Abacus source while cloning

1. **The completed_work_trial body has no `contractorId`.** `TagsBody` requires it, so
   that automation would fail validation and **could never have run on Abacus either.**
2. **`studio.task.status_change` exposes no `${contractorId}`.** Its fields are
   campaignId, createdBy*, jobId, ownedBy*, previousStatus*, projectId, qualifiesDone,
   task*, transitionedBy*, version, world*. Fixed on Cadre by using
   `${createdByUserId}`, the task AUTHOR, per the author-targeting rule. **Still
   unverified:** whether the event's `${jobId}` is the author's job or the
   transitioner's. Confirm before activating.
3. **Abacus's name describes behaviour it does not have** ('Ready for Delivery' vs a World Created trigger). Its name is wrong regardless of which milestone is eventually chosen.

## Cross-vertical audit of ALL Sparta automations (2026-07-28)

Pulled every automation on all 6 verticals and read each in full: Panacea 50 (36
active), Vigil 50 (24 active), Abacus 7 (1), Atria 10 (2), Rampart 6 (1), Cadre 6 (1).

**Zero cross-vertical id leaks.** No automation embeds another vertical's project id,
campaign id, world id or job title. Checked every sql, body and trigger_config.

**No active bonus or payout automation exists on any vertical.** No live money paths.

### FINDING 1: Panacea and Rampart share an Active Writer tag, both ACTIVE

`tags_AAABnYiHKEtdOhtigt1IUIft` is granted by BOTH:

- Panacea `auto_AAABnxERowtHlA-dXFRJTIzf` "Grant Active Writer tag on contract activation" — **active**
- Rampart `auto_AAABn40grBa_GSbm8pJNgIuV` "Grant Onboarding + Active Writer on contract active" — **active**

This is the bare-shared-tag collision the vertical-prefix rule exists to prevent, and
it is live. The `clone-vertical-automations` skill's own reference section admits the
Rampart run reused shared tags ("all returned existing/shared, not dedicated"), so this
was a known compromise that never got cleaned up. Rampart also shares
`tags_AAABnZflw34wRQLVfGVEa7yt` for Onboarding.

**Blast radius, checked:** NEITHER project has an audience anchored on that tag, so
nobody is getting wrong Studio/Slack/Insightful access from it today. The live harm is
reporting contamination: anything reading that tag sees Panacea and Rampart writers
mixed. The latent harm is that anchoring any audience on it later turns this into an
access problem instantly.

**Fix:** give Rampart dedicated `Rampart `-prefixed Onboarding and Active Writer tags
and repoint its automation, the same way Cadre has dedicated ones.

### FINDING 2: three verticals share the completed_work_trial tag (all draft)

`tags_AAABn05fDkO2qNlPVB5HDoFI` is used by Abacus, Atria and Rampart drafts. If any two
are activated, their work-trial rosters merge, which gates the Writer Calendar and the
active roster. **Cadre is the only vertical done right**, using its own
`tags_AAABn6mAHCODg46TUR1A9ZD0`, because the clone substituted it.

### FINDING 3: the same missing-contractorId defect sits in Rampart

Rampart `auto_AAABn40hKF7kPyNYaaJMtYA8` "Grant completed_work_trial on first World
Created" also omits `contractorId`, so it would fail validation if activated. Draft, so
harmless today. Note its name honestly matches its World-Created trigger, unlike
Abacus's, though that milestone still disagrees with the playbook's Ready-for-Delivery
intent.

## FIXES APPLIED to the other verticals' DRAFTS, 2026-07-28

Four draft automations repointed onto their own vertical's tags. **No active automation
was touched and Panacea was not touched at all** (verified still 50 automations, 36
active). The script refuses to edit anything whose state is not `draft`.

| Vertical | Automation | Change |
|---|---|---|
| Abacus | `auto_AAABn08kHckoPl1weaRPWIgt` | renamed to "on first World Created" (was "on first task Ready for Delivery", which nothing implemented); added `contractorId: ${createdByUserId}`. Tag unchanged, `tags_AAABn05fDkO2qNlPVB5HDoFI` is Abacus's own. |
| Atria | `auto_AAABn405u-kABDSYNdxJVq0A` | tag repointed from Abacus's shared work-trial tag to Atria's own `atria_completed_work_trial` `tags_AAABn5tfEp_Ojn5yohRDDY_Z`; renamed from "(event, cloned from Abacus)". |
| Rampart | `auto_AAABn40hKF7kPyNYaaJMtYA8` | tag repointed to Rampart's own `rampart_completed_work_trial` `tags_AAABn5tgSgrHUFU526NNwKs7`; added `contractorId: ${createdByUserId}`. |
| Rampart | `auto_AAABn40g6WC87yjAjzZGXrPI` | Pod A tag repointed to `Rampart Pod A` `tags_AAABn5tcp_L-j6vGBbxHZ55_`, **in both the body and the SQL NOT EXISTS dedup guard** (leaving the guard on the old tag would re-grant on every cron tick). |

These were functional bugs, not tidiness. `Rampart Pod A` is the anchor of the audience
that targets slack `rampart-pod-a`, and `rampart_completed_work_trial` anchors the one
targeting google `rampart-completed-wt`. Granting a different tag meant the writer never
reached either, and the work-trial group gates the Writer Calendar and the Expert Facing
Drive folder.

**Post-fix scan is clean except one deliberate leave-alone:** no tags automation is
missing `contractorId`, no name misdescribes its trigger, and the only remaining
multi-vertical tag is `tags_AAABnYiHKEtdOhtigt1IUIft`, shared by Panacea's and Rampart's
**active** contract-activation automations. Ryu chose to leave the active ones alone.

### Still open on Rampart's active automation

It grants Panacea's `tags_AAABnYiHKEtdOhtigt1IUIft` while `Rampart Active Writer`
`tags_AAABn5tcoYZ5opTJDzxF0KK3` **already has 22 members and a studio target**, so
Rampart's writers are on the dedicated tag by some other route while the automation
grants a different one. Repointing it is two tag ids, but it is live and any writer
already tagged stays on the old tag, so it needs a backfill decision. No audience is
anchored on the shared tag in either project, so nothing is mis-granting access today.

## NEW: EPM auto-tag automation, all 4 spun-up verticals (2026-07-28)

On contract active, if the contractor's ROLE is EPM / Expert Project Manager, grant every
role tag specific to that project. Created as DRAFTS on all four. Script:
`epm_autotag.py <dry|go> <Vertical>` in the session scratchpad.

| Vertical | Automation id | Tags | EPM role exists? |
|---|---|---|---|
| Cadre | `auto_AAABn6uMwe9chk2kDoRMvZmn` | 9 | yes |
| Abacus | `auto_AAABn6uNWB0Na_G0j5FHrYnU` | 9 | yes |
| Atria | `auto_AAABn6uNk5IXrPMqPPFOhYHy` | 9 | yes |
| Rampart | `auto_AAABn6uOF5dy4kHJGGhOjrjA` | 8 | **NO** |

Design: cron `0,15,30,45 * * * *` + Snowflake (the role condition needs `JOBS.TITLE`, and
the event trigger cannot filter on role). Scoped by `PROJECTID`, `STATUS='active'`,
`ISLATEST=1`, and a **tight** role match — exact `UPPER(TRIM(TITLE))='EPM'` or `TITLE
ILIKE '%Expert Project Manager%'`. It deliberately does NOT use the broader Team Lead /
Project Lead / Project Consultant EPM regex, per Ryu's ask.

**Dedup guard** is the project's own EPM marker tag, which the automation itself grants,
so each EPM is processed once. **Consequence:** an EPM who already carries the EPM tag but
is missing the others will NOT be picked up. That is what the backfill is for (Abacus has
12 EPM-tagged, Atria 6, Rampart 1, Cadre 1).

### The tag ownership matrix, which is the reason this is safe

Built from every project's audience anchors and cross-checked across all six Sparta
verticals. **No tag id anchors more than one project's audiences.** Bare tag NAMES are
not the tell: Abacus, Atria and Rampart all have bare-named `Active Writer` / `Onboarding`
/ `Reviewer` tags that are genuinely their own distinct ids. Judge by id, never by name.

The build script asserts, per vertical, that no granted id appears in any other vertical's
grant list, and the post-create verification re-reads all four and confirms zero foreign
tags and zero other-project ids in the SQL. All four PASS.

**Excluded per Ryu:** operational/cohort tags. Concretely Abacus's `Sprint`
(`tags_AAABn0oCIOmsT_MROQtJNqR8`, 12 members) tracks a work cycle, not access.

### Flags before activating

- **Rampart has NO EPM role**, only `Insurance Expert`. Its automation matches nobody and
  is inert until an EPM role is created. Built as a draft on purpose so it is ready.
- **Rampart has no Studio Admin tag**, hence 8 tags rather than 9.
- **Atria's `Onboarding` audience has ZERO targets**, so granting that tag confers nothing.
  Worth wiring or removing.
- **EPMs will appear in writer-stage rosters** (Active Writer, Onboarding, etc.). SVA and
  the daily emails exclude EPMs by title/role regex rather than by absence of writer tags,
  so metrics should be unaffected — but verify before activating.
- The `<Vertical> EPM` audience already grants most access on its own (Cadre's carries 8
  targets: studio admin, core-team group, Insightful, 5 Slack channels). This automation's
  added value is the remaining tags, not access from zero.

### Backfill: DONE 2026-07-28

21 people granted their vertical's full role-tag set, verified complete on a spot-check of
one recipient per vertical. Script: `backfill_epm_tags.py <dry|go>`, driver
`add_contractor_tag(tag_id, user_ids[])` which is idempotent.

| Vertical | Recipients | Tags each |
|---|---|---|
| Cadre | 2 (Ryu, **Chaya Tong**) | 9 |
| Abacus | 12 | 9 |
| Atria | 6 | 9 |
| Rampart | 1 (Michael Kaiser) | 8 |

**Previewing first is what made this safe.** The EPM tag is NOT a reliable proxy for "is
an EPM". Cross-checking every tag holder against `JOBS.TITLE` and contract status found
four who are not EPMs by role:

| Vertical | Person | Actual title | Ryu's call |
|---|---|---|---|
| Abacus | Dylan Matthews | External Expert Consultant | **include** |
| Abacus | Nadum | External Expert Consultant | **include** |
| Rampart | Michael Kaiser | Insurance Expert (writer) | **include** |
| Abacus | Hua Xin You | **no job on this project at all** | **EXCLUDE** |

Hua Xin You was verified untouched afterwards: still holds only the Abacus `EPM` tag and
none of the other 8.

**Going forward** (Ryu): non-EPM-role people get tagged **by hand by an EPM**. The
automation only picks up genuine EPM-role contracts, and only when the contract **turns
active** — so `STATUS='active'` is correct as built and was deliberately NOT widened to
`accepted`/`extended`. Consequence to remember: Chaya Tong is on an `extended` contract
and would never have been caught by the automation, which is precisely why the backfill
was needed.

### What the backfill actually changed

Of **188** (person, tag) memberships across the 21 recipients, **112 already existed and
76 were new.** 19 of the 21 recipient slots gained at least one tag; two already had the
full set (Ryu on Cadre, Muhammad Jamal Akhtar on Abacus).

| Vertical | already had | NEW | total |
|---|---|---|---|
| Cadre | 10 | 8 | 18 |
| Abacus | 76 | 32 | 108 |
| Atria | 21 | 33 | 54 |
| Rampart | 5 | 3 | 8 |
| **TOTAL** | **112** | **76** | **188** |

The consistent gap was the mid-pipeline stage tags: `World Builder`, `Task Writer`,
`completed_work_trial` and `Pod A` were what most EPMs were missing. Atria's EPMs were the
least provisioned (33 of 54 memberships were new; four of them were missing 6-7 tags each).

**`CREATEDAT` is `TIMESTAMP_TZ` in UTC — do NOT classify "was this just created" with a
date-string prefix.** Doing so during a PT evening compares against the wrong UTC date and
silently misreports. Use `DATEDIFF(minute, CREATEDAT, CURRENT_TIMESTAMP())` and a
freshness window instead. The rows split cleanly bimodal: 5 minutes old (the backfill) vs
~26,098 minutes (~18 days). A first pass using the string check produced badly wrong
numbers, caught only because it claimed Ryu held no Cadre tags while the Cadre EPM
audience already listed Ryu as its single member.

### Two tooling findings worth keeping

- **`preview_audience_members` UNDERCOUNTS.** It reported 12 for Abacus and 1 for Cadre;
  the `CONTRACTORTAGS` truth is 13 and 2. It appears to drop people with no job on the
  project (Hua) and missed Chaya Tong entirely. **Do not use it to establish a population.**
  Query `CONTRACTORTAGS` joined to `JOBS` instead.
- **`add_contractor_tag` takes `tag_id` + `user_ids[]`**, is idempotent, needs no evidence
  block, and returns `{tagId, tagged}`. One call per tag with the whole recipient list is
  the efficient shape (35 calls for this backfill).

## Skill corrections owed to `clone-vertical-automations`

Its instructions produced two of the problems above and should be fixed:

1. It says to call `create_tags` with bare names. That returns shared company-wide tags.
   Use dedicated vertical-prefixed tags and read their ids from
   `list_project_audiences` anchors.
2. It says to reuse the shared `completed_work_trial` tag `tags_AAABn05fDkO2qNlPVB5HDoFI`
   unchanged. That is what created FINDING 2. Each vertical needs its own.
3. It should warn that `create_automation` requires `contractorId` in a tags body, that
   `studio.task.status_change` has no `${contractorId}`, and that payout evidence needs
   `formula` + `valueCents` **flat on `evidence`**, not nested under a `payout` object.

---

## Original handoff (superseded, kept for the identifier tables)



Stopped here deliberately. Everything below is resolved and verified live; what
remains is the id-substitution step, where a single wrong id creates an automation
that pays bonuses or rewrites hour caps on **Abacus** writers instead of Cadre's.
That is not a step to rush at the end of a long session.

Follow the `clone-vertical-automations` skill, with the three deviations noted below.

## Source and target

| | |
|---|---|
| SOURCE | Abacus `proj_AAABn0Um0Wr19Gj_ql9JHKSh` |
| TARGET | Cadre `proj_AAABn6Z-4irb63tDd_NNRr5G` |
| Company | Sparta `company_AAABlLQjCsYYoXP4rsZKpY0y` |

Abacus has 7 automations: 1 active + 6 drafts. Cadre has 1, the active one, already
equivalent. So **5 to clone**, not 6. See the exclusion below.

## Cadre identifiers, all verified live this session

| What | Value | Source |
|---|---|---|
| Role / job title | `Human Resources Expert` | `get_project include=roles` (also has an `EPM` role) |
| Studio campaign | `camp_35e49895edea4ad7b822d8347dab6c4c` | memory + live |
| WB golden world | `world_f68670e0b59d4a13b4658a3e1ed2a6ee` | memory |
| Tasking world | `world_585c8fd8aff14903916f4a279d5b9735` | live `GET /worlds/...` |
| Studio company / account | `comp_2fa4115109d741cd94a3c409ed89e61f` / `acct_be8f7fcc2c554b33baa5a0c9d05496e3` | shared Sparta |

**Cadre tag ids, read live from `list_project_audiences` anchors.** These are
DEDICATED Cadre-prefixed tags, which is the whole point:

| Tag | Id |
|---|---|
| `Cadre Onboarding` | `tags_AAABn6mAB_bxog3d-LlMMKqF` |
| `Cadre Active Writer` | `tags_AAABn6mAC-UIM3rhyoJO24SB` |
| `Cadre Pod A` | `tags_AAABn6mAIJq2LF1RIadN25yR` |
| `cadre_completed_work_trial` | `tags_AAABn6mAHCODg46TUR1A9ZD0` |
| `Cadre World Builder` | `tags_AAABn6mAGAhaUxkMN-VOHrVy` |
| `Cadre Task Writer` | `tags_AAABn6mAE1CGbLMn23NPuosU` |
| `Cadre Reviewer` | `tags_AAABn6mAEBmEoU3XhDlJDZnf` |
| `Cadre EPM` | `tags_AAABn6mAATXzJa4p4w1D1IKy` |
| `Cadre Studio Admin` | `tags_AAABn6mALHLEk_rotq5Lwa39` |

## THREE DEVIATIONS from the skill. Read these before running it.

1. **Do NOT call `create_tags`.** The skill tells you to, and warns that it returns
   existing company-wide shared tags rather than dedicated ones. Cadre already has
   dedicated prefixed tags, listed above. Calling `create_tags(["Onboarding",
   "Active Writer","Pod A"])` would hand back the SHARED Sparta tags and the
   automations would then act across verticals. Use the ids in the table.

2. **Do NOT reuse the shared `completed_work_trial` tag.** The skill says to reuse
   company-wide `tags_AAABn05fDkO2qNlPVB5HDoFI` unchanged. That is wrong for Cadre,
   which has its own `cadre_completed_work_trial` = `tags_AAABn6mAHCODg46TUR1A9ZD0`.
   Using the shared one cross-contaminates verticals. This is the vertical-prefix
   rule; the skill predates it and should be corrected.

3. **Clone 5, not 6. Exclude the $300 one.** Abacus's `Abacus: First World Created
   Bonus Payment ($300) [UNCONFIRMED]` (`auto_AAABn2MzHm4pF_9U87VCQpO_`) carries its
   own note: *DRAFT, DO NOT ACTIVATE, milestone UNCONFIRMED*, and says the official
   Abacus onboarding doc defines a single $800 payment. It is not in the canonical
   6 and not in the startup playbook. Do not propagate an unconfirmed milestone to
   a new vertical. Raise it with Ryu instead.

## The 5 to clone

Fetch each with `get_automation(<id>)`; `list_automations` does NOT return `sql` or
`body`, only metadata.

| # | Abacus id | Name | Handler | Trigger |
|---|---|---|---|---|
| 1 | `auto_AAABn08ibnfR1Ok-QI1CW5nJ` | Assign Pod A on World Created | `tags` | cron `0,15,30,45 * * * *` |
| 2 | `auto_AAABn08kHckoPl1weaRPWIgt` | Grant completed_work_trial on first task RfD | `tags` | event |
| 3 | `auto_AAABn2MxHUiJUL5XkhRK_5FB` | Bump writer hours 2 to 10 on spec doc approved (WB golden) | `update_hours` | cron `0,15,30,45 * * * *` |
| 4 | `auto_AAABn2Mx2W0MzD2SmklNAb-J` | Bump writer hours 10 to 40 on first task RfD | `update_hours` | cron `0,15,30,45 * * * *` |
| 5 | `auto_AAABn2MyfUVjGwE2gp5Hvob6` | Onboarding Complete Bonus Payment ($800, spec doc approved) | `bonus` | cron `0 * * * *` |

Already done, do not re-create: `Add Onboarding and Active Writer tags on Contract
= Active`, **active** on Cadre.

## Substitution checklist, per automation

In both `sql` and `body`, replace Abacus to Cadre for:

- project id `proj_AAABn0Um0Wr19Gj_ql9JHKSh` to `proj_AAABn6Z-4irb63tDd_NNRr5G`
- `j.TITLE IN ('<Abacus title>')` to `'Human Resources Expert'`
- Abacus WB world id to `world_f68670e0b59d4a13b4658a3e1ed2a6ee`
- Abacus tasking world id to `world_585c8fd8aff14903916f4a279d5b9735`
- Abacus campaign id `camp_930d4d8b84d2436497b2f3fcf79d483c` to `camp_35e49895edea4ad7b822d8347dab6c4c`
- every team-tag id to its Cadre equivalent above

Leave alone: status ids (`98680cd3` World Created, `ba9f81f7` RFD,
`planning_done_pipeline`), `companyId`, and any `${...}` placeholder.

**Verify same-lineage first.** The tasking world's `/worlds/` response must list
`ba9f81f7-...` in its Review custom-view filters. Cadre was cloned from
`[CLONE ME] Sparta Professionals Campaign`, the same lineage as Abacus, so it should
hold, but confirm rather than assume. If absent, STOP and resolve real status ids.

**After substituting, grep each payload for `Abacus`, `AAABn0Um`, `930d4d8b`, and
every Abacus world id.** Zero hits, or you have a cross-vertical automation.

Create all 5 as **DRAFT**. `create_automation` always returns draft. A
`"SQL returned 0 rows"` warning is EXPECTED on a vertical with no writers yet.

## Flag to Ryu before anyone activates

- The **$800 bonus and both hour ladders (2 to 10, 10 to 40) are inherited from
  Abacus and unconfirmed for Cadre.** Confirm Cadre's real comp numbers first; the
  playbook's guardrail section explicitly says do not inherit amounts from another
  vertical.
- The bonus automation needs its self-ID dedup guard added.
- Ryu activates in the UI. Never activate from here.

## Tooling note

`mercor-mcp` is not mounted (its `tools/list` times out on 739 schemas). Every call
above went through the keychain-token bridge `coil.py`; see the tooling section of
`HANDOFF-playbook-sync-2026-07-28.md` for how to rebuild it.
