---
name: add-vertical-calendars
description: Create the two Google Calendars a new Sparta vertical needs (Onboarding + Writer), share them to the vertical's own tag-synced Google groups so access grants and revokes itself, then paste the links into every Slack canvas that has a calendar slot. Also audits the existing verticals' calendars for the three defects this rollout keeps producing (world-readable onboarding calendar, contractor-alias owners, empty calendars). Use during a new-vertical spinup, or when someone says "spin up the calendars for <vertical>", "add the writer calendar", "the onboarding calendar link is missing from the canvases", "check the vertical calendars are set up right".
---

# Add the Onboarding + Writer calendars to a new Sparta vertical

Every Sparta vertical gets exactly two calendars. They are cheap to create and easy to get subtly wrong, and the failure mode is silent: a writer subscribes to a dead link, or an onboarding calendar quietly serves its full event list to the public internet. Distilled from the Abacus / Atria / Rampart / Cadre rollouts (Cadre 2026-07-28 is the clean reference).

Everything here is self-serve through `mcp__mercor-mcp__google_workspace_calendar_call` (methods `calendar.calendars.insert`, `calendar.acl.insert`, `calendar.acl.list`, `calendar.acl.patch`, `calendar.events.list`) plus `mcp__claude_ai_Google_Calendar__list_calendars` for a quick inventory. Canvas edits go through `mcp__mercor-mcp__slack_read_canvas` / `slack_update_canvas`; see the `editing-channel-canvases` skill for the canvas rules and the per-vertical canvas ID registry.

## The canonical shape

Two calendars, both `America/Los_Angeles`, named exactly `<Vertical> Onboarding Calendar` and `<Vertical> Writer Calendar`.

| Rule | Onboarding Calendar | Writer Calendar |
|---|---|---|
| Creator (Ryu) | owner | owner |
| `<vertical>-core-team-XXXX@mercor.expert` | owner | owner |
| `<vertical>-onboarding-XXXX@mercor.expert` | **reader** | not shared |
| `<vertical>-completed-wt-XXXX@mercor.expert` | not shared | **reader** |
| `domain:mercor.com` | freeBusyReader | freeBusyReader |
| `default` (public internet) | freeBusyReader | **no rule at all** |

The whole point of the group grants is that they are tag-synced audiences, so access follows the tag: someone who leaves onboarding loses the onboarding calendar, and only writers carrying `<vertical>_completed_work_trial` ever see the writer calendar. Never share these to individuals or to the `everyone` group; that breaks the auto-revoke.

Individual @mercor.com owners are OPTIONAL and vary by vertical (Carlota on all three legacy ones, Viraj on Abacus and Atria, Shaswat on Atria, Erick on Rampart). Cadre deliberately has none, because the Teams secondary-owner setup already reaches whoever needs it. Default to none and ask.

## HARD RULES

- **Get the group emails from `list_project_audiences`, never from `get_project_integrations`.** The integrations call returns the workspace-derived `<slugged workspace>-XXXX.admins@mercor.expert` / `.epms@` groups, which are NOT the groups the audiences actually sync into. The real ones are the `google` targets on the audience rows and follow `<vertical>-<name>-<projectsuffix>@mercor.expert`. Grabbing the wrong pair produces a calendar shared to an empty group, which looks fine and reaches nobody.
- **Decode every cid before you paste it anywhere.** The Slack link is `https://calendar.google.com/calendar/u/0?cid=<base64 of the calendar id, trailing "=" padding stripped>`. Base64-decode it back and byte-compare against the id Google returned. Atria shipped a dead onboarding-calendar link into three canvases on 2026-07-21 from a single transcribed digit and it was not caught until 7/23.
- **Pass `sendNotifications: false` on every `acl.insert`.** Otherwise Google emails the whole group "you have been given access" for a calendar that has zero events on it.
- **Never grant `owner` to an `@mercor.expert` alias.** Owner can delete the calendar and rewrite its sharing. Contractors and EPM aliases get reader through their group. Rampart violates this today.
- **A calendar with no events is not done.** Creating the calendars is the easy half; three of the six pre-existing vertical calendars are completely empty, so their links lead writers nowhere. Either seed the recurring sessions or tell the human explicitly that the links are hollow until someone does.

## Step 0 — Gather inputs

| Need | How to get it |
|---|---|
| Vertical name | the human |
| Teams project id | `list_projects(company_id=<Sparta>, query="<vertical>")` |
| The 3 Google group emails | `list_project_audiences(project_id=…)`, read the `google` targets |
| Individual owners (optional) | ask; default to none |

Sparta company is `company_AAABlLQjCsYYoXP4rsZKpY0y`. Confirm the three groups exist before creating anything: core-team (anchored to the `<Vertical> EPM` tag), onboarding (anchored to `<Vertical> Onboarding`), completed-wt (anchored to `<vertical>_completed_work_trial`). If the completed-wt audience has no `google` target yet, the human has to create the group first; a vertical can ship without it but the writer calendar then has no audience.

