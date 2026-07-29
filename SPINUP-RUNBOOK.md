# New Vertical Spinup Runbook

Fifteen steps in order. For each: the skill that runs it, what it does, what to confirm, what to watch out for. Written 2026-07-29 from the Abacus, Atria, Rampart and Cadre spinups. Long-form reasons live in GOTCHAS.

## Before you start

- Company is always **Sparta** `company_AAABlLQjCsYYoXP4rsZKpY0y`. Never Mercor internal.
- Get an `RLS_API_KEY` **scoped to the new campaign**. It 403s on every other one.
- Get every number in writing: expert pay, EPM pay, bonuses, hours, headcount. **Nothing is inherited.**
- Skills live in `~/.claude/skills/`. Diff against `new-project-spinup/skills/` before trusting either.
- **Inventory before you create.** Almost nothing here is cleanly reversible.
- **A clone always looks finished and is not.** That is the pattern behind most of this doc.

## The fifteen steps

1. Teams project and roles. `create-vertical-teams-project`
2. The listing, one per expert role. `create-vertical-listing`
3. Slack workspace. **Manual**
4. Studio campaign. `clone-sparta-campaign`, after a human clones in the UI
5. Extra worlds or hook gaps, only if needed. `clone-studio-world`
6. The nine Slack channels. `provision-vertical-slack-channels`
7. Drive tree and the two forms. `new-vertical-drive-folder` (its own steps 1 to 7; its step 8 waits for step 9)
8. Tags, audiences, targets. `provision-vertical-teams-integrations`
9. Drive share and the two calendars. `new-vertical-drive-folder` step 8, then `add-vertical-calendars`
10. Automations. `provision-vertical-automations`
11. Doctor and upload bots. `add-vertical-bots`
12. Writer instructions doc. **Manual, by design**
13. Create the canvas set. `create-vertical-canvases`
14. Swap the inherited links, all six surfaces. `replace-instructions-link`
15. Audit. `verify-vertical-spinup`

Three rules set that order:

- **Step 2 interrupts step 1.** The platform chain is listing, then role, then milestone.
- **Channel ids must exist before** audiences, canvases and bots.
- **The core-team Google group only exists after step 8**, so step 9 cannot run earlier.

## Step 1: Teams project and roles

Skill: `create-vertical-teams-project`. Asks fourteen questions before it writes (row 9b, the EPM comp arrangement, is the one nobody asks and no field anywhere holds).

Does: creates the project as `humandata` on `rl_studio`, one Writer role per expert profile plus one EPM role, auto-provision email on, owners, milestone.

Watch out:

- **Roles come after the listing.** The skill pauses and sends you to step 2.
- **A second project splits the roster** and is not cleanly undoable. Inventory first.
- **Insightful must succeed or nothing is written.** A failure means not created, not half created.
- **Billable must exceed payable.** Atria's expert bills 50 and pays 85. Abacus's EPM bills 55 and pays 90.

Confirm:

- Every expert role **meant to be sourced** has a `listing_id`. A null is expected on the EPM role AND on any role filled by direct invite, so it is not automatically a defect: Abacus has two such roles, `EPM` and `External Expert Consultant`. Ask which roles are meant to be sourced, and flag a null only on those.
- `get_project_integrations` shows `auto_provision_email_enabled: true`. **`get_project` never shows it.**
- Record the project id's **last four characters**. They name every Google group later.

## Step 2: The listing, one per expert role

Skill: `create-vertical-listing`. Seventeen questions, and a source listing to copy is required.

Does: copies a live Sparta listing, diffs the description with you, validates it, creates it, hands the id back to step 1.

Watch out:

- **Creating a listing publishes it.** No draft exists. Archiving is the only way back.
- **`commitment` defaults to `full-time`.** Every live Sparta listing is hourly.
- **The band is what candidates read as their pay.** Reconcile it with the role's payable rate.
- **Never write one from scratch**, and never leave the source vertical's wording in it.
- Abacus runs nine listings, Cadre two. The EPM role gets none.
- **Check what a listing actually IS before copying it.** Some Abacus listings are `isPrivate` with `disableApplications`, and `General Accountant` points at a 30-minute intake survey, not a hiring funnel. `status: active` tells you nothing about whether anyone can apply.

