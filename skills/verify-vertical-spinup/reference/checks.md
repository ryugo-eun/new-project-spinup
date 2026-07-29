# Check specifications

One section per area. Each check: what to call, what PASS looks like, and what the
false-positive is (the way it can look done while being broken).

Company is always Sparta `company_AAABlLQjCsYYoXP4rsZKpY0y`.

---

## A. Teams project

| Check | Call | PASS | False positive |
|---|---|---|---|
| A1 project exists | `get_project(project_id)` | returns | |
| A2 roles defined | `get_project(id, include=['roles'])` | at least one writer role, and an EPM role | Rampart has only `Insurance Expert` and no EPM role, so its EPM automation matches nobody and is inert |
| A3 auto-provision email ON | `get_project` attributes / `set_project_autoprovision_email` read path | enabled | **Ships OFF.** Every live vertical needs it ON. Without it new members get no @mercor.expert address, and nothing else fails visibly |
| A4 owner + secondary owners | `list_project_secondary_owners(project_id)` | at least the vertical's EPM lead | |
| A5 **Studio campaign linked on the project** | by eye in the Teams UI | the project points at this vertical's `camp_...` | The last step of campaign setup and the most forgotten. Nothing in the clone does it and there is no `enable_project_integration` slug for Studio. `talent_success_get_project_annotation_platform` is **access-restricted** (`Access denied` for Ryu, confirmed 2026-07-29), so this cannot be confirmed through mercor-mcp. **Unverified is FAIL, not PASS** |

---

## B. Tags

Build the tag set from `list_project_audiences(project_id)` anchors, NOT from `list_tags`
(caps at 200 rows for Sparta, so new tags are invisible).

| Check | PASS | False positive |
|---|---|---|
| B1 nine role tags exist | Onboarding, Active Writer, Pod A, `<v>_completed_work_trial`, World Builder, Task Writer, Reviewer, EPM, Studio Admin | Rampart legitimately has 8, no Studio Admin tag |
| B2 vertical-prefixed | each name carries the vertical prefix | Abacus, Atria and Rampart have bare-named `Active Writer` / `Onboarding` / `Reviewer` that are genuinely their OWN distinct ids. A bare name is a smell, not a defect. **Judge by id** |
| B3 dedicated, not shared | no tag id anchors any other Sparta project's audiences | See the known-contaminated list below |

Known shared ids, flag on sight:

- `tags_AAABnYiHKEtdOhtigt1IUIft` Active Writer, granted by Panacea AND Rampart, both ACTIVE
- `tags_AAABnZflw34wRQLVfGVEa7yt` Onboarding, same pair
- `tags_AAABn05fDkO2qNlPVB5HDoFI` completed_work_trial, Abacus's own; Atria and Rampart were
  repointed off it 2026-07-28

To prove ownership: pull `list_project_audiences` for all six verticals and assert each id
appears as an anchor on exactly one project.

---

## C. Audiences

| Check | PASS | False positive |
|---|---|---|
| C1 canonical audience set present | one per role tag plus Everyone | |
| C2 **every audience has at least one target** | `targets` non-empty | **Atria's `Onboarding` audience has ZERO targets.** The audience exists, the tag grants, and the writer receives nothing. This is the single most checklist-invisible defect in the whole spinup |
| C3 Slack targets resolve | each Slack target's `externalId` matches a live channel id | **A channel rename leaves the target NAME stale while `externalId` stays correct.** Resolve by id. A name mismatch alone is cosmetic; an id mismatch is real |
| C4 Everyone provisioned into all-hands | announcements + maven-support targets present | |

---

## D. Slack channels

`slack_search_channels(workspace=<WORKSPACE NAME>, channel_types="public_channel,private_channel")`.

`workspace` takes the workspace NAME (e.g. `Hr - sparta vertical`), not the vertical name; a
bad value errors with the list of valid ones. mercor-mcp Slack is authed as Ayush Jain.

The canonical nine:

