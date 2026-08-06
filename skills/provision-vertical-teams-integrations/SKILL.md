---
name: provision-vertical-teams-integrations
description: Wire a new Sparta vertical's Teams-platform tags, audiences and integration targets, so that tagging an expert automatically grants them the right Studio role, Google group, Insightful project and Slack channels. Creates the vertical-prefixed team tags, builds the canonical audience set, attaches every target, turns on auto-provisioned @mercor.expert email, then verifies. Use during a new-vertical spinup, or when someone says "wire the integrations for <vertical>", "set up the tags and audiences", "provision everyone into the announcements channel", "the audiences are not granting access", "add the Slack targets to the Everyone audience".
---

# Provision a vertical's Teams tags, audiences and integration targets

This is the Teams "Integrations" tab: the layer that turns **a tag on a person** into
**actual access**. Tag someone `<Vertical> Reviewer` and the audience wiring gives
them the Studio reviewer subrole, the Insightful reviewer project and the reviewers
Slack channel. Get it wrong and the failure is silent: people are tagged, look
correct in Teams, and have no access.

Grounded in the Cadre rollout (`proj_AAABn6Z-4irb63tDd_NNRr5G`, 2026-07-28), whose
live shape is the reference matrix below.

Everything here is self-serve: `create_tags`, `list_tags`,
`create_project_audience`, `update_project_audience`, `delete_audience_target`,
`list_project_audiences`, `preview_audience_members`,
`get_project_audience_schema`, `get_project_integrations`,
`set_project_autoprovision_email`.

## Step 0: what you need first

Audiences point at things that must already exist. Confirm before starting, or you
will create audiences with dangling targets:

- **Slack channels** — run `provision-vertical-slack-channels` first. You need the
  channel **ids**, not names.
- **Google groups** — `<vertical>-onboarding-XXXX@mercor.expert`,
  `-completed-wt-`, `-core-team-`, `-everyone-`. The `XXXX` suffix is the project
  id's last 4 chars (Cadre `proj_AAABn6Z-4irb63tDd_NNRr5G` gives `Rr5G`).
- **Insightful projects** — one per working stage.
- **Studio campaign** — from `clone-sparta-campaign`.

Ask the operator for the vertical name and project id. Derive the prefix as the
lowercased vertical name for group/channel/Insightful names, and the Capitalized
name for tag names.

## Step 1: create the vertical-prefixed tags

**Prefix every tag with the vertical name.** Sparta team tags are company-scoped and
shared across all verticals; bare `Onboarding` and `Active Writer` already exist
dozens of times, so an automation or audience anchored to a bare tag can act on
another vertical's people.

```
create_tags(project_id=TARGET, company_id="company_AAABlLQjCsYYoXP4rsZKpY0y",
            names=["<V> Onboarding", "<V> World Builder", "<V> Task Writer",
                   "<v>_completed_work_trial", "<V> Active Writer", "<V> Pod A",
                   "<V> Reviewer", "<V> EPM", "<V> Studio Admin"])
```

**`create_tags` is idempotent on (company, name).** Pass a bare name and it hands
back the EXISTING shared company tag with `created:false`, which is exactly the
cross-vertical bug above. Prefixed names are what make it create fresh ones.

Note the casing split that Cadre actually uses: the work-trial tag is snake_case
and lowercase (`cadre_completed_work_trial`) while the rest are Title Case with a
capitalized vertical prefix. Match it; the automations reference these by id, but
humans read the names.

`list_tags` **caps at 200 rows for Sparta**, so new tags are often invisible to it.
Verify in the Teams UI, or read the ids back out of `list_project_audiences` anchors
once the audiences exist, which is more reliable.

## Step 2: build the audiences and their targets

`create_project_audience(project_id, anchors=[...], targets=[...])`.

- **anchor**: `{anchorType:"tag", anchorId:"<tag id>", displayName:"<tag name>"}`.
  `anchorType` is one of `tag`, `role`, `function`, `autogroup`, `project_owners`,
  `epms`, `pipeline_autogroup`, `everyone`.
- **target**: `{targetType, name, externalId, metadata}`. Live `targetType` values
  come from `get_project_audience_schema`: `slack`, `google`, `github`,
  `insightful`, `studio`, `studio_worlds`, `tags`, `github_user_repo`, `linear`,
  `claude`, `cursor`, `secure_browser`, `model_proxy`, `island_browser`,
  `workramp_group`, `workramp_folder`, `slack_mentionable_group`,
  `vercel_passport`. Cadre also has a live target of type **`insightful_account`**
  which is NOT in that list, so treat the schema list as incomplete rather than
  authoritative.

