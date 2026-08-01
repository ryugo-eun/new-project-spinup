---
name: create-vertical-canvases
description: >
  Create the full Slack channel-canvas set for a NEW Sparta vertical by cloning the canonical
  Abacus 15-canvas set into the vertical's Slack workspace and adapting each: title prefixed with
  the vertical name, domain wording swapped, every channel mention repointed to the vertical's
  channels, SVA dashboard + Insightful timer set, and every vertical-specific link left as an
  explicit TBD (never invented). Use when standing up a new Sparta vertical whose channels have no
  canvases yet. Triggers on "make the canvases for <vertical>", "create the channel canvases for
  <vertical>", "clone the canvas set into <vertical>", "build the best canvases for <vertical>".
  For EDITING an existing set or filling a single TBD, use `editing-channel-canvases` instead.
metadata:
  author: ryugo-eun
  outbound_writes: true
---

# Create vertical channel canvases (clone the Abacus set)

The canvas-creation step of a new-vertical spinup. Studio/Teams/Slack channels come from
`clone-sparta-campaign`; the Drive folder from `new-vertical-drive-folder`; this skill fills the
new vertical's Slack channels with their canvases. `editing-channel-canvases` EDITS an existing
set; this skill BULK-CREATES a new vertical's set from the Abacus template.

## Tools

`mcp__mercor-mcp__slack_create_canvas`, `slack_read_canvas`, `slack_update_canvas`. Every call
needs `workspace` = the vertical's Slack workspace NAME (not URL). Do NOT use the
`mcp__claude_ai_Slack__*` variants; they only see the Mercor workspace, not vertical workspaces.
Each create/update is a state-changing call and needs `evidence` (source the channel IDs, campaign
id, and domain).

## Inputs to collect first

- **VERTICAL** — project name, e.g. `Cadre`.
- **DOMAIN** — human domain label. Pull it from `get_project(project_id, include=['roles'])` →
  the Writer role's `role_title` (e.g. "Human Resources Expert" → DOMAIN = Human Resources).
- **Slack workspace name** — if unknown, call any `slack_read_canvas` with a bogus `workspace`;
  the error lists all available workspace names (e.g. Cadre = `Hr - sparta vertical`).
- **Channel IDs** — `slack_search_channels(query="<vertical>", channel_types="public_channel,private_channel")`.
  Most vertical channels are PRIVATE, so include private in the search.
- **Studio campaign id** — for the SVA dashboard link `https://sva-pi.vercel.app/campaigns/<campaign_id>/`.

## Source set (read these, workspace `Abacus`)

**The canonical set is 15** (settled 2026-07-29). It was 13; the Reviewer Roster and Weekly
Availability canvases were built on Cadre first and are now part of the default set. Create all 15.

The canonical canvases + their Abacus source IDs live in the Abacus table of
[../editing-channel-canvases/reference/canvas-registry.md](../editing-channel-canvases/reference/canvas-registry.md).
Read each source canvas, then create the adapted copy. The set, by target channel:

| Target channel type | Canvas | Notes |
|---|---|---|
| epms | EPM Start Here · EPM Roster · Key Links · Reimbursements and Bonus Forms | 4 canvases |
| pod-a | Pod A: Start Here · Information Station | 2 canvases |
| onboarding | Welcome to the <V> Onboarding Channel! · Onboarding Support: Read Before Posting | both here if no separate support channel |
| reviewers | Welcome, <V> Reviewers! | |
| announcement(s) | <V> Announcements: Start Here · Welcome to <V> | Welcome goes in a general channel if one exists, else the announcement channel |
| maven-support / robot-advice | Meet Maven: How to Use This Channel | |
| technical-issues | Technical Issues: How to Get Help | |
| epms | Weekly Availability | **`#<v>-epms` ONLY.** Ryu, 2026-07-29: reviewers do not need it, EPMs do. Cadre's copy was shared into both channels; do not repeat that. LOCKED FORMAT (from the Abacus EPM template, confirmed on Cadre 2026-07-28): an intro line `Weekdays 9-5 unless otherwise stated.` then a table with columns `EPM Name | Sunday | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday` and ~20 blank rows. It is a day-of-week grid — NOT a per-person prose block and NOT a timezone/general-schedule/OOO table. |
| reviewers | Reviewer Roster | blank roster, one line per reviewer: name - role (pod) - timezone - availability; parallels EPM Roster |

## Adaptation rules (the core of this skill)

1. **Every title carries the vertical name** so it's obvious which canvas belongs to which channel
   (`EPM Roster` → `<V> EPM Roster`, `🔗 Key Links` → `🔗 <V> Key Links`, etc.). Ryu's hard rule.
2. **Body excludes the title heading** — `slack_create_canvas` takes the title as its own param;
   a `# Title` in the body duplicates it. Start the body at the first `##` section.
3. **Domain swap:** Abacus → `<V>`, and accounting → `<DOMAIN>` wording. The onboarding/Welcome
   "What is <V>?" line becomes "`<V>` is a `<DOMAIN>` benchmark where `<DOMAIN>` professionals work
   in simulated ... 'worlds' and design tasks that test AI agents." Flag it for the operator to
   eyeball (domain framing is inferred from the role title).
4. **Channel-mention repoint:** build an old→new map (Abacus channel ID → the vertical's channel
   ID from the search) and swap every mention. Write mentions as `![](#Cxxxx)`, NEVER `<#Cxxxx>`.
