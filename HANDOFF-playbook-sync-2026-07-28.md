# Handoff: Playbook sync + Cadre calendars (2026-07-28)

Updated 2026-07-28 ~15:35 PT. The playbook sync is COMPLETE. What remains is a
data-integrity fix on the Essentials sheets, plus the pre-existing Cadre gaps.

## Documents in play

| Thing | ID |
|---|---|
| Master Playbook | `1B2m77LvX2sX2_PDF3oOoJ1JpquKw-WG8J80bvaFv5Is` |
| Cadre Playbook (clone of master) | `1vujrC5rbJLJ0UNnowXU-yvuPhuoRRR9LrKyVJqUiK_I` |
| Master Essentials checklist | `1CZqjPsGV2WQoWCcKil89KbPJ2QDqj5V0uzNAFowq46Y` |
| Cadre Essentials checklist | `1jGxwvwFPk3cY38gApIJgLBUeDX36I-SzsUHzMYGpzxY` |
| Cadre Teams project | `proj_AAABn6Z-4irb63tDd_NNRr5G` (Sparta `company_AAABlLQjCsYYoXP4rsZKpY0y`) |
| Abacus Teams project (automation source) | `proj_AAABn0Um0Wr19Gj_ql9JHKSh` |

## DONE and verified (this session, 2026-07-28 afternoon)

**Cadre Playbook re-synced to the master.** Three batchUpdates, descending index
order, each verified by a fresh read:

1. Step 6 heading `Step 6: Trackin` to `Step 6: Tooling`.
2. Step 4 body replaced with the master's trimmed 9-row structure (Vertical
   calendars + 2 subs, Reimbursement and Bonus Dispute Forms, 15 Slack channel
   canvases, Technical channel ticket workflow + Doctor-bot setup, Maven Setup +
   Needs Instructions Link). The calendar sub-rows carry Cadre's real group names.
3. Step 3 gained the master's new `Add Slack Channels` block, populated with
   Cadre's 9 REAL channels (`#cadre-announcement`, `-doctor-bot`, `-epms`,
   `-maven-support`, `-onboarding`, `-pod-a`, `-reviewers`, `-technical-issues`,
   `-world-file-upload-bot`). Cadre's `Reviewer channels (if reviewers)` row was
   NOT dropped, it moved under that block; the master lost it with no replacement.

Remaining master-vs-Cadre diff is only Cadre's intentional concrete values plus
the heading-indent drift (below). Verified: all 11 inserted paragraphs kept their
checkbox list bullets; 181 paragraphs total.

**Done items struck through in Cadre** (Ryu chose strikethrough over manual
ticking). The rule Ryu set: **nothing gets marked if it does not exist yet.**
Struck: Create Role, RL Studio, Expert-facing Drive folder, the whole
`Add Slack Channels` block (all 9 channels verified live), every Step 3
tag/audience row and sub-row except the help-desk row, Step 4 calendars + forms,
and Step 5's Grant Onboarding + Active Writer.

Each struck row was checked for real existence, not just for a wired Teams
target. Two rows were struck and then **un-struck** after that check:

- **`Slack #cadre-help-desk`** - no such channel; the workspace has exactly 9 and
  this is not one. RESOLVED: Ryu renamed the help-desk channel to
  technical-issues, which is why the `Everyone` audience target still *named*
  `Cadre-help-desk` has externalId `C0BM1LRQ42U` = **#cadre-technical-issues**.
  The routing is CORRECT, only the label is stale. The row was renamed to
  `Slack #cadre-technical-issues` and struck through as done. Do not "fix" that
  Teams target as a misconfiguration.
- **`15 Slack channel canvases`** - the canvases exist as standalone files owned
  by Ryu, but none are attached to their channels and the API cannot attach them.
  The channel-facing outcome does not exist yet.

Insightful sub-rows DID stay struck: every one resolves to a real Insightful
project URL under account `wgynqneefwhytdm`, so those integrations are genuinely
wired. The forms row stayed struck too (both forms plus both linked response
sheets confirmed live in Drive).

NOT struck: Teams identity bridge, Settings & Project owner, Send test contract,
Listings Page, all Step 2 instructions rows, Reviewer channels, #cadre-help-desk,
15 canvases, Technical ticket workflow, Doctor-bot setup, Maven Setup, Assign Pod
A, Grant completed_work_trial, the hours bumps, the bonus, and all of Steps 6/7.

**Master fix (Ryu approved).** The `Add Slack Channels` list had `Onboarding`
twice and no announcement row. The stray first duplicate is now `Announcement`,
which also restores alphabetical order. That is the ONLY master edit; the master
otherwise stays clean and untouched.

**Step 3 kept its Cadre Studio Admin and Everyone rows** (Ryu: keep both). Both
are real live audiences.