### The `slack` externalId you SEND is not the one you READ BACK

**Send the bare channel id. The API prefixes the workspace URL itself.** Verified on Westwood
2026-08-05: passing the full `https://app.slack.com/client/E09EQ48AGDV/C0BP60FLG8Y` stored
`https://app.slack.com/client/E09EQ48AGDV/https://app.slack.com/client/E09EQ48AGDV/C0BP60FLG8Y`,
a doubled value that resolves to nothing. It returns 200 and looks fine in the response until you
read the `externalId` carefully, so this is a silent breakage.

The table below is the **stored** shape, which is what every live vertical shows and what misled this
skill into documenting it as the input shape. `slack` input is `C0BP60FLG8Y`; `google`,
`insightful`, `studio` and `insightful_account` inputs are stored verbatim, so for those the two
shapes coincide.

`externalId` shapes, from Cadre's live targets:

| targetType | externalId (as STORED) |
|---|---|
| `slack` | `https://app.slack.com/client/<TEAM>/<CHANNEL_ID>` — **send only `<CHANNEL_ID>`** |
| `google` | `<vertical>-<name>-XXXX@mercor.expert` |
| `insightful` | `https://app.insightful.io/#/app/project/<account>/<project>` |
| `studio` | the **Teams project id** (`proj_...`), with `name:"studio_campaign"` |
| `insightful_account` | the literal `app_access` |

### The canonical matrix (Cadre live, 2026-07-28)

| Audience anchor | Targets |
|---|---|
| `<V> Onboarding` | google `<v>-onboarding`, insightful `<v>-onboarding`, slack `#<v>-onboarding` |
| `<V> World Builder` | insightful `<v>-world-building` |
| `<V> Task Writer` | insightful `<v>-task-writing` |
| `<v>_completed_work_trial` | google `<v>-completed-wt` |
| `<V> Active Writer` | studio `studio_campaign` (grants campaign_annotator, writer subrole) |
| `<V> Pod A` | slack `#<v>-pod-a` (one audience per pod) |
| `<V> Reviewer` | studio `studio_campaign` (reviewer subrole), insightful `<v>-reviewers`, slack `#<v>-reviewers` |
| `<V> EPM` | studio `studio_campaign` (campaign_admin), google `<v>-core-team`, insightful `<v>-epms`, slack `#<v>-epms`, `#<v>-onboarding`, `#<v>-pod-a`, `#<v>-doctor-bot`, `#<v>-world-file-upload-bot` |
| `<V> Studio Admin` | studio `studio_campaign` (campaign_admin) |
| project `everyone` | insightful `<vertical> Task` project + `insightful_account` `app_access` |
| tag `Everyone` | google `<v>-everyone` **+ slack `#<v>-announcements` + slack `#<v>-maven-support`** (see step 3) |

## Step 3: provision Everyone into the all-hands channels

Every project member must land in the channels that are for everyone. **On Cadre
this was wrong**: the Everyone audience routed to only `#cadre-technical-issues`, so
nobody was being added to announcements or Maven support.

Required Slack targets on Everyone:

| Channel | Why |
|---|---|
| `<v>-announcements` | The all-hands channel. Everyone, no exceptions. |
| `<v>-maven-support` | Public support channel; every expert must be able to ask. |
| `<v>-technical-issues` | Where experts raise issues. |

**Put the Slack targets on the tag-anchored `Everyone` audience**, alongside the
Google group. That is what Cadre does and it works. Cadre's three everyone-anchored
audiences, live:

| Audience id | Anchor | Carries |
|---|---|---|
| `ac003a8b-de70-4119-996e-4400f7cd5d83` | **tag `Everyone`** | google `cadre-everyone` + slack `#cadre-announcements` + slack `#cadre-maven-support` |
| `aud_AAABn6aCsiLh0uNkv_xLLYLp` | project `everyone` | insightful project + `insightful_account` `app_access` |
| `aud_AAABn6aCsZ63ILKwodRNoJyL` | project `everyone` | slack `Cadre-help-desk` (resolves to `#cadre-technical-issues`) |

The tag `Everyone` audience is the one you extend. The two project-`everyone` ones
are auto-created at project setup and already hold the Insightful access and the
tech channel. **Audiences are not segregated by target type** — a single audience
happily carries google and slack targets together, so do not go looking for "the
Slack one".

Cadre's team is `E09EQ48AGDV`; `#cadre-announcements` is `C0BL42735QV` and
`#cadre-maven-support` is `C0BLEA2TNCR`. **Cadre's Everyone provisioning is DONE**
as of 2026-07-28.

### `update_project_audience` APPENDS targets. Verified 2026-08-05.

