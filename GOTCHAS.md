# Read this before you spin up a Sparta vertical

Every item below cost us real time on Abacus, Atria, Rampart or Cadre. None of them
are theoretical and none of them are in the Playbook, which tells you *what* to do,
not *what will go wrong*. Written 2026-07-28 from four spinups.

The single biggest lesson: **a clone looks finished and is not.** Studio clones,
Drive clones, automation clones and canvas clones all produce something that reads
correct and behaves wrong, usually by silently still pointing at the vertical you
cloned from.

---

## 1. Studio campaign and worlds

**A cloned world is not runnable.** The clone copies flow, statuses, remix configs,
eval configs and custom fields, and leaves out everything that makes the runner
accept the world. The Sparta runner preflights and rejects **one reason at a time**,
so if you fix them one by one you will burn an afternoon discovering the next one.
Fix all of these up front:

1. **Hooks do not clone.** They live in a separate `/hooks` router, not the world
   export bundle. Zero hooks means every task strands in "Running Task AutoQC"
   forever and never even reaches the runner. This is what happened to Abacus.
2. **The world-level Sparta verifier does not clone.** Missing gives
   `Found 0 world-level verifier(s)`. Create exactly one via `POST /verifiers/`.
3. **The default agent can be wrong.** A clone can carry a `loop_agent` instead of
   `sparta_external_agent`, giving `no_sparta_external_agent`.
4. **World files point at the source world.** `prometheus_gcs_path` is inherited
   stale, so the runner mounts an empty or wrong volume and the trajectory errors
   with `platform_has_environment=False`. Fire Sync to External Storage.
5. **The Taiga env leaks.** `taiga_environment_id` can still be the source
   campaign's. Abacus once carried Vigil's. Verify even when it looks right.

**`[CLONE ME]` itself is stale in four places, audited live 2026-07-29.** The mechanics are
current (all four worlds, 22 hooks on the tasking world dated 2026-07-22, SER Heal present,
`base_world_id` correct, no stale file pointer). The content is not: its Taiga env is
**Abacus's** `2a931db7-ee3f-42d4-8125-9ff4361ed755` on both worlds, the **old Vigil
instructions doc** is hard-coded 10x in the tasking world and 6x in the GWB, consensus points at
**Vigil's** world while its own consensus world sits unused, and the GWB links a doc titled
**`[Outdated] Onboarding Document`**. Adopt mode repairs the first three on the target, so a
spinup is safe, but every clone starts with them. Fixing them at the source is still owed.

**Campaign-level config does not clone at all.** Found on Cadre. The clone carries
world-level config, qc_specs and hooks, and drops `world_remix_configs` (including
the `prometheus_sync` file-to-Taiga-storage sync), `campaign_settings.pipeline_autoqc`,
`analytics_config`, `file_chat_enabled` and `qc_subrole_labels`. There is no create
API for these; the only self-serve path is `PATCH /campaigns/{id}`, which is a
partial merge.

**`pipeline_autoqc_configs.spec_world_id` must point at the vertical's own Golden
World Building world.** Atria was cloned from Abacus verbatim and initially still
pointed at Abacus's GWB; caught and repointed 2026-07-27. Verified correct live
2026-07-28: Abacus `world_044eeb97…`, Atria `world_a50c1c4b…`, each its own. The
`cprc_id` and `dimension_tags` beside it are shared-canonical and reused verbatim, so
`spec_world_id` is the one field in that block that is per-campaign and the one that
gets missed. Check it on every clone. Do not copy Rampart's block, its
pipeline_autoqc is off entirely.

**Do not wire Prometheus on a new vertical.** Chain B is the legacy backend; Vigil
cut over to the Sparta chain around 16-17 June 2026. Attaching the three Prometheus
remixes to Abacus made the agent double-run and made env-linters pull from a
different env, which engineers flagged. New campaigns are Sparta-chain only.

**An enabled hook is not a live chain.** Remix configs are world-scoped, not
campaign-wide, and a hook only resolves a remix that is attached to its own world's
`task_remix_configs`. Panacea and Vigil have Chain B hooks enabled but the remixes
unattached, so the chain is inert. Copying "enabled hooks" from them is not enough
signal.

**Every cloned world points writers at Vigil's instructions doc.** The Google Doc id
`1nvj9D-IW7dBQyn-lOaXTINZoxVEJJ1R4GwzNgMOUi7U` is hard-coded inside `instructions_card`
modules in both `module_layout` and `module_layout_draft`, typically 10 occurrences in
the tasking world and 6 in the GWB. Nothing warns you. Run
`replace-instructions-link` once the vertical has its own doc.

**A blank annotator view is a layout-page problem, not a flow problem.** Writers on
Abacus saw a completely empty view in the AutoQC-review statuses. `module_layout` was
byte-identical to Panacea's and Vigil's, which rendered fine, so the API cannot show
you the difference. The cause is the per-status task layout page in the Studio layout
editor. Check that first, not `flow_config`.

