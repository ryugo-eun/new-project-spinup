---
name: replace-instructions-link
description: >
  Replace every inherited link in a new Sparta vertical's platforms, across RL Studio, Mercor Teams,
  Slack and Drive, in one pass. A spinup clones its campaign, its automations, its canvases and its
  Drive tree from a live vertical, and every one of those clones carries the SOURCE vertical's writer
  instructions doc and onboarding calendar, so a brand-new vertical silently points its writers at
  Vigil's or Abacus's material. This owns all six surfaces that bake a per-vertical link in, not just
  the Studio world layouts. Runs as runbook step 14, the LAST build step before the audit, once the
  instructions doc (step 12), the canvas set (step 13) and the two calendars (step 9) all exist.
  Moved from 13 to 14 on 2026-07-29 because surface 4 rewrites canvases, so it has to run after they
  are created, not before. Use during a new-vertical spinup, or for "swap the instructions link",
  "the worlds still link Vigil's instructions", "fix the links for <vertical>", "the welcome DM sends
  writers to the wrong doc", "replace the calendar link everywhere".
---

# Replace a new vertical's inherited links

Every Sparta vertical is cloned off the Vigil lineage (Vigil to Abacus to Atria to Rampart to Cadre),
and per-vertical links are hard-coded, not resolved. So a clone looks finished and points writers at
another vertical's material. Nothing warns anybody.

**This is a spinup step, scoped to one vertical.** It fixes the vertical named in the inputs plus the
clone template that vertical came from. It is not a Drive-wide link cleanup.

`reference/link-map.md` is the audit of which spinup skill creates each link and which ones ship a
stale copy. Read it before calling any surface clean.

## The link classes

| Class | Where the canonical value comes from | Spinup step |
|---|---|---|
| Writer instructions doc | the vertical's own Google Doc in its `Expert Facing` folder | 12 |
| Onboarding calendar | `add-vertical-calendars`, the onboarding-tag calendar | 9 |
| Writer calendar | `add-vertical-calendars`, the completed_work_trial calendar | 9 |
| SVA dashboard | `sva-pi.vercel.app/campaigns/<campaign_id>/` | optional, step 16 |
| Onboarding checklist app | the vertical's checklist site, if it has one | manual |
| Slack channel links | the vertical's own nine channels | 6 |

The last three are in scope only where they sit in a field this skill is already rewriting. Do not go
hunting for them.

## Known inherited values to search for

| Vertical | Instructions doc id |
|---|---|
| Vigil (the lineage root, and the one clones carry) | `1nvj9D-IW7dBQyn-lOaXTINZoxVEJJ1R4GwzNgMOUi7U` |
| Abacus | `1u-Go8CrHhzLwss4p1SqX9WiTNs3vJVmmG5bdKvBByws` |
| Atria | `1iyyef-zgJcIu0vnwjvk9qVFsPaMoanRGmIlJ5KFs-SU` |
| Rampart | `1WcKj4snqF4yHX1LdS1VWV6AOpsjGbseGUrBbRq_Mkcs` |

The Vigil doc is titled `[EXP] Project Vigil - Onboarding Document`, which is why people scanning
file names never notice it is the instructions doc.

Vigil's onboarding calendar, carried by cloned automations, is the `cid` beginning
`Y19iYzEzMmZmNDRjOGFiMDBkZjdhYTNiOTFmZWZlOTQ3MWZiZTYyMzZjODQ4MWIzOGExMWU2YzY2MmUzODdjYmQ1`.

**Search for every one of these, not just Vigil's.** Cloning moved on from Vigil: Atria, Rampart and
Cadre each inherited **Abacus's** doc id, so a Vigil-only scan reports a clean vertical that is not.

## Inputs to collect first

Ask in one pass, read it back, write nothing until the operator confirms.

| # | Ask | Notes |
|---|---|---|
| 1 | Vertical name, and the source vertical it was cloned from | the source's ids are what you search for |
| 2 | Studio `campaign_id` | surface 1 |
| 3 | Teams `project_id` | surfaces 2 and 3 |
| 4 | New instructions doc id | must already exist. If it does not, stop and run step 12 first |
| 4b | Confirm the canvas set EXISTS | surface 4 rewrites canvases, so they have to be there. If `create-vertical-canvases` has not run, stop and run step 13 first rather than reporting surface 4 clean against zero canvases |
| 5 | Both calendar links, copied whole | a retyped `cid` is a silent dead link |
| 6 | The vertical's Drive folder id | scopes surface 5 to this vertical |
| 7 | Which surfaces to run | default all six. Named exclusions only |