5. **SVA dashboard** → `https://sva-pi.vercel.app/campaigns/<campaign_id>/` (pass: sparta-va).
6. **Insightful timer** → `"Sparta - <V> - World"` for world work + `"Taskwriting"` for tasks.
   Flag: confirm the exact Insightful project name (this is the convention, not verified per-vertical).
7. **Onboarding, when there's no separate onboarding-support channel** (common — Cadre, Atria):
   put BOTH the onboarding-welcome and onboarding-support canvases in `#<v>-onboarding`, and reword
   the cross-refs — setup problems → "this channel / see the Onboarding Support canvas here",
   content/tasking → the pod channel.
8. **Maven** → the vertical's actual Maven channel (e.g. `#<v>-maven-support`), whatever it is named.
9. **General vs announcement:** if the vertical has no separate general channel, both the
   Announcements and Welcome canvases live in the announcement channel; note Welcome can move to a
   `#<v>-general` later.
10. **TBD everything vertical-specific with no value yet** — instructions doc, Drive folders, forms,
    calendars, office-hours TIMES, EPM training doc, automations sheet, expert tracker, org-chart
    image, reviewer guide, FA/GA quick guide, pod-lead + roster names. Use `(link TBD)` / `*link TBD*`.
    **Never invent a value.** Carry over ONLY genuinely Mercor-standard values (e.g. Claude Max
    $100/month reimbursement); comp amounts, quotas, and office-hours times are vertical-specific → TBD.
11. **Callout caveat:** on create, avoid a `#`/`##` heading INSIDE a `::: {.callout}` block (use
    bold text instead) — the create validator can reject in-callout headings.

## Constraint: standalone only

`slack_create_canvas` makes a STANDALONE canvas owned by the caller; the API cannot attach it as a
channel tab. After creating, give the operator every URL and remind them to share each into its
channel (share icon → channel). `in:#channel type:canvases` search only finds file-shared canvases,
so absence from search ≠ absence.

## After creating

- **Register** the new vertical's canvas ID table in
  [../editing-channel-canvases/reference/canvas-registry.md](../editing-channel-canvases/reference/canvas-registry.md)
  (new section, like the Abacus/Atria/Rampart/Cadre tables), plus the workspace name and the
  channel-set differences vs the standard.
- **Link backfill (later, once resources exist):** as `new-vertical-drive-folder` produces the Drive
  folder, Expert Facing folder, the two forms, the EPM Training doc, and the Automations sheet — and
  as the operator creates the two Google **Calendars** (Onboarding + Writer) and the SVA dashboard
  goes live — fill the matching `(link TBD)` slots. Read each affected canvas for its fresh
  `section_id_mapping` (the operator edits these by hand too, so never reuse cached ids), then
  `slack_update_canvas` with the `sections` array (edit_type `replace`, targeted `section_id`) —
  a full-body replace is REJECTED in vertical workspaces (`missing_required_field:section_id`), and
  the write-judge wants EVERY link in the replaced paragraph sourced in `evidence`, even unchanged
  ones. **COPY calendar URLs verbatim** from wherever the operator first pasted them (usually Key
  Links) — a retyped calendar `cid` is a silent dead link (bit Atria once). Which canvases carry
  which fillable links:
  - **Drive folder** → Key Links, EPM Start Here
  - **Expert Facing folder** → Key Links, EPM Start Here, Pod A Start Here
  - **Bonus + Reimbursement forms** — the link is the **responder** URL
    `https://docs.google.com/forms/d/e/<1FAIpQL…>/viewform`, read live from
    `forms.forms.get` → `responderUri` (mercor-mcp `google_workspace_drive_call`). NEVER the file-id
    shape `https://docs.google.com/forms/d/<fileId>/viewform`, which only reaches the form via a
    Google 301 and exposes the file id, and NEVER `/edit`, which opens the LIVE form's editor for
    anyone with edit access (every EPM has it, via `<vertical>-core-team`). Cadre shipped all 7 of
    its form links in the file-id shape and 2 of them as `/edit`; fixed 2026-08-01.
    → Key Links, Reimbursements & Bonus, Pod A, Announcements; reimbursement-only → Onboarding
    Welcome, Welcome to <V>
  - **EPM Training doc** → EPM Start Here · **Automations sheet** → Key Links
  - **SVA dashboard** (`https://sva-pi.vercel.app/campaigns/<camp>/`) → Key Links, EPM Start Here
  - **Onboarding + Writer calendars** → Onboarding Welcome, Onboarding Support, Welcome to <V> (both
    calendars); Pod A + Information Station (Writer calendar only)
- **Stays `(link TBD)` until the resource is actually built** (never invent one): the vertical
  **Instructions doc** (the biggest — Key Links, EPM Start Here, Onboarding Welcome, Announcements,
  Pod A, Information Station, Reviewers), **Expert Tracker** + **SSOT / Daily Syncs** (Key Links),
  **Reviewer Guide** (Reviewers), **FA/GA Quick Guide** + **Reviewer Feedback Form** + **org-chart
  image** (Information Station), **office-hours times**, and **pod-lead / roster names**. The
  Instructions doc unblocks the most slots — prioritize creating it.

## First real use

**Cadre (Human Resources)**, 2026-07-28 — 15 canvases in workspace `Hr - sparta vertical`; IDs +
channel-set differences recorded in the registry. Onboarding had no separate support channel (both
canvases in `#cadre-onboarding`); Maven channel = `#cadre-maven-support`; no `#cadre-general` (Welcome
went in `#cadre-announcement`).