**API mechanics that will waste your time:**
- The Studio API sits behind Cloudflare and returns 403 error 1010 to
  `Python-urllib/*`. Send a browser `User-Agent`, or use `curl`.
- `PATCH /worlds/{id}` replaces the **entire** `world_settings` (~160KB), so you must
  GET, modify, and PATCH the whole object back. It is far too big to author inline
  through the mercor-mcp `studio()` tool; build and verify with a local script.
- `GET /worlds/?campaign_id=` returns `module_layout: null`. Fetch per world.
- `GET /verifiers/world/{id}` and the Snowflake VERIFIERS mirror both under-report
  and returned empty on a known-good world. Trust the `POST` 201.
- **`RLS_API_KEY` is campaign-scoped.** It 403s "not scoped" on every other campaign.
  Re-mint scoped to the new campaign before you start.
- The Sparta External Runner is **async on Modal**. It returns a job id, not a result.
  Poll `GET /task-remix/jobs/{job_trx_id}`; a Cadre smoke run took ~3.75 minutes.
- Uploading world files through the Studio UI double-nests them to
  `filesystem/filesystem/`. The world-upload bot's reRoot dedups. Use the bot.

## 2. Google Drive and forms

- **The Drive API cannot recursively copy a folder.** You have to recreate every
  folder and copy every file individually. That is why the clone skill exists.
- **The Forms API cannot create a response destination.** Linking a form to a sheet
  is manual in the UI (Responses, then Link to Sheets), and the "(File responses)"
  folder only appears after the first upload.
- **Order matters, or writers can see the responses.** Move the forms into
  `Ops/Bonus and Reimbursements` first, link each to a response sheet so the sheet is
  born there, then move only the forms back to `Expert Facing`. Response sheets should
  never touch the writer-readable folder.

## 3. Slack channels

- **There is no channel-mutation API. Anywhere.** Zero of mercor-mcp's 739 tools and
  none on the claude.ai connector create, rename, archive or set the topic of a
  channel. Only canvases, messages, search and read. Channel setup is manual in the
  UI for every vertical, permanently. Do not go looking for the tool; it does not exist.
- **`slack_search_channels` defaults to public-only.** Seven of the nine canonical
  channels are private, so it returns 2 of 9 and it looks like nothing was built.
  Always pass `channel_types="public_channel,private_channel"`.
- **A rename leaves the Teams audience target's NAME stale while its `externalId`
  stays correct.** Cadre's `Everyone` audience still has a target labelled
  `Cadre-help-desk` pointing at `#cadre-technical-issues`. The routing is right, only
  the label is wrong. Do not "fix" it as a misconfiguration. **Resolve audience
  targets by channel id, never by display name.**
- **Renamed channels keep their default topic and purpose.** `#cadre-epms` still says
  "Non-work banter / water cooler". Clear them by hand.
- The `workspace` parameter takes the workspace **name** (e.g. `Hr - sparta vertical`),
  not the vertical name. A wrong value errors with the list of valid ones.
- **mercor-mcp's Slack is authed as Ayush Jain, not you.** Unconfirmed whether that
  affects canvas authorship, but if you cannot see something you just created, check
  the connection's authed identity before assuming it failed.
- Each vertical has its own Slack workspace, so searching the `mercor` workspace will
  never find its channels. The Claude app also has to be approved per workspace:
  https://b617b7daea5adf5.slack.com/marketplace/A08SF47R6P4-claude

## 4. Canvases

- **The API cannot attach a canvas to a channel.** All 13 are created standalone and
  owned by whoever ran the skill; every one has to be shared into its channel by hand.
- If you do not have the channel ids yet, cross-channel references inside a canvas
  stay plain text. `list-channels` is blocked and search is membership-gated, so on
  Rampart only one channel id was ever known.
- **Comp figures and office-hours times carry over verbatim from the source vertical
  and are unconfirmed.** Abacus's $800 / 2h / 15h numbers propagated to Atria and
  Rampart untouched. Confirm before they reach a writer.

## 5. Calendars

- Calendars were **missing from the spinup package entirely** until 2026-07-28.
  Neither the Playbook nor the Essentials sheet had an item, so there was nothing to
  tick and three verticals shipped without anyone noticing.
- The audit of the other three found the same three defects each time: an onboarding
  calendar whose public rule was `reader`, making the whole event list world-readable
  (Abacus, fixed); **owner** granted to a contractor alias, meaning they can delete
  the calendar and rewrite its sharing (Rampart, still open); and calendars that exist
  but are completely empty, so the writer-facing link is hollow (Atria both, Rampart
  writer).

## 6. Tags, automations and the Teams project

- **Prefix every team tag with the vertical name.** Sparta tags are company-scoped and
  bare names like "Onboarding" and "Active Writer" already exist dozens of times over.
  An automation targeting a bare tag can grant on the wrong project's writers.
- **`create_tags` silently returns the existing shared tag** rather than creating a
  dedicated one. Rampart's automations are wired to company-wide tags because of this
  and nobody noticed at the time.
