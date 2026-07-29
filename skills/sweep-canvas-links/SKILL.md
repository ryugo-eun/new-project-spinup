---
name: sweep-canvas-links
description: >
  Sweep every canvas in a Sparta vertical's Slack canvas set and fix its links in one pass:
  fill the "link TBD" slots from live sources, point every instructions link at that vertical's
  own Google Doc with the standard label, and add the Studio access block to the writer-facing
  canvases that are missing it. Builds a full link inventory first, never invents a URL, and
  re-reads every canvas afterwards. Use for "fix the links in the canvases", "fill the TBDs",
  "the instructions link is wrong in the canvases", "add the Studio link to the canvases",
  "sweep <vertical>'s canvas links". For creating a canvas set use `create-vertical-canvases`;
  for a single hand edit use `editing-channel-canvases`.
---

# Sweep Canvas Links

One pass over a vertical's whole canvas set that fixes links, instead of the one-canvas-at-a-time
hand editing in `editing-channel-canvases`. Canvas IDs come from that skill's
`reference/canvas-registry.md`, which is the only place the per-vertical registry exists.

Three fix classes, in this order:

1. **Fill TBDs.** Replace `link TBD` / `_link TBD_` slots with the real URL, but only where the
   asset actually exists.
2. **Instructions link.** Point at the vertical's own Google Doc, label `<Vertical> Instructions`.
3. **Studio access block.** Add it to the writer-facing canvases that lack it.

## Hard rule: never invent a link

If the asset does not exist, the TBD stays a TBD and goes in the report as unresolved. A
plausible-looking wrong URL is worse than a visible gap, because a TBD gets chased and a wrong
link gets clicked. This has already cost a real incident: the Atria onboarding calendar cid was
written with a one-character transcription typo (`...668821...` for `...668861...`) and shipped
a dead link into three canvases before anyone noticed.

Every URL written must be **verified against its live source in this session**, and calendar
cids must be base64-decoded and matched against the live calendar id before writing.

## Step 1: build the link inventory before changing anything

`slack_read_canvas(canvas_id, workspace)` for every canvas in the vertical's set. Produce one
table, and show it to the operator before any write:

```
| Canvas | Section id | Label | Current value | Class | Resolves to |
```

Class is one of: `TBD-resolvable`, `TBD-blocked` (asset does not exist), `WRONG-VERTICAL`
(carries another vertical's id), `STALE` (points at a retired asset), `OK`, `MISSING-STUDIO`.

The inventory is the deliverable even if the operator stops there. Do not batch reads and
writes together; a write based on a stale read overwrites someone else's edit.

## Step 2: resolve each link from its live source

| Link | Source of truth | Verify by |
|---|---|---|
| Instructions doc | the vertical's own Google Doc | open it, confirm it is this vertical's content, not Panacea's or Vigil's |
| Drive folders | `<Domain> (Project <Vertical>)` under Sparta drive `1ZkXpFKOl4EbL7w06EMb64LHEnSF9p3PC` | folder id resolves and the title carries no `{{VERTICAL}}` token |
| Expert forms | Bonus Compensation + LLM Usage Reimbursement in `Expert Facing` | form opens; a form can exist with no response sheet linked, which is a separate defect |
| Calendars | `list_calendars` | **base64-decode the cid and match it to the live calendar id** |
| SVA dashboard | `https://sva-pi.vercel.app/campaigns/<camp_id>/` | campaign id is this vertical's |
| Automations sheet | the vertical's Ops folder | |
| Org chart image | Slack file `F0BHESJ76C9`, hosted by a message in `#abacus-pod-a` | **do not delete that hosting message**, every vertical's Information Station embeds it |
| Studio | see Step 4 | |

## Step 3: the instructions link

**Source of truth is the vertical's own Google Doc, not the Instructions Hub** (confirmed
2026-07-29). The 2026-07-21 move to the Hub was reversed on 2026-07-23 across Abacus, Atria and
Rampart, and the reversal also de-hubbed the surrounding prose.

| Vertical | Doc id |
|---|---|
| Abacus | `1u-Go8CrHhzLwss4p1SqX9WiTNs3vJVmmG5bdKvBByws` |
| Atria | `1iyyef-zgJcIu0vnwjvk9qVFsPaMoanRGmIlJ5KFs-SU` |
| Rampart | `1WcKj4snqF4yHX1LdS1VWV6AOpsjGbseGUrBbRq_Mkcs` (URL uses `/mobilebasic`) |
| Cadre | **does not exist yet.** Leave TBD and report it as blocking |

Rules:

- Label is exactly `<Vertical> Instructions`. Not "Hub", not "Instructions Hub".
- Fix the surrounding prose too, or the link and the words disagree: step-1 headings become
  "Read the Instructions", "reading through the hub" becomes "the instructions", "the hub's FAQ"
  becomes "the instructions doc's FAQ".