| Channel | Public? | Origin |
|---|---|---|
| `<v>-announcements` | public | renamed from `general`, PLURAL |
| `<v>-epms` | private | renamed from `random` |
| `<v>-technical-issues` | private | renamed from `help-desk` |
| `<v>-onboarding` | private | created |
| `<v>-pod-a` | private | created |
| `<v>-reviewers` | private | created |
| `<v>-maven-support` | public | created |
| `<v>-doctor-bot` | private | created |
| `<v>-world-file-upload-bot` | private | created |

| Check | PASS | False positive |
|---|---|---|
| D1 all nine present | 9 of 9 | **Without `channel_types` you get 2 of 9** and conclude nothing was built |
| D2 no leftover default topics | none of the 3 renamed channels still carries Slack's default topic | a renamed channel keeps its old topic, so it looks generic |
| D3 announcements is plural | `-announcements` | Cadre's live channel is still singular and needs renaming |

There is **no Slack channel-mutation API**: 0 of mercor-mcp's 35 Slack tools and none on the
claude.ai connector create, rename, archive or set-topic. Every fix here is manual in the UI.

---

## E. Canvases

Canonical set is the Abacus 13. The per-vertical canvas ID registry lives in the
`editing-channel-canvases` skill and is the only place it exists.

| Check | PASS | False positive |
|---|---|---|
| E1 13 canvases exist | count matches | canvases start **standalone** and must be shared into their channel; an unshared canvas exists but nobody sees it |
| E2 shared into channels | each canvas attached to its channel | |
| E3 TBD count | report the number of remaining explicit TBD links | TBDs are deliberate at creation time, so this is a progress metric, not a failure, until launch |
| E4 instructions link | points at THIS vertical's writer instructions doc | inherited links point at Panacea's or Vigil's |
| E5 Studio links | any Studio URL resolves to this vertical's campaign | inherited campaign ids in canvas links send writers to another vertical |

---

## F. Calendars

| Check | PASS | Known recurring defect |
|---|---|---|
| F1 both calendars exist | Onboarding + Writer | |
| F2 shared to tag-synced groups | access grants and revokes itself | |
| F3 onboarding calendar not world-readable | restricted | one of the three defects this rollout keeps producing |
| F4 owner is not a contractor alias | owned by a @mercor.com identity | second recurring defect |
| F5 calendar not empty | has events | third recurring defect |

---

## G. Studio worlds

Headers: `X-Company-Id: comp_2fa4115109d741cd94a3c409ed89e61f`,
`X-Account-Id: acct_be8f7fcc2c554b33baa5a0c9d05496e3`, plus `X-Campaign-Id`.

Per tasking world AND the Golden World Building world:

| Check | Call | PASS | False positive |
|---|---|---|---|
| G1 hooks present | `GET /hooks` for the world | non-zero, and the canonical chain length (21 or 22 Sparta-only) | **A clone carries statuses and remixes but NOT hooks.** Zero hooks means tasks strand at "Running ... AutoQC" and never reach the runner. The world looks fully configured |
| G2 world-level verifier | runner DB check, or the POST 201 from creation | exactly one | `GET /verifiers/world/{id}` and the Snowflake mirror **under-report**. Do not trust a zero from them alone |
| G3 default agent | `GET /worlds/{id}` `default_agent_ids` | contains `sparta_external_agent` | a clone can carry a `loop_agent`, giving runner error `no_sparta_external_agent` |
| G4 taiga env | `world_custom_fields.taiga_environment_id` | this campaign's env | clones leak the source's. Abacus once carried Vigil's. **Verify even when it looks right** |
| G5 file sync | `world_custom_fields.prometheus_gcs_path` | contains THIS world's id, with a fresh `prometheus_synced_at` | a clone inherits the SOURCE world's path, so the runner mounts an empty volume and trajectories error with `platform_has_environment=False` |
| G6 base_world_id | `sparta_create_tasking_world` remix | points at this campaign's own `[Live New Flow]` | |
| G7 instructions link | `world_settings.module_layout` and `module_layout_draft`, `instructions_card` modules | this vertical's doc | inherits the OLD Vigil doc `1nvj9D-IW7dBQyn-lOaXTINZoxVEJJ1R4GwzNgMOUi7U`. Direct API needs a browser User-Agent to dodge Cloudflare 1010 |