If input 4 does not exist yet, stop. Swapping a link to nothing is worse than the inherited link,
because the inherited one at least renders.

## Premortem

| Failure | Guard |
|---|---|
| The whole URL gets replaced, dropping a `?tab=` or `#heading=` suffix, so writers land on page one of a 26-tab doc | Replace the **doc-id substring**, never the URL. Both live Vigil automations and the Abacus onboarding doc carry `?tab=...#heading=...` |
| Half the occurrences get fixed because each link is written twice | Every markdown self-link `[url](url)` holds the id twice. Count occurrences before and after and expect an even number |
| Only Vigil's id is searched, so an Abacus-derived vertical reports clean | The table above. Search all four |
| A surface is skipped because there was no procedure for it | The scorecard has one row per surface, and a skip needs a written reason |
| The Studio PATCH wipes `world_settings` | The script reads the whole object, edits two fields, PATCHes it all back. Never hand-build a partial |
| The onboarding doc gets truncated | `set_project_onboarding_doc` upserts and does not diff. Pass the FULL markdown, edited, every time |
| An automation is edited and silently stops firing | `update_automation` re-runs the SQL and template preview, and its judge can stick. Verify state after, and recreate via `create_automation` if it blocks |
| A calendar `cid` is retyped, so the link renders and is dead | Copy links whole, then base64-decode the `cid` and match it to the live calendar id. Atria's onboarding calendar was dead for two days from a one-character typo |
| The link is fixed and the sentence around it still says "hub" | Surface 4. The prose moves with the link |
| The next vertical inherits the same defect | Surface 6. The clone template is a surface, not an afterthought |

## The six surfaces

Run in this order. 1 to 3 are the ones writers hit first.

### 1. Studio world layouts

The `instructions_card` modules in `world_settings.module_layout` and `module_layout_draft`. Roughly
5 + 5 occurrences in a `[Live New Flow] Final Tasking World` and 3 + 3 in a
`[LIVE] Golden World Building`.

```
set -a; . ~/Desktop/MERCOR/.env.local; set +a
python3 replace_instructions_link.py scan <campaign_id> <old_doc_id>
python3 replace_instructions_link.py replace <world_id> <campaign_id> <old> <new> --dry-run
python3 replace_instructions_link.py replace <world_id> <campaign_id> <old> <new>
```

Scan once per inherited id from the table. Confirm the world list with the operator before writing,
these are live worlds writers see. Verify: the script prints `VERIFY new_id_count=N old_id_count=0`.

### 2. Teams onboarding doc

Holds the instructions link in its "read the project instructions" step, and often the checklist app
and two Slack channel links.

- Locate: `get_project_onboarding_doc(project_id)`, then search the returned markdown for each
  inherited id.
- Replace: edit the doc-id substring in the markdown, then `set_project_onboarding_doc` with the
  **entire** edited body.
- Verify: `get_project_onboarding_doc` again, confirm the new id is present, the old is gone, and the
  document did not shrink except by the id swap.

### 3. Teams automations, only if the set was cloned

**Usually empty on a new vertical. Check, do not assume.** Verified 2026-07-29: Abacus, whose set was
authored from the `provision-vertical-automations` templates, has 8 automations, all `tags`, `bonus`
and `update_hours`, and no messaging automations at all. The templates carry no links, so an authored
set is clean.

This surface only carries links when someone ran `clone-vertical-automations` and copied a legacy
vertical's set across. Vigil, hand-built, has a welcome DM and an onboarding nudge whose bodies each
carry the instructions doc **and** the onboarding calendar, each written twice as a markdown
self-link. Cloning those brings Vigil's links with them.

So: run this surface if the vertical's automations were cloned, or if it predates the template set.
One `list_automations` call settles it, so check either way.

- Locate: `list_automations(project_id, limit=100)`, then `get_automation` on every automation whose
  `handler_name` is a messaging handler (`send_slack_message_as_bot`, `send_slack_message`,
  `send_email`). Search `body`, and separately search `notes` and `description`.
- Replace: `update_automation(automation_id, body=<edited body>)`. Leave `sql`, `trigger_config` and
  `reasons` untouched.
- Notes and descriptions carry stale ids as provenance citations. Fix them too, in the same call,
  because the next person cloning this vertical reads them as fact.
- Verify: `get_automation` again for the id counts, and confirm `state` is unchanged. An automation
  that was active must still be active.

### 4. Slack canvases