**Its own tool description says "optionally replace targets". It does not replace, it appends.**
Confirmed twice on Westwood: passing the full intended list to repair one bad target produced
duplicates of every target in that list, including a Google group added twice.

So the old advice to "pass the full intended list, correct under either semantics" is **wrong and
actively harmful**. Do this instead:

1. **To ADD a target: pass ONLY the new target(s).** Existing ones survive untouched.
2. **To FIX or REMOVE a target: `delete_audience_target(audience_id, target_id)`**, then add the
   replacement. There is no in-place edit.
3. **Re-read afterwards and count.** A repair attempt that appends leaves the broken target live
   alongside the good one, which reads as working while half the rows are junk.

`anchors` is required on every update, so pass the audience's existing anchors verbatim or you will
change who the audience catches while trying to edit a target.

## Step 4: turn on auto-provisioned email

A fresh Teams project ships with this **OFF**, and without it a new member gets no
`@mercor.expert` address. Since all the Drive, calendar and group sharing is granted
to `<vertical>-*@mercor.expert` groups, an expert without one has access to nothing.

```
set_project_autoprovision_email(project_id=TARGET, enabled=true)
```

**Only `get_project_integrations` reports this flag.** `get_project` does not return
it at all, which is why it gets missed. Verify by re-reading. Reversible with
`enabled=false`. Cadre shipped `false` and was fixed 2026-07-28.

## Step 5: verify

1. `list_project_audiences(project_id, company_id)` and diff against the matrix.
   Report any audience with **zero** targets; that is a tag that grants nothing.
2. **Resolve every slack target by its `externalId` channel id, never by its `name`.**
   A renamed channel leaves the target's name stale while the id stays correct. Cadre
   has a target still named `Cadre-help-desk` whose id resolves to
   `#cadre-technical-issues`. Routing is fine; the label lies. Do not "fix" it.
3. For each all-hands channel, confirm some Everyone-anchored audience has a Slack
   target ending in that channel's id.
4. Confirm every Insightful target resolves to a real project URL rather than a bare
   name.
5. `get_project_integrations` shows `auto_provision_email_enabled: true`.
6. `preview_audience_members(audience_id)` to sanity-check who an audience actually
   catches before anyone relies on it.

Report what is missing plainly. A tagged expert with no access looks identical in the
Teams UI to a correctly provisioned one, so silence here is not evidence of success.

## Step 6: the groups you just made still own nothing

Creating a Google group as an audience target grants membership, not access. Nothing is
shared TO the group until someone shares it. The one that gets forgotten:

- **The vertical's main Drive folder must be shared to the `<v>-core-team` group as
  `writer`**, e.g. `rampart-core-team-zZi7@mercor.expert` on `Insurance (Project Rampart)`.
  Share the TOP folder so the whole tree inherits. Procedure and the `Expert Facing`
  reader shares: `new-vertical-drive-folder` step 8.
- The two calendars are shared to the onboarding and completed-work-trial groups:
  `add-vertical-calendars`.

Verify the folder share with `drive.permissions.list` + `supportsAllDrives: true`; the plain
`get_file_permissions` hides group permissions and shows only the owner. All four new
verticals were confirmed shared 2026-07-29 (PT).

## Hand off

- `provision-vertical-slack-channels` if the channels are not built yet (do it first).
- `clone-vertical-automations` for the launch automations, which reference these tag
  ids. **Feed it the prefixed tag ids from step 1**; its own instructions tell it to
  call `create_tags` with bare names, which returns the shared company tags.
- `add-vertical-calendars`, whose sharing targets the Google groups above.

## Gotchas

- **Bare tag names return shared company-wide tags.** Always prefix.
- **Never reuse another vertical's `completed_work_trial` tag.** Each vertical gets
  its own `<v>_completed_work_trial`. Sharing it merges the two verticals' rosters.
- **`list_tags` caps at 200 rows for Sparta**; read tag ids from
  `list_project_audiences` anchors instead.
- **`update_project_audience`'s merge-vs-replace behaviour is UNVERIFIED.** Always pass the full intended target list and re-read. See step 3.
- **Three everyone audiences.** Extend the **tag-anchored** one; the two project-`everyone` ones are setup defaults. Audiences are NOT segregated by target type, one can hold google and slack together.
- **`get_project` does not expose `auto_provision_email_enabled`**; only
  `get_project_integrations` does.
- **The `studio` target's `externalId` is the Teams project id**, not a Studio
  campaign id. Counterintuitive but correct.
- **`get_project_audience_schema`'s targetTypes list is incomplete** — Cadre has a
  live `insightful_account` target that the list omits.