The runner preflights and rejects **one reason at a time**, in the observed order verifier,
then default agent, then file sync. So a green preflight after one fix proves nothing about the
next. Check all of G1 to G7 independently.

Also: guard `WORLDS.ARCHIVED_AT IS NULL` when counting worlds. Studio archives worlds without
stamping child tasks, producing ghost tasks.

---

## H. Automations

`list_automations(project_id, company_id)` for metadata, then `get_automation(id)` per
automation for `sql` and `body`, which `list_automations` does NOT return.

| Check | PASS | False positive |
|---|---|---|
| H1 canonical 7 present | see `provision-vertical-automations` | onboarding emails and the 48hr stalled-task reminder are **out of scope** (Ryu, 2026-07-29). Do not mark a vertical incomplete for lacking them, and do not count Atria's toward its total |
| H2 state | report `draft` vs `active` per automation, with a count | existence is not activation. Cadre, Abacus and Rampart each have 1 active of 7 |
| H3 no foreign ids | zero `proj_` / `camp_` / `world_` / `tags_` / `auto_` literal in `sql`, `body`, `trigger_config` that is not this vertical's | **include `auto_`.** Omitting it is why Cadre's bonus guard carries Abacus's id. Do NOT scan `notes` |
| H4 tag guard pairs | the id in `body.tagIds` equals the id in the SQL `NOT EXISTS` guard | a mismatch re-grants on every cron tick |
| H5 `contractorId` present | in every `tags` body | Abacus and Rampart omit it, so those automations fail `TagsBody` validation and could never run |
| H6 author attribution | `studio.task.status_change` bodies use `${createdByUserId}` | that event exposes no `${contractorId}`; using the transitioner tags the reviewer, not the writer |
| H7 bonus self-ID guard | guard 2's `par.AUTOMATIONID` equals this automation's own id | Cadre names Abacus's; Atria and Rampart never installed it |
| H8 no money live | no `bonus` or payout automation is `active` | true across all six verticals as of 2026-07-29. If that changes, it is deliberate or it is an incident |

---

## I. Bots

| Check | PASS | False positive |
|---|---|---|
| I1 Studio Doctor deployed | Vercel deployment healthy, `/doc` responds in `<v>-doctor-bot` | env set but not redeployed means the old env is still live. **Vercel env changes need a redeploy to take effect** |
| I2 Deployment Protection OFF | bot does not 401 | SSO wall on by default; the bot 401s silently |
| I3 cron switches | `/doc cron` list | **all crons are off by default** behind a Redis switch. Scheduled in `vercel.json` is not the same as enabled |
| I4 Upload bot deployed | GitHub Action green, write-scoped RLS key set | a read-only RLS key fails only at write time |

---

## J. Drive and docs

| Check | PASS | False positive |
|---|---|---|
| J1 folder tree | `<Domain> (Project <Vertical>)` exists under Sparta drive `1ZkXpFKOl4EbL7w06EMb64LHEnSF9p3PC` with the CLONEME subtree | |
| J2 tokens replaced | no `{{VERTICAL}}` or `{{DOMAIN}}` left in any title or body | |
| J3 both expert forms | LLM Usage Reimbursement + Bonus Compensation | **The Drive API cannot create form response destinations.** Linking Responses to Sheets is manual, so a form can exist with no response sheet |
| J4 response sheets relocated | into `Ops/Bonus and Reimbursements` | |
| J5 writer instructions doc | exists, is this vertical's, and matches the link in G7 and E4 | three places carry this link and they drift independently |

---

## Cross-check: the Essentials sheet

Read the vertical's `<Vertical> Startup Essentials` sheet and diff its `Done` column against
the verdicts above. Report every disagreement with its direction:

- **sheet says done, live says not**: launch risk, the vertical goes live missing the thing
- **sheet says not done, live says done**: wasted rebuild risk

Do not update the sheet. That is a write, and this skill does not write.
