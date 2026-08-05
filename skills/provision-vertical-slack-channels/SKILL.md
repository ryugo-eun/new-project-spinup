---
name: provision-vertical-slack-channels
description: Stand up a new Sparta vertical's Slack channel set: rename the three channels the workspace ships with (general, random, help-desk) and create the six that have to be made by hand, then verify the live workspace against the canonical nine and audit the vertical's Teams audience targets for names left stale by the renames. Use during a new-vertical spinup, or when someone says "set up the Slack channels for <vertical>", "create the channels for the new vertical", "rename the default Slack channels", "audit the vertical's Slack channels", "which channels does the new vertical need".
---

# Provision a new Sparta vertical's Slack channels

Every Sparta vertical runs on the same nine channels. Three of them already exist the moment IT creates the workspace and only need renaming; the other six you create. Distilled from the Cadre rollout (workspace `Hr - sparta vertical`, 2026-07-28), which is the clean live reference and the source of every name below.

## Read this first: there is no channel API

Slack channel mutation is **not available to you**. `mercor-mcp` exposes 35 Slack tools and **none** of them create, rename, archive, or set the topic of a channel; the claude.ai Slack connector is the same. You get canvases, messages, search and read. Verified 2026-07-28.

So do not promise to create or rename anything. The operator does that in the Slack UI. What this skill automates is the part that actually goes wrong:

1. the exact channel spec, so nobody improvises a name,
2. a live diff of the workspace against that spec,
3. an audit of the Teams audience targets, which silently go stale the moment a channel is renamed.

Step 3 is the reason this skill exists. See the trap below.

## Step 1: ask for the vertical

Ask the operator, in one message:

- **Vertical / project name** (e.g. `Cadre`). Everything else derives from it: the channel prefix is the lowercased name, so `Cadre` gives `cadre-*`.
- **Slack workspace name as mercor-mcp knows it.** This is NOT the vertical name. Cadre's workspace is `Hr - sparta vertical`. If they do not know it, call `slack_search_channels` with a junk `workspace` value; the error response enumerates every workspace you can reach. Do that rather than guessing.
- **Teams project id** (`proj_...`), needed for the step-4 audit. Optional if they only want the channel list.

Do not proceed on a guessed prefix or workspace.

## Step 2: hand over the channel spec

Emit both tables with `<v>` replaced by the real prefix. Keep the visibility column; it is not decoration, it is what Cadre actually has.

**Rename these three. They already exist, created by IT Admin at workspace creation.**

| Ships as | Rename to | Visibility | Note |
|---|---|---|---|
| `general` | `<v>-announcements` | public | The all-members channel. **Plural.** Its default topic and purpose are already correct, so keep them. |
| `random` | `<v>-epms` | private | **Replace the leftover topic and purpose** (see step 2b). They default to the water-cooler text and it is still on `#cadre-epms` today. |
| `help-desk` | `<v>-technical-issues` | private | |

**Create these six.**

| Channel | Visibility | Note |
|---|---|---|
| `<v>-onboarding` | private | Both onboarding canvases live here; Cadre deliberately has no separate `-onboarding-support`. |
| `<v>-pod-a` | private | One channel per pod. Add `-pod-b`, `-pod-c` as pods open. |
| `<v>-reviewers` | private | Only if the vertical has reviewers. |
| `<v>-maven-support` | public | Named `-maven-support`, not `-robot-advice`. |
| `<v>-doctor-bot` | private | Studio Doctor target; see `add-vertical-bots`. |
| `<v>-world-file-upload-bot` | private | Upload bot target; see `add-vertical-bots`. |

### Visibility: the default above holds, and Westwood is an exception

**Westwood (2026-08-05) runs every channel public, on Ryu's call, because the Teams integrations did
not provision reliably into its private channels.** That is a per-campaign decision, NOT a change to
this spec. Ask before applying it to another vertical, and do not read Westwood as the new pattern.