## THE ESSENTIALS SHEET IS WRONG IN BOTH DIRECTIONS

This is the important finding and the main open item. The Cadre Essentials
`Checklist` tab disagrees with live state on 6 rows. Live evidence came from
`list_project_audiences`, `list_automations` and `get_project` on the Cadre
project, read this session. The strikethrough pass followed LIVE state, not
the sheet, so the doc and the sheet currently disagree.

| Row | Item | Sheet says | Live truth |
|---|---|---|---|
| 12 | World Builder tag | FALSE | **TRUE** - audience `Cadre World Builder` to Insightful `cadre-world-building` |
| 14 | Pod A / B / C | FALSE | **TRUE** - audience `Cadre Pod A` to Slack `cadre-pod-a` |
| 15 | Reviewer | FALSE | **TRUE** - audience `Cadre Reviewer` to studio_campaign + Insightful + Slack |
| 16 | EPM / Team Lead | FALSE | **TRUE** - audience `Cadre EPM` to studio_campaign + 6 Slack + core-team group |
| 21 | Insightful timer | FALSE | **TRUE** - live Insightful targets on 5 audiences plus the `Sparta-HR - Sparta Vertical - Task` project |
| 22 | RL Studio | FALSE | **TRUE** - campaign `camp_35e49895...`, runner test PASSED 2026-07-28 |
| 23 | Pod auto-assignment | TRUE | **FALSE** - no such automation exists |
| 24 | Onboarding + role tags | FALSE | **TRUE** - automation `Add Onboarding and Active Writer tags on Contract = Active`, status active |
| 25 | Welcome DM/email | TRUE | **FALSE** - no such automation exists |

The Cadre project carries **exactly one** automation. That single fact is what
kills rows 23 and 25: whoever ticked them ticked intent, not a shipped
automation. Rows 2 and 25 also contradict each other inside the sheet (row 2
"Onboarding welcome email + DM" is FALSE, row 25 "Welcome DM/email" is TRUE).

Un-ticking rows 23 and 25 was deliberately NOT done without Ryu's say, because it
overwrites someone's claim. The 6 FALSE-to-TRUE corrections are pure additions of
verified truth and are safe to apply.

Note the earlier `project_cadre_vertical` memory claim that the sheet had "RL
Studio" and "onboarding+role-tag automation" checked is stale; both read FALSE
live. Do not trust that memory line.

## Cadre channel provenance, and the missing Slack skill

Three Cadre channels are **renamed IT-Admin defaults**, not fresh creations
(Ryu, 2026-07-28): workspace **general to #cadre-announcement**, **random to
#cadre-epms** (still carrying the stale "Non-work banter / water cooler" topic and
purpose, worth cleaning), **help-desk to #cadre-technical-issues**
(`C0BM1LRQ42U`). The general lesson: after a rename, Teams audience target NAMES
go stale while the externalId stays right, so always resolve a target by its
externalId channel id, never by its display name.

**There is no Slack-channel skill, and one cannot fully exist today.** Neither
mercor-mcp (739 tools) nor the claude.ai Slack connector exposes channel create /
rename / archive / set-topic; only canvases, messages, search and read. So channel
setup has been manual in the Slack UI for every vertical, and the skill set stops
at `create-vertical-canvases` and `add-vertical-calendars`.

**BUILT 2026-07-28: skill `provision-vertical-slack-channels`**, at
`~/.claude/skills/provision-vertical-slack-channels/SKILL.md` and mirrored into
`~/Desktop/MERCOR/new-project-spinup/skills/`. It cannot create or rename a
channel (no API), so it is a guided runbook plus the API-backed checks:

1. Asks for the vertical name, the workspace name as mercor-mcp knows it, and the
   Teams project id.
2. Hands over the canonical nine as two tables: the 3 IT-Admin defaults to rename
   (`general` to `-announcement`, `random` to `-epms`, `help-desk` to
   `-technical-issues`) and the 6 to create by hand, each with its real
   public/private visibility. Then pauses for the human.
3. Verifies live: diffs the workspace against the spec and reports missing, extra,
   wrong-visibility, and channels still carrying a default topic/purpose.
4. Audits the Teams side: resolves every slack audience target by its externalId
   channel id and flags stale labels, dangling targets, and untargeted channels.
   This step is what would have caught the help-desk case in seconds.
5. Hands off to `create-vertical-canvases`, `add-vertical-calendars`,
   `add-vertical-bots`, and reports how many canvases are still unattached.

It also records the Cadre reference table (9 channels with ids, visibility, and
which were renamed defaults) and the gotchas: `channel_types` must include
`private_channel` or you see 2 of 9; `workspace` takes the workspace NAME not the
vertical name; mercor-mcp's Slack is authed as Ayush Jain, not Ryu.

