# Which spinup skill creates a link, and which ones carry a stale copy

Audited across all 17 skills in this package, 2026-07-29. Read this before deciding a surface is
clean. "Creates" means that skill is the source of truth for the value. "Carries" means the skill
produces an artifact with the link baked in, so a clone of it inherits the source vertical's value.

| Skill | Creates | Carries a link that goes stale |
|---|---|---|
| `create-vertical-teams-project` | the Teams project, the Insightful project | the **onboarding doc** it sets, which holds the instructions link, the checklist app, and 2 Slack channel links |
| `create-vertical-listing` | the listing | nothing. Descriptions carry no instructions or calendar link, and offer copy is not writable. Out of scope |
| `clone-sparta-campaign` | the campaign's worlds | **instructions link, 10x in the tasking world and 6x in the Golden World Building world** |
| `clone-studio-world` | one extra world | same, per cloned world |
| `provision-vertical-slack-channels` | the nine channel ids | nothing itself, but every canvas and the onboarding doc reference these channels |
| `new-vertical-drive-folder` | the Drive tree, both Google Forms | the **EPM Training doc's instructions line**. The `_CLONEME` template's own copy carries Abacus's doc id, so every future vertical inherits it |
| `provision-vertical-teams-integrations` | tags, audiences, targets | ids, not links. Nothing to sweep |
| `add-vertical-calendars` | **both calendar links**, the source of truth | fills 6 canvases with them. Key Links rows exist for Cadre only; Abacus, Atria and Rampart still need backfilling |
| `provision-vertical-automations` | the canonical automation set from templates | templates carry no link, so an authored set is clean |
| `clone-vertical-automations` | a copied automation set | **instructions doc AND onboarding calendar**, in message bodies, plus stale doc ids cited in `notes` |
| `add-vertical-bots` | the two bots | deploy URLs only, not per-vertical doc links |
| runbook step 12, **manual, no skill** (`create-vertical-instructions-doc` deleted 2026-07-29) | **the instructions doc**, the source of truth | a human copies Abacus's doc `1x6WJoATGg0cfGLgHa9BiFk0IDKToyc-HZOtHDoXVxFI` and recasts it, so the copy carries Abacus's own links until recast. Grep the finished doc for the source vertical, source domain, `Taiga` and the client name |
| `create-vertical-canvases` | the 13-canvas set | **instructions link in 7 to 9 canvases**, both calendars in 6, the SVA dashboard link, Insightful timer names |
| `editing-channel-canvases` | single canvas edits | the registry is where every vertical's live link values are recorded |
| `sweep-canvas-links` | fills canvas TBDs | owns the canvas half of the sweep |
| `verify-vertical-spinup` | nothing, read-only | checks that the link landed |

## The canvases that carry the instructions link

Rampart's 2026-07-23 reversal touched **nine**: announcements, general, EPM Start Here, Key Links,
onboarding welcome, onboarding support, Pod A Start Here, Information Station, reviewers. Abacus was
7 and Atria 9, because the set grew. Treat "roughly 7" as a floor, and read the registry for the
vertical you are working on rather than assuming a count.

Six canvases take calendar links: onboarding welcome, onboarding support, the vertical welcome
canvas, Pod A Start Here and Information Station (writer calendar only in those two), plus Key Links.

## The instructions-link convention, and why it looks contradictory

- **2026-07-21:** every canvas instructions link was repointed to the Instructions Hub
  (`sparta-instructions-hub.vercel.app/<vertical>`).
- **2026-07-23:** reversed, at the operator's instruction, back to a **per-vertical Google Doc** for
  Abacus, Atria and Rampart. Label standardized to `<Vertical> Instructions`, with "Hub" dropped.

**Current convention is the per-vertical Google Doc.** The hub carries no per-vertical content, so do
not re-point at it. The 7/21 note in the registry is historical.

Two consequences for this skill:

1. **URL forms vary.** Abacus uses `/edit?tab=...`, Rampart uses `/mobilebasic`. This is the reason to
   replace the doc-id substring and never the whole URL.
2. **The prose has to move with the link.** The reversal also had to fix "Read the Instructions Hub"
   to "Read the Instructions", "reading through the hub" to "the instructions", and "the hub's FAQ" to
   "the instructions doc's FAQ". A canvas whose link is right and whose sentence still says "hub" is
   not done.

## Calendar links: the defect that keeps recurring

A retyped `cid` is a silent dead link. Atria's onboarding calendar was written into three canvases
with a one-character transcription error (`...668821...` instead of `...668861...`) and stayed dead
from 2026-07-21 to 2026-07-23.

**Rule: base64-decode every `cid` and match it against the live calendar id before it touches any
surface.** Copy links whole. Never retype one.

Also: a calendar with no events is a hollow link. `add-vertical-calendars` records that Atria's two
and Rampart's writer calendar were empty as of 2026-07-28.

## Canvas write mechanics that will cost you an hour

Carried from `add-vertical-calendars` and `editing-channel-canvases`, all verified:

- `edit_type: append` inside the `sections` array still requires a `section_id`. Anchor to the last
  element's id.
- Full-canvas `action=replace` is rejected in these workspaces. Use the `sections` array.
- `slack_read_canvas` prints live channel mentions `![](#C…)` back as `<#C…>`. That is a display
  artifact. Write them back as `![](#C…)` and they round-trip.
- The write-judge wants **every** link in a replaced paragraph sourced in `evidence`, including the
  ones you did not change. Cite those as carried verbatim from the read.
- Re-read every canvas after writing and diff against the pre-edit copy.