For any vertical, if provisioning into a private channel fails: `channel_not_found` on a private
channel means **the bot is not in it**, not that the id is wrong. Inviting the app is the normal fix.
Going all-public is the other option and costs privacy on `<v>-epms`, which is where offboarding, pay
and performance get discussed; each vertical has its own workspace, so the exposure is that vertical's
own experts, but it is real. If a vertical wants that conversation private while staying all-public,
use a separate private channel that no audience targets.

Then **pause and wait** for the operator to say they are done. Do not run step 3 optimistically.

**Naming: `announcements` is PLURAL.** Settled by Ryu 2026-07-28 and Cadre is renamed to match. Every vertical uses the plural, because the canvases and the Teams audience targets both hardcode it.

**Channels deliberately NOT in the set** (they exist on older verticals; do not recreate them unless asked): a separate `-general`, `-onboarding-support`, `-onboarding-announcements`, `-pod-leads`, `-help-desk`. The reviewer channel split (`-task-writing-reviewer`, `-world-builder-reviewer`, `-reviewer-announcements`, `-auditors`) is a Phase-1 item on the startup playbook that no vertical has actually built; leave it as a to-do rather than creating four empty channels.

## Step 2b: fix the inherited topics and purposes (manual, no API)

A renamed default channel keeps the topic and purpose it shipped with, and there
is **no tool that can change them** (confirmed across all 35 mercor-mcp Slack
tools; `update_maven_slack_channel` only repoints a Maven deployment, it does not
touch topics). So this is an explicit operator step, not something you can do.

Hand the operator this list:

| Channel | Inherited topic/purpose | Action |
|---|---|---|
| `<v>-epms` | "Non-work banter and water cooler conversation" / "A place for non-work-related flimflam, faffing, hodge-podge or jibber-jabber..." | **Replace.** It came from `random` and is actively misleading in the EPM channel. |
| `<v>-announcements` | "Company-wide announcements and work-based matters" / "This channel is for workspace-wide communication and announcements. All members are in this channel." | **Keep.** It came from `general` and is already correct. |
| `<v>-technical-issues` | none | nothing to do |
| everything created by hand | none | nothing to do |

Verify by reading the `Topic:` line back out of `slack_search_channels`; only the
two renamed defaults ever carry one. A water-cooler topic still sitting on
`<v>-epms` is the fingerprint of an unfinished rename.

## Step 3: verify against live

Read the workspace and diff it against the spec.

```
slack_search_channels(query="<v>", workspace="<workspace name>",
                      channel_types="public_channel,private_channel", limit=20)
```

**`channel_types` is mandatory.** It defaults to public only, and seven of Cadre's nine channels are private, so the default returns 2 of 9 and looks like nothing was built. This has already caused one wrong conclusion.

Report three lists, and do not soften them:

- **Missing**: in the spec, not in the workspace.
- **Extra**: in the workspace, not in the spec. Often a rename that was half-done, or a default nobody renamed.
- **Wrong visibility**: present but public where it should be private, or the reverse.

Also flag any channel still carrying an unwanted **default topic or purpose** (step 2b). Only the two renamed defaults ever have one.

## Step 4: audit the Teams audience targets (the trap)

**When a channel is renamed, its Teams audience target keeps the OLD name while its `externalId` still points at the right channel.** The routing stays correct and the label lies. On Cadre this produced a target named `Cadre-help-desk` whose `externalId` resolves to `C0BM1LRQ42U`, which is `#cadre-technical-issues`. Read by name it looks like a broken integration pointing at a channel that does not exist. It is not broken. Do not "fix" it.

The rule: **resolve every audience target by its `externalId` channel id, never by its target name.**

```
list_project_audiences(project_id="<proj_...>", company_id="company_AAABlLQjCsYYoXP4rsZKpY0y")
```

For each target where `targetType == "slack"`, pull the trailing channel id out of `externalId` (shape `https://app.slack.com/client/<team>/<CHANNEL_ID>`), look that id up in the step-3 result, and compare the live channel name to the target's `name`. Report:

- **Stale label**: id resolves fine, names differ. Cosmetic. Offer a Teams rename, and say plainly that routing is unaffected.
- **Dangling target**: id resolves to nothing live. Real breakage; escalate.
- **Untargeted channel**: a spec channel with no audience routing to it. Usually means an audience was never wired.

Do the same sweep over the vertical's playbook and canvases: a rename invalidates every hardcoded `#<v>-oldname`. Search the Cadre / vertical playbook doc and the canvas set for the old name before declaring the rename finished.

## Step 4b: Everyone must reach the all-hands channels

The Everyone audience needs a Slack target for `<v>-announcements`,
`<v>-maven-support` AND `<v>-technical-issues`. On Cadre it had only
technical-issues, so nobody was being added to announcements or Maven.

**That wiring lives in `provision-vertical-teams-integrations` step 3**, which also
covers the three-different-everyone-audiences trap and the
`update_project_audience` replace-semantics danger. Do not duplicate it here; run
that skill.

Audit rule for this skill: for each all-hands channel, confirm some
Everyone-anchored audience has a Slack target whose `externalId` ends in that
channel's id. Compare by channel id, never by target name.

## Step 5: hand off

Channels alone are an empty room. Next:

- `create-vertical-canvases` for the canvas set. **The API cannot attach a canvas to a channel**, so they are created standalone and the operator shares each one by hand. Report how many are still unattached rather than calling canvases done. Cadre has 15 created and 13 still standalone.
- `add-vertical-calendars` for the two calendars, whose links go into the canvases.
- `add-vertical-bots` for the two bot channels to point at something.
- `provision-vertical-teams-integrations` to wire the tags, audiences and every Slack/Google/Insightful/Studio target onto these channels.

## Cadre reference (live 2026-07-28)

Workspace `Hr - sparta vertical`, url `ff0e0e6a7578518.slack.com`, enterprise grid `E09EQ48AGDV`. Exactly nine channels, no `#cadre-help-desk`.

| Channel | Id | Visibility | Origin |
|---|---|---|---|
| `#cadre-announcements` | `C0BL42735QV` | public | renamed from `general`; keeps the default topic, which is correct |
| `#cadre-epms` | `C0BM1LER10Q` | private | renamed from `random`, default topic still present |
| `#cadre-technical-issues` | `C0BM1LRQ42U` | private | renamed from `help-desk` |
| `#cadre-onboarding` | `C0BLF04SU4R` | private | created by hand |
| `#cadre-pod-a` | `C0BL64S6ZAP` | private | created by hand |
| `#cadre-reviewers` | `C0BKX15BK55` | private | created by hand |
| `#cadre-maven-support` | `C0BLEA2TNCR` | public | created by hand |
| `#cadre-doctor-bot` | `C0BL652SQQK` | private | created by hand |
| `#cadre-world-file-upload-bot` | `C0BM6NB5L56` | private | created by hand |

The three renamed ones are stamped `IT Admin` / `2026-07-27`; the six hand-made ones are `Ryu Go-eun` / `2026-07-28`. That creator-and-date split is a fast way to tell, on any vertical, which channels were defaults and which were built.

## Gotchas

- **No channel create / rename / archive / set-topic tool exists.** Confirmed across all 35 mercor-mcp Slack tools and the claude.ai connector, 2026-07-28. Manual, every time.
- **`channel_types="public_channel,private_channel"` or you see a third of the set.**
- **`workspace` takes the workspace NAME, not the vertical name.** `workspace="cadre"` errors; `workspace="Hr - sparta vertical"` works. The error message lists valid values, so trigger it deliberately instead of guessing.
- **mercor-mcp's Slack connection is authed as Ayush Jain, not Ryu.** A vertical workspace missing from that error list means the connection is not in it, not that the workspace does not exist. The claude.ai Slack connector is authed as Ryu and may see different workspaces; cross-check both before concluding a channel is absent.
- **A renamed channel keeps its creator and creation timestamp**, so `Created by IT Admin` is evidence of a default, never of a fresh build.
- **Renames break hardcoded references silently** in the startup playbook doc, the channel canvases, and the Teams target names. Sweep all three.