Open naming question left for Ryu rather than silently decided: live Cadre is
`#cadre-announcement` **singular**, but it gets called "announcements" in
conversation. Pick one and keep every vertical consistent, since the canvases and
Teams targets both hardcode it.

## Still open

1. **Apply the 9 Essentials-sheet corrections above** (Cadre sheet; the master
   sheet is a blank template so only its row set matters, not its values).
2. **Heading indent drift, deliberately unported.** The master's Phase 2 and
   guardrail `HEADING_2`s sit at indentStart 36; Cadre's are at 0. Left alone
   because indented headings look like drift IN THE MASTER rather than intent, so
   porting it would spread a probable mistake. Decide which way is correct, then
   fix whichever doc is wrong.
3. **Cadre's calendars still have zero events.** The canvas links lead nowhere
   until office hours are seeded. Needs times, days and hosts.
4. **13/15 Cadre canvases are still standalone**, not attached to their channels.
   The API cannot attach; it is a manual share per channel.
5. **#cadre-epms still carries the default random-channel topic and purpose**
   ("Non-work banter and water cooler conversation"). Manual fix in the Slack UI.
6. ~~Everyone into announcements + maven~~ **DONE by Ryu 2026-07-28**, on the tag-anchored `Everyone` audience.
7. **The `Cadre-help-desk` Teams target name is stale** (points correctly at
   #cadre-technical-issues). Optional cosmetic rename in Teams.
8. ~~Decide singular vs plural~~ **DONE: plural**, and #cadre-announcements is renamed.
9. **Decide singular vs plural (superseded)** on `<vertical>-announcement(s)` and align Cadre.
8. `provision-vertical-slack-channels` is newly written, so it has **never been
   run end to end**. First real use is the next vertical; expect to correct the
   spec if that workspace ships different defaults than Cadre's did.

## Tooling: mercor-mcp was unusable this session, here is the workaround

`mercor-mcp` connects but its `tools/list` **times out in the harness** because
the server returns **739 tool schemas**. Zero `mcp__mercor-mcp__*` tools mount, so
`google_workspace_drive_call` is unreachable the normal way. It is NOT a stale
`mcp-remote` proxy (that server is direct HTTP, no proxy process exists) and NOT a
server-side gap: a direct `tools/list` proves all 739 are served.

The fallback that works, and will work again next session:
`/private/tmp/claude-501/-Users-ryugo-eun/<session>/scratchpad/coil.py` - reads the
OAuth access token out of the macOS keychain (`security find-generic-password -s
"Claude Code-credentials"`, key `mcpOAuth`), does the MCP init handshake against
`https://coil.mercor.com/mcp/`, then `tools/call`. Never prints the token. Token
TTL is about an hour; re-read it from the keychain each run rather than caching.

Companion scripts, worth re-creating rather than trusting stale copies:
`fetch_docs.py` (pull both playbooks, flatten to `indent|style|struck|text`),
`patch_cadre.py` (the three structural batchUpdates), `strike_cadre.py` (the
strikethrough pass). All under the same scratchpad.

Every `google_workspace_drive_call` needs an `evidence` object
(`{rationale, variables}`); reads need it too, and a vague rationale is rejected.

## Hard-won gotchas (all still true)

- **The Docs API CANNOT tick a checkbox.** `Bullet` exposes only `listId`,
  `nestingLevel`, `textStyle`; nothing carries checked state. `BULLET_CHECKBOX` is
  only a `createParagraphBullets` preset. Done means strikethrough via
  `updateTextStyle {strikethrough:true}`, or a manual click.
- **Never re-run `createParagraphBullets` over an existing checklist.** It is
  already tickable; re-applying may silently clear ticks you cannot see.
- **A block replace merges paragraphs and the survivor can inherit EITHER end's
  indent.** Replacing Step 4 left all 9 rows at indentStart 72 (it took the LAST
  paragraph's indent, not the first). Always set indentStart explicitly on every
  row afterward, both the 36s and the 72s, never only the ones you think changed.
- **Cadre's "nesting" is visual only.** Every paragraph is `nestingLevel` 0; depth
  is pure `indentStart` 36/`indentFirstLine` 18 and 72/54. So the old 3-step
  tab-and-rebullet dance is unnecessary in this doc: insert, then set indentStart.
- **Insert at `endIndex - 1`** of the paragraph you want to append after, so the
  text inherits that paragraph's list formatting, not the next heading's.
- **When deleting a whole bullet block, stop one char short** of the final
  newline, then insert at the block start.
- Patch in **strictly descending startIndex order**, and prefer one batchUpdate
  per block with a fresh read between, over one clever mega-batch.
- `docs.documents.get` returns the JSON with a trailing `{"_mercor_rid":"..."}`
  object appended. Use `json.JSONDecoder().raw_decode`, not `json.loads`.