- **`list_tags` caps at 200 rows for Sparta**, so tags you just created sort past the
  cap and are invisible via the API. Verify in the Teams UI.
- **`auto_provision_email_enabled` ships OFF.** Every live vertical needs it ON or new
  members never get an @mercor.expert address. Cadre shipped with it off.
- Cloned automations are **drafts with unconfirmed money in them**. The $800 onboarding
  bonus also needs a self-ID dedup guard added before activation. Do not bulk-activate.
- The automation **write-review judge can deny** a clone (it denied Abacus's $300
  first-world bonus on Atria), and `update_automation`'s judge can get stuck reusing a
  previous rationale and block you. Recreate via `create_automation` when that happens.
- **There is no `enable_project_integration` slug for Studio.** The Studio-to-Teams
  project link is an undocumented manual step in Teams settings; the clone sets no
  project id.

## 7. Bots

- **The `/doc channel set` deadlock, ~30 minutes on Cadre.** `set` uses the channel you
  invoke it from, but Slack Grid's app-channel restriction blocks `/doc` inside
  `#<v>-doctor-bot` itself, so `set` can never run there. Escape hatch: the raw-id form
  from any channel where `/doc` works, `/doc channel C0BL652SQQK`, run from the
  vertical's own app. `/invite` does **not** fix it: Grid tracks bot membership and the
  channel app-allowlist separately.
- **Two red herrings.** `/doc list` appearing to work while `/doc channel` does not is
  not a permissions split; `list` is not a registered command, so it hits the
  unknown-command fallback which sits before `authorize`. And empty-message 200s in
  `vercel logs` are normal, not failures.
- Every bot reply is a **DM to the invoker**, never in-channel. Read the DM before
  diagnosing.
- Env set in Vercel does nothing until you **redeploy** to bake it in. Deployment
  Protection must be off or the bot 401s.
- Slack app and bot-user names must be **vertical-prefixed**:
  `<Vertical> World File Upload Bot`, and `Studio Doctor (<Vertical>)` with bot handle
  `<vertical>-doctor`. One Vercel deployment serves every vertical, so generic names
  make the apps indistinguishable and misattribute messages.

## 8. Docs, sheets and the checklists themselves

- **The Google Docs API cannot tick a checkbox.** Verified against the live v1
  discovery doc: `Bullet` exposes no checked-state property anywhere.
  `BULLET_CHECKBOX` is only a preset for *making* a checklist. Mark done items with
  strikethrough, or use the Essentials sheet's `Done` column. **Do not re-run
  `createParagraphBullets` over an existing checklist "to make it tickable"** — it
  already is, the API just cannot show you the state, and re-applying the preset can
  clear ticks you cannot see.
- **Do not trust the Essentials checklist.** Cadre's disagreed with live state on nine
  rows, in both directions: it claimed RL Studio, Insightful and four tag rows were not
  done when they were, and claimed pod auto-assignment and the welcome DM were done
  when the project had exactly one automation. Trust `list_project_audiences` and
  `list_automations`.
- The Panacea automations sheet has checkbox padding down to about row 1000, so
  `appendRow` drops rows below it. Find the real last row before writing.

## 9. Where the tooling lives

- **`~/.claude` is not a git repo.** Five spinup skills existed in exactly one place on
  one machine, including `editing-channel-canvases`, which carries the per-vertical
  canvas ID registry that is not reconstructible from anywhere else.
- **Stale duplicate skill copies on disk are actively wrong**, not merely old. The copy
  of `panacea-resync-taiga-outputs` under `vigil-workspace/skills/` labels Vigil's
  campaign id as Panacea's. The copy of `clone-sparta-campaign` under
  `sparta-professionals-clone/` is missing the entire campaign-level config block.
  Installed (`~/.claude/skills/`) is the source of truth; read nothing else.
- Note: `new-project-spinup/` was once described in `SKILLS.md` as reaching GitHub. It does
  not. As of 2026-07-29 it is still **not a git repository**, so the backup mirror is a second
  copy on the same disk and one disk loss takes all 18 spinup skills. `SKILLS.md` has been
  corrected.
- **"Installed wins" is a default, not a guarantee.** On 2026-07-29 the MIRROR held the newer
  `add-vertical-bots` (the three-sweep set) while installed still described the retired
  seven-sweep set including the two sweeps that looped. Diff both copies before trusting either.

---

## The durable fixes we still owe

- Get the Studio team to fold hooks, the verifier, the `sparta_external_agent` default,
  the env re-stamp and the file sync into the world clone itself.
- Fold campaign-level `world_remix_configs` and `pipeline_autoqc` (with `spec_world_id`
  pointed at the target's own GWB) into `clone-sparta-campaign`.
- ~~Build `verify-vertical-spinup`~~ **BUILT 2026-07-29**: one read-only sweep that audits a
  vertical against the whole playbook and reports what is genuinely done. It would have caught
  every Essentials-sheet error found on 2026-07-28. Never run end to end yet.
- Write the writer-instructions-doc skill. It is now the only spinup step with no skill, and it
  was Cadre's blocker.