- Do **not** relink generic prose mentions of "instructions doc" that were deliberately left as
  plain text (reviewers "How we work", Pod A "Project flow").
- The same link lives in three independent places that drift apart: the canvases, the Studio
  world layouts (`replace-instructions-link`), and the Drive folder. Fixing one does not
  fix the others. Report all three.

## Step 4: the Studio access block

Most vertical canvases carry **no Studio link at all**. Verified 2026-07-29 on Cadre: neither
Key Links nor Pod A Start Here contains a `studio.mercor.com` URL, and Studio appears only in
prose ("Studio or platform bugs").

The proven writer-facing form, taken from Panacea's live production canvas
`Active Experts, Read Me!` F0BAYNA2GJ3:

```
## Do Your Work in Studio

All builds and tasks happen in 👉 [Studio](https://studio.mercor.com)
(via [work.mercor.com](http://work.mercor.com) → Okta). Use Chrome, not Safari.
```

Three parts, all load-bearing: the bare root, the Okta route through `work.mercor.com`, and the
Chrome instruction. Writers who go straight to `studio.mercor.com` without the Okta route hit an
access wall, and Safari misrenders the annotator.

**Open question, do not resolve it by guessing.** Panacea uses the bare root, and no
campaign-scoped Studio landing URL has been verified to exist. The canonical campaign-scoped
form `https://studio.mercor.com/annotator/tasks/<task_id>/?campaignId=<camp_id>` is a **task**
deep link, correct for DMing someone a specific task, not for a canvas that has no task id. So:

- Writer-facing canvases get the bare-root block above.
- EPM canvases may additionally carry the vertical's campaign id as text, so an EPM can build a
  deep link.
- If someone confirms a campaign-scoped landing URL exists, prefer it and update this section.

Add to: onboarding welcome, Pod A Start Here, Information Station, and the Key Links canvas.
Do not add it to announcements or the bot channels.

## Step 5: write, one section at a time

Canvas write mechanics, all verified the hard way:

- **Full-canvas replace is rejected.** Legacy `action=replace` with no `section_id` fails
  `missing_required_field:section_id`. Replace a specific paragraph via the `sections` array.
- **`edit_type: append` also REQUIRES `section_id`**, even though appending to the end
  conceptually needs no target. Anchor to the LAST element's section_id; content lands after it.
- **The write-judge blocks thin evidence.** Source EVERY link and number in the paragraph you
  are writing, including the ones you did not change. Sourcing only your edit fails.
- **`slack_read_canvas` denormalizes live channel mentions `![](#C…)` back to `<#C…>` in its
  output.** That is a display artifact, NOT a broken mention. When you rewrite a block containing
  one, write it back as `![](#C…)` and it round-trips. Rewriting it as `<#C…>` breaks a working
  mention.
- Section ids are `temp:C:...` and are **read-specific**. Re-read immediately before writing;
  do not reuse ids from an earlier read in the same session.
- `slack_list-channels` returns `team_access_not_granted` on the project workspaces, and
  `slack_search_channels` only surfaces channels you are a member of. Channel ids come from the
  registry or the operator, not from enumeration.
- `workspace` takes the workspace NAME: `Abacus`, `Project atria`, `Insurance`,
  `Hr - sparta vertical`, `Consulting professional envs`, `Vigil`, `Sanctum`.

Write one section per call. On any failure, stop and report rather than retrying against a
different section.

## Step 6: verify and report

Re-read every canvas you wrote and assert:

1. No `link TBD` remains except the ones reported as blocked.
2. No other vertical's campaign, world, project, doc or folder id appears anywhere.
3. Every instructions link is this vertical's doc, labelled `<Vertical> Instructions`.
4. Every channel mention still renders as a mention, not plain text.
5. Every calendar cid base64-decodes to the live calendar id.

Report:

- Canvases changed, with what changed in each.
- **Unresolved TBDs**, each with the reason and who or what unblocks it.
- **Drift found elsewhere**: the Studio world layouts and the Drive copy of the instructions link.
- Anything that looked wrong and was deliberately left alone, with why.

Then update `editing-channel-canvases/reference/canvas-registry.md`. That registry is not
reconstructible from anywhere else, and a sweep that does not update it silently invalidates it.

## Known unresolved TBDs across the existing sets

Carry these forward rather than rediscovering them:

- Pod lead names (Start Here, Information Station).
- Recurring daily Google Meet links, still posted in-channel rather than on the canvases.
- Reviewer guide, interactive tutorial, recorded call (reviewers canvas).
- Reviewer sync cadence, link, incentives (reviewers canvas).
- Maven bot mention, pending the Maven deploy to each workspace.
- Help-request form and status tracker (technical-issues canvas).
- EPM training tracker.
- Cadre: instructions doc, SSOT / Daily Syncs, Expert Tracker. All blocked on assets that do
  not exist.
- Abacus, Atria and Rampart Key Links canvases have **no calendar rows**; only Cadre's does.
  Backfilling them is a candidate for this sweep.