Confirm:

- `get_listing` for band, commitment, eligibility, status.
- Steps show the default pair: resume, then work authorization.
- `list_project_roles` shows the role pointing at this listing.

## Step 3: Slack workspace

Manual. Request it.

Watch out:

- **Each vertical has its own workspace.** Searching `mercor` will never find its channels.
- The Claude app has to be **approved per workspace**.

## Step 4: Studio campaign

Manual: a human clones `[CLONE ME] Sparta Professionals Campaign` in the Studio UI.

Skill: `clone-sparta-campaign` in adopt mode then fixes what the clone leaves broken.

Does: renames the copied worlds and writes in the Taiga env, verifier, default agent, `base_world_id`, consensus target, hooks, qc_specs and campaign-level config.

Watch out:

- **A cloned world is not runnable**, and the runner rejects it one reason at a time. Fix all of it up front.
- **Hooks do not clone.** Zero hooks means tasks strand in "Running Task AutoQC" forever.
- **The world-level verifier does not clone.**
- The default agent can be a `loop_agent` instead of `sparta_external_agent`.
- **World files still point at the source world**, so the runner mounts the wrong volume.
- **The Taiga env leaks.** Every vertical needs its own env.
- **Campaign-level config does not clone at all.**
- `pipeline_autoqc_configs.spec_world_id` must be this vertical's **own** Golden World Building world. Atria pointed at Abacus's.
- **Do not wire Prometheus.** New campaigns are Sparta-chain only.

Confirm, per tasking world:

- Hooks present, and exactly one world-level verifier. Trust the **POST 201**, not `GET /verifiers/world/{id}`.
- Default agent is `sparta_external_agent`.
- `taiga_environment_id` is this campaign's.
- `prometheus_gcs_path` contains this world's own id, with a fresh sync timestamp.

## Step 5: Extra worlds or hook gaps

Skill: `clone-studio-world` (it absorbed `provision-autoqc-hooks` on 2026-07-29, so hooks are step 4 of the same skill).

Does: clones one more world correctly, or copies the canonical hook chain onto a world that has none.

Watch out:

- **Skip this if step 4 already wired qc_specs and the hooks.** Run it only for a world that is missing them.
- Source the hook chain from **this campaign's own** proven live world, never another vertical's.

Confirm:

- The new world passes the same four checks as step 4.

## Step 6: The nine Slack channels

Manual: creating and renaming every channel.

Skill: `provision-vertical-slack-channels` gives the spec, verifies live, audits the Teams targets.

Does: hands you the nine-channel spec, then checks the live workspace and flags target names left stale by renames.

The set is nine and **only six are created**. `general`, `random` and `help-desk` get renamed to `<v>-announcements` (plural), `<v>-epms`, `<v>-technical-issues`. Made by hand: `<v>-onboarding`, `<v>-pod-a`, `<v>-reviewers`, `<v>-maven-support`, `<v>-doctor-bot`, `<v>-world-file-upload-bot`.

Watch out:

- **There is no channel-mutation API anywhere.** Do not go looking for it.
- **`slack_search_channels` is public-only by default** and returns 2 of 9. Pass both channel types.
- **A rename leaves the target's name stale** while its id stays right. Resolve targets by id, never by name.
- **Renamed channels keep their default topic.** `#<v>-epms` will still say "water cooler".

Confirm:

- All nine present, announcements is plural, no default topics left.

## Step 7: Drive tree and the two forms

Skill: `new-vertical-drive-folder`. Run only its own steps 1 to 7 here; its step 8 is the sharing, which happens in step 9 of this runbook because it needs the groups.

Manual: linking each form to a response sheet.

Does: recreates the folder tree, copies all seven template files renamed to this vertical, and produces the two expert-facing forms.

Watch out:

- **The Drive API cannot recursively copy a folder.** Every file is copied one at a time.
- **The Forms API cannot create a response destination.** Linking is UI work.
- **Order matters for privacy.** Move both forms to `Ops/Bonus and Reimbursements`, link there, then move only the forms back.
- **Response sheets must never sit in `Expert Facing`**, which writers can read.
- The "(File responses)" folder is often born with a **stale vertical name**.