## Step 1 — Create both calendars

`calendar.calendars.insert` with `summary`, `timeZone: "America/Los_Angeles"`, and a one-line `description`. Two calls. Keep the returned `id` from each; that is the only place the real id is guaranteed correct.

The three legacy verticals have blank descriptions. Write one anyway (Vigil and Panacea do), it shows in the calendar list and costs nothing.

## Step 2 — Apply the ACLs

Four `acl.insert` calls on the onboarding calendar, three on the writer calendar, per the matrix above. All with `sendNotifications: false`. The creator's owner rule already exists; do not re-add it.

Then `acl.list` both and diff against the matrix. Confirm the writer calendar has NO `default` rule and that no `@mercor.expert` address holds `owner`.

## Step 3 — Build and verify the share links

Compute each cid, strip the trailing `=`, then verify:

```
printf '%s' "<calendar_id>" | base64 | tr -d '\n'          # strip trailing =
printf '%s==' "<cid>" | base64 -d                           # must byte-match the id
```

Both directions must agree before the link touches a canvas.

## Step 4 — Fill the canvases

Read the vertical's canvas IDs from the `editing-channel-canvases` registry. Six canvases take calendar links; read each one first and place the link where its TBD slot actually is rather than assuming.

| Canvas | Gets |
|---|---|
| Welcome to the `<Vertical>` Onboarding Channel | both |
| `<Vertical>` Onboarding Support: Read Before Posting | both |
| Welcome to `<Vertical>` (the all-members channel) | both |
| `<Vertical>` Pod A: Start Here | writer only, inside a callout |
| `<Vertical>` Information Station | writer only, inside a callout |
| `<Vertical>` Key Links (EPM hub) | both, appended as two link rows |

Key Links is the newest addition (Cadre 2026-07-28). Abacus, Atria, and Rampart Key Links still have no calendar rows; backfill them when convenient.

Canvas mechanics that will bite you:

- **A calendar line inside a `::: {.callout}` means resupplying the whole callout.** Reproduce every other line verbatim from the read you just did. Leave unrelated TBDs as TBDs.
- **`slack_read_canvas` prints live channel mentions `![](#C…)` back as `<#C…>`.** That is a display artifact, not broken text. When rewriting a block containing one, write `![](#C…)`; it round-trips.
- **`edit_type: append` still requires a `section_id`** even when you mean "end of canvas". Anchor to the last element's id.
- **Full-canvas `action=replace` is rejected** in these workspaces (`missing_required_field:section_id`). Use the `sections` array.
- The write-judge wants **every** link in a replaced paragraph sourced in `evidence`, including ones you did not change. Cite them as carried verbatim from the read.

Re-read each canvas after writing and diff against the pre-edit copy.

## Step 5 — Seed the recurring sessions (or say you did not)

Abacus is the only vertical with a real series: `<Vertical> - Onboarding Call - Morning` 9am PT and `- Evening` 4pm PT, weekdays, one shared Google Meet room on the onboarding calendar. Writer-calendar office hours are posted ad hoc.

Needs from the human: times, days, and who hosts. Without those, do not invent a schedule. State plainly that the calendars are empty and the canvas links currently lead to nothing.

Watch the timezone field: the Abacus series carries `timeZone: America/New_York` while its offsets are Pacific, so it reads as noon and 7pm to an East Coast viewer. Set `timeZone` to match the offsets you write.

## Step 6 — Audit the other verticals

Cheap, and it has caught something every time. `list_calendars`, then `acl.list` each vertical calendar:

- [ ] Any `default` rule at `reader` rather than `freeBusyReader`? That calendar's full event list is public. (Abacus onboarding was this until 2026-07-28.)
- [ ] Any `@mercor.expert` alias holding `owner`? (Rampart, both calendars, still open.)
- [ ] Any writer calendar carrying a `default` rule at all? It should have none.
- [ ] `events.list` each one: empty calendars mean hollow canvas links. (Atria x2 and Rampart writer were empty as of 2026-07-28.)
- [ ] Group grants present and pointing at the vertical's OWN groups, not a copied neighbour's.

## Step 7 — Log it

- Add both cids plus their decoded ids to the `editing-channel-canvases` registry under Fixed assets, and note which canvases were filled.
- Update the vertical's memory file.
- Tick the calendars row on the vertical's Startup Essentials `Checklist` tab.

## Done checklist

- [ ] Two calendars, named to convention, `America/Los_Angeles`, with descriptions
- [ ] ACLs match the matrix exactly; writer calendar has no public rule; no expert-alias owners
- [ ] Both cids decode back to the ids Google returned
- [ ] Six canvases carry the links; each re-read and diffed after writing
- [ ] Events seeded, or the human explicitly told the calendars are empty
- [ ] Other verticals audited on the four checks above
- [ ] Registry, memory, and Essentials checklist updated