The largest surface by count: **7 to 9 canvases carry the instructions link, and 6 carry the
calendars.** Rampart's 2026-07-23 pass touched nine (announcements, general, EPM Start Here, Key
Links, onboarding welcome, onboarding support, Pod A Start Here, Information Station, reviewers). Read
the `editing-channel-canvases` registry for this vertical's actual set rather than assuming a count.

Delegate the writing to `sweep-canvas-links`, which owns the label convention
(`<Vertical> Instructions`, never "Hub"), the calendar slots and the TBD fills. Do not reimplement it.

Three things to carry into that run:

- **The link is a per-vertical Google Doc, not the Instructions Hub.** The convention flipped to the
  hub on 2026-07-21 and was reversed on 2026-07-23. The hub still has no per-vertical content, so do
  not re-point at it. See `reference/link-map.md`.
- **Fix the prose with the link.** "Read the Instructions Hub", "reading through the hub" and "the
  hub's FAQ" all had to change too. A canvas with a correct link and a sentence that still says "hub"
  is not done.
- **Key Links calendar rows exist for Cadre only.** Abacus, Atria and Rampart still need them.

Report the remaining-TBD count into this skill's scorecard.

### 5. Drive, inside this vertical's own tree

- Locate: `drive.files.list` with `q: "fullText contains '<old_doc_id>'"`, plus
  `includeItemsFromAllDrives`, `supportsAllDrives` and `corpora: allDrives`. Run it once per
  inherited id. Then keep only the files under this vertical's folder id from input 6, and list the
  rest as a cross-vertical leak, report-only.
- Replace: Docs via `docs.documents.batchUpdate` `replaceAllText` on the doc-id substring. Sheets via
  `sheets.spreadsheets.batchUpdate` `findReplace`. The EPM Training doc is the usual hit.
- Verify: re-run the same search and confirm this vertical's files no longer appear.

### 6. The clone template

`{{VERTICAL}} EPM Training`, `1WJbvFBSQ-ViMPq4Css43GNCmrdnfTpPd8uGpq4JqAac`, inside
`[INT] Project {{VERTICAL}}` in `_CLONEME (New Vertical Template)`.

It carries a live vertical's instructions link, so every future spinup inherits it. The template must
point at **no** vertical: replace the link with the literal `{{INSTRUCTIONS_DOC_URL}}` token so
`new-vertical-drive-folder` treats it like the other placeholders and the gap is visible instead of
silently wrong.

Verify: `fullText contains` each of the four ids returns zero template files.

### Out of scope: listings

Checked 2026-07-29. Sparta listing descriptions carry no instructions or calendar link, and the offer
template is not writable by `create_listing` or `edit_listing`. A writer-instructions doc is
post-hire and confidential, so it should never be in a public listing. If you find one there, that is
a confidentiality issue to escalate, not a link to swap.

## Scorecard

Six rows, each PASS, FAIL or SKIPPED with a reason, plus the cross-vertical leaks found in surface 5
as a separate report-only list. Per row give the before and after occurrence counts. "The doc exists"
is not the deliverable. Six surfaces pointing at this vertical is.

## Verify

```
python3 replace_instructions_link.py scan <campaign_id> <each old_doc_id>   # expect zero worlds
get_project_onboarding_doc <project_id>                                     # new id present, old absent
get_automation <each messaging automation>                                  # new id, old gone, state unchanged
drive.files.list fullText contains '<each old_doc_id>'                      # none under this vertical
```

## Gotchas

- **The id, not the URL.** URL forms differ per vertical: Abacus uses `/edit?tab=...#heading=...`,
  Rampart uses `/mobilebasic`. Replacing the URL throws the suffix away and breaks the deep link.
- **Links are written twice.** `[url](url)` is the house style in automation bodies, so a "1 hit"
  report usually means you found half of them.
- **Cloning is no longer Vigil-only.** Atria, Rampart and Cadre inherited Abacus's doc id. Scanning
  for Vigil's id alone gives a false clean.
- **A cloned automation cites its source in the notes.** That is how the wrong doc id survives a
  correct body fix and gets copied into the next vertical.
- **The instructions hub is not a destination.** The DB-backed app carries no per-vertical content
  yet, so do not point writers at it as though it were live.
- **Not a git repo.** This folder is not version-controlled, so changes here are not committed.
  Mirror any edit into `~/.claude/skills/replace-instructions-link/` or the installed copy drifts.

## Hand off

1. `sweep-canvas-links`, for surface 4.
2. `verify-vertical-spinup`, which re-checks that the link actually landed.
3. If surface 5 reported cross-vertical leaks, hand that list to the owning vertical's EPM. This
   skill does not fix other verticals.