Confirm:

- Six folders, five docs and sheets, two forms, and no `{{` tokens left anywhere.
- `Bonus and Reimbursements` holds both response sheets. `Expert Facing` holds only the two forms.

## Step 8: Tags, audiences, targets

Skill: `provision-vertical-teams-integrations`. This is what turns a tag on a person into real access.

Does: creates the vertical-prefixed tags, builds the canonical audience set, attaches every Slack, Google, Insightful and Studio target, turns on auto-provisioned email.

Watch out:

- **Prefix every tag with the vertical name.** Bare names like "Onboarding" exist dozens of times over.
- **`create_tags` silently returns the existing shared tag.** Rampart's automations are wired to company-wide tags because of it.
- **`list_tags` caps at 200 rows** for Sparta, so a new tag can be invisible. Check the UI.
- Three "everyone" audiences exist. **Extend the tag-anchored one.**
- **The five stage Insightful projects must already exist** (onboarding, world-building, task-writing, reviewers, epms). An `insightful` target's `externalId` is a full URL carrying an **opaque project id**, so it cannot be authored from a convention, and there is no `insightful` slug on `enable_project_integration`. The `<workspace> - Task` project and the `insightful_account` `app_access` come free with the Teams project, on the two auto-created project-`everyone` audiences.
- **Google groups are the opposite: they provision from the naming convention.** A `google` target's `externalId` is just `<vertical>-<name>-<projSuffix>@mercor.expert`, so creating the audience is enough. Do NOT take group emails from `get_project_integrations`, which returns a different family (`<slugged workspace>-<suffix>.admins/.epms@`). The audience-synced groups appear ONLY as `google` targets in `list_project_audiences`.

Confirm:

- **Every audience has at least one target.** Zero targets means the tag grants nothing.
- Judge tag ownership **by id** against audience anchors, never by name.
- **Do not use `preview_audience_members`** for a population. It undercounted 12 against 13 on Abacus.

## Step 9: Drive share and the two calendars

Skills: `new-vertical-drive-folder` step 8, then `add-vertical-calendars`. Both need the groups from step 8.

Does: shares the top folder to the core-team group as writer and `Expert Facing` to the writer groups as reader, then creates both calendars and shares them to the tag-synced groups.

Watch out:

- **A Google group grants membership, not access.** Nothing is shared to it until someone shares it.
- **Read shares with `drive.permissions.list` and `supportsAllDrives`.** The plain tool hides group permissions and shows only you.
- The three recurring calendar defects: **world-readable** onboarding calendar, **owner given to a contractor alias**, and calendars that are **empty**.

Confirm:

- Top folder lists `<vertical>-core-team` as **writer**. All four live verticals were correct on 2026-07-29.
- `Expert Facing` is **reader** for the everyone and writer groups.

## Step 10: Automations

Skill: `provision-vertical-automations`, authored from templates. **Prefer it over cloning**, because clones leak source ids.

Manual: activating them.

Does: authors the canonical launch set from parameterized templates, including the self-ID dedup guard, and leaves them as drafts.

Watch out:

- **Clones are drafts with unconfirmed money in them.** Do not bulk-activate.
- **The bonus automation needs a self-ID dedup guard.** Cadre's named another vertical's automation, so it was inert.
- **A guard pointing at a different tag than the body grants** re-grants on every cron tick.
- The review judge can deny a clone, and `update_automation`'s judge can get stuck. Recreate via `create_automation`.

Confirm:

- **Read `state` on every one**, not existence. Cadre had one of ten active.
- Each guard tag id matches the tag the body grants.

## Step 11: Doctor and upload bots

Skill: `add-vertical-bots`. **One shared deploy serves every vertical**, so this is code plus a Slack app, never a new Vercel project.

Manual: creating the Slack apps, setting Vercel and GitHub secrets, redeploying.

Does: wires both repos, writes both Slack app manifests, pauses for secrets, then checks the deploys.

Watch out:

- **Env set in Vercel does nothing until you redeploy.** Deployment Protection must be off or the bot 401s.
- **`/doc channel set` cannot run inside `#<v>-doctor-bot`.** Use the raw-id form from a channel where `/doc` works.
- **Every bot reply is a DM to the invoker**, never in-channel.
- App and bot names must be **vertical-prefixed** or messages get misattributed.
- **Crons ship off** and are enabled by exact name, one per command.

Confirm:

- The bot answers, and each cron switch is in the state you intended.

## Step 12: Writer instructions doc

**Manual, and deliberately so.** There is no skill for this and there should not be: the work is deciding what an HR (or insurance, or accounting) data room and a realistic domain task actually look like. That is domain judgment, not find-and-replace. A skill was written for it on 2026-07-29 and deleted the same day, because once the link fan-out moved into step 14 the only thing left was the recast, and the recast is the human part.

How it is done: `drive.files.copy` a live vertical's instructions doc into this vertical's `Expert Facing` folder, then rewrite it for the domain. Abacus's `1x6WJoATGg0cfGLgHa9BiFk0IDKToyc-HZOtHDoXVxFI` is the best-maintained source, 26 tabs, recast from Panacea 2026-07-12 with sprint methodology added 7/13.

Watch out:

- **Deliberately late**, because the doc waits on the domain spec. Nothing in steps 1 to 11 needs it.
- **It does not permit writers starting work.** Until step 14 runs, every world still links the old Vigil doc.
- This plus step 14 are a **launch gate, not a setup gate**.
- **Inventory before you create.** Two instructions docs is worse than none: half the destinations end up pointing at each, and nothing surfaces the split.
- **Every number the source doc states is the source's number.** File count per world, golden-answer time, task-count guidance, scoring threshold, Claude plan cost, the weekly commitment, office-hours times. Ask for each; Abacus states its own weekly commitment three different ways across its own documents.
- **People names are Google smart chips**, which `replaceAllText` cannot touch. They need a delete-plus-insert by index.
- **The doc is too big for `docs.documents.get includeTabsContent`** (Abacus's is around 4.5M chars with styling; it blows the tool buffer). Export text via `google_workspace_export_to_upload`, then `upload_get_download_url`, then curl the single-quoted URL. For index-based edits, fetch with a `fields` mask.
- **Never name Taiga or the client.** Run and eval is "the client platform", QC is "the QC platform", the Studio control is "Agent Runner & QC".
- **Do not fabricate a worked example.** Keep the cloned one with a rebuild-pending banner until the team authors real golden tasks.
- **The Instructions Hub is NOT a destination.** As of 2026-07-29 `sparta-instructions-hub.vercel.app/atria/onboarding` still reads "You're a practicing accountant" on the **Atria** (Admin Healthcare) route: the channel names were swapped and the domain lexicon never was. Same class of defect as check K7. Never point writers at it as though it were live.

Confirm:

- Export the finished text and grep for the source vertical's name, `#<source>-`, the source domain's vocabulary, `Taiga`, and the client name. Any hit means the recast is incomplete. A doc that still says Abacus is not this vertical's doc no matter what the filename says.
- It sits in `Expert Facing`, not `[INT]`, or writers cannot read it.

## Step 13: Create the canvas set

Skill: `create-vertical-canvases`.

Manual: sharing each canvas into its channel.

Does: clones the canonical 13-canvas Abacus set and adapts each one, leaving every link this vertical does not have yet as an explicit TBD.

Watch out:

- **The API cannot attach a canvas to a channel.** All thirteen are standalone and owned by whoever ran the skill.
- **Comp figures and office-hours times carry over verbatim and unconfirmed.** Abacus's numbers reached Atria and Rampart untouched.
- **Copy calendar links whole.** A retyped `cid` is a silent dead link.
- Build the set as soon as channels exist. It does not wait on the instructions doc.
- **Do NOT run `sweep-canvas-links` here.** It is surface 4 of step 14, and running it now is wasted because the instructions doc landed at step 12 but the other link sources have not all been gathered.

Confirm:

- Thirteen canvases exist and are shared into their channels.
- Report the count of remaining TBDs. They are expected at this point; step 14 fills them.

## Step 14: Swap the inherited links, everywhere

Skill: `replace-instructions-link`. Six surfaces, not just Studio: the world layouts, the Teams onboarding doc, the Teams automations, the Slack canvases, this vertical's Drive tree, and the clone template. `replace-world-instructions-link` is retired into it.

**This is the last build step before the audit, and it moved from 13 to 14 on 2026-07-29.** Its canvas surface rewrites the canvases, so it has to run after they exist. In the old order it ran first and had nothing to rewrite.

Does: replaces the instructions doc and both calendar links across every surface that bakes them in, then reports a per-surface scorecard.

Watch out:

- The old Vigil doc id is hard-coded **roughly ten times in the tasking world and six in the GWB**.
- **Cloning is no longer Vigil-only.** Atria, Rampart and Cadre each inherited **Abacus's** doc id, so scanning for Vigil's id alone reports a false clean. Search all four known ids.
- **The automations surface is usually empty on a new vertical, so check rather than assume either way.** A set authored from the `provision-vertical-automations` templates carries no links (verified: Abacus has 8 automations, none of them messaging). It only carries links if the set was CLONED from a legacy vertical, and then it brings that vertical's instructions doc and onboarding calendar with it.
- **7 to 9 canvases** carry the instructions link and **6** carry the calendars. Fix the surrounding prose too, not just the URL.
- **Replace the doc-id substring, never the whole URL.** Abacus uses `/edit?tab=...#heading=...`, Rampart uses `/mobilebasic`.
- A retyped calendar `cid` is a **silent dead link**. Copy whole, then decode and match against the live calendar id.
- `PATCH /worlds/{id}` **replaces all ~160KB of `world_settings`**, so it is a get, modify, patch.
- The Studio API **403s error 1010 on a Python user agent**. Send a browser one.
- The `_CLONEME` EPM Training doc carries a **live vertical's** link, so every future spinup inherits it. Fixing it once fixes every future vertical.

Confirm:

- Scan the campaign for each old doc id and get **zero hits**.
- `get_project_onboarding_doc` and every messaging automation carry the new id, and each automation's `state` is unchanged.
- The scorecard has six rows, and any SKIPPED row has a written reason.

## Step 15: Audit before launch

Skill: `verify-vertical-spinup`. Eleven areas, 42 checks, live APIs, writes nothing.

Does: audits every area against live APIs and reports PASS, FAIL, BROKEN or SKIPPED per check.

Watch out:

- **BROKEN means present but non-functional.** That is the category checklists miss.
- **Do not trust the Essentials sheet.** Cadre's was wrong on nine rows, in both directions.

## What stays manual, permanently

- Creating, renaming and archiving **Slack channels**, and clearing their topics.
- **Attaching a canvas** to a channel.
- **Linking a form** to its response sheet.
- The **`[CLONE ME]` campaign clone** in the Studio UI.
- The **Studio-to-Teams project link**. No `enable_project_integration` slug exists for Studio.
- **Activating automations.**
- Creating **Slack apps**, setting Vercel and GitHub secrets, redeploying.
- **Ticking the Playbook checkboxes.** The Docs API cannot tick one. Use the Essentials sheet's Done column.
- **Making a listing private** or closing applications. Neither create nor edit exposes those fields.
- The **per-status task layout page** in Studio. A blank annotator view is a layout problem, not a flow problem.

## The failures that read as done

- **A world with zero hooks.** Tasks strand and never reach the runner.
- **An audience with zero targets.** The tag confers nothing.
- **An automation sitting in draft.** It exists, it never fires.
- **A Drive tree shared to nobody**, because the group and the share are different steps.
- **A calendar** that is world-readable, alias-owned, or empty.
- **A listing** that went live the moment it was created.
- **A role paying more than it bills.**
- **Worlds still linking another vertical's instructions doc.**
- **A checklist row that disagrees with live state**, in either direction.

## Final gate before writers start

- `verify-vertical-spinup` run, and every BROKEN item fixed or consciously accepted.
- The instructions doc exists and **step 13 has swapped it into every world**.
- **One real person on a contract** who can reach the work.
- **Every comp number confirmed by a human**, not inherited.
