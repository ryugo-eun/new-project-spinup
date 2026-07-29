# HANDOFF: vertical copy + numbers, and what shipped 2026-07-29

Session of 2026-07-29 (PT). Read this plus `SKILLS.md` and `GOTCHAS.md` and you can resume cold.
Everything below was verified against live APIs on the day unless labelled otherwise.

---

## 0. Read this first, two hard constraints

1. **The runbook Google Doc is hand-edited by Ryu. Never regenerate it.**
   https://docs.google.com/document/d/1RKyWoKfweCVQLZEzZONMhZQGAzrow0bOUc911uu92o0/edit
   Ryu edited it at 13:42 PT and told the agent not to overwrite. `drive.files.get` confirms
   `lastModifyingUser` is Ryu, version 41. The local `SPINUP-RUNBOOK.md` is therefore **behind**
   the Doc. Do NOT re-run the markdown upload plus `drive.files.copy` conversion against it, which
   replaces the entire body. To change it: read the live Doc, make a targeted `batchUpdate`, and
   ask first. Memory: `feedback_dont_overwrite_doc_edits`.
2. **`new-project-spinup/` is not a git repo and neither is any parent.** The mirror is a second
   copy on the same disk, not a backup. It now also holds the only copies of the hook scripts. A
   `git init` plus a remote is the single highest-value chore outstanding.

---

## 1. State of the skills

**16 spinup skills**, installed at `~/.claude/skills/<name>/SKILL.md`, mirrored to
`new-project-spinup/skills/`. Verified byte-identical at end of session.

**Built today (never run end to end):**

- `create-vertical-teams-project` — step 0. Interviews 13 inputs, creates the project as
  `humandata` on `rl_studio`, one Writer role per expert profile plus one EPM role, auto-provision
  email on, owners, milestone, test contract. Carries the 6 canonical `function_id`s. Hard-blocks
  a role whose payable exceeds its billable.
- `create-vertical-listing` — step 0a, **runs before `create_role`**. Interviews 14 inputs, and a
  **source listing to copy is required**; it never authors from scratch. Leads with the trap that
  `create_listing` publishes instantly with no draft state.

**Collapsed today:** `insert-autoqc-hooks` was merged into `provision-autoqc-hooks` and deleted;
then hook attachment was folded again into **`clone-studio-world`**, which is now the single skill
that makes a cloned world runnable. `provision-autoqc-hooks` no longer exists. All four scripts
(`provision_hooks.py`, `insert_hooks.py`, `fix_claim_gating.py`,
`references/canonical_hooks.json`) live in `clone-studio-world/` and are mirrored. Two stray
copies of the old skill on the Desktop were deleted; a third set still sits in
`vigil-workspace/skills/provision-autoqc-hooks/` and is stale, do not read from it.

**Canonical hook implementation is `port_hooks()` in
`clone-sparta-campaign/clone_sparta_campaign.py`.** It is the only one proven end to end on live
campaigns: idempotent by hook name, remaps qc_spec ids in the payload AND the predicate, drops
Prometheus, checks target remixes first. The two standalone scripts are for gap-filling one world.
**If they ever disagree, `port_hooks()` wins.**

**HARD RULE recorded in both skills: never attach the 3 Prometheus hooks.** The tasking set is
**22**. Merging the two hook skills is what exposed this: the script-driven one attached the trio,
which is what made Abacus double-run. `canonical_hooks.json` still contains them, so the data file
invites the mistake.

---

## 2. Live defects found today, none fixed

Nothing in this section was touched. Each is a real state change on a running vertical, so each
needs a human decision.

### 2a. `[CLONE ME]` template, five defects every clone inherits

Full audit is in `clone-sparta-campaign/SKILL.md` under "Audit of `[CLONE ME]` itself". Template
is `camp_4040aadecd0544a6ab7f9a97780b809f`. It is **current on mechanics** (four canonical worlds,
22 hooks dated 2026-07-22, SER Heal, correct `base_world_id`, no stale file pointer) and **stale
on content**:

| # | Defect |
|---|---|
| 1 | Taiga env is **Abacus's** `2a931db7-ee3f-42d4-8125-9ff4361ed755`, on both the tasking world and the GWB. Highest risk: a clone whose operator skips the env question runs in Abacus's environment |
| 2 | Old **Vigil instructions doc** `1nvj9D-…` hard-coded **10x in the tasking world, 6x in the GWB** |
| 3 | **Consensus points at Vigil's** world while the template's own consensus world sits unused |
| 4 | The GWB links a doc titled **`[Outdated] Onboarding Document`** (`1PLYPvK3R5jwQHVE1cyLZLXi_UwId5fuD2lg-6mBk94o`, erickchen@, modified 2026-06-05) |
| 5 | **`campaign_settings` is `{}`** — no `pipeline_autoqc`, no `world_remix_configs` |

Plus a risk, not a defect: the GWB links `world_spec_writer_template.docx`
(`10GQbLMWxpfnVw429uPluLL6eRiJ9ctxf`) **owned by a contractor alias**
`marigold.terebellum.buna@mercor.expert`, who can delete or rewrite it.

Adopt mode repairs 1, 2, 3 and 5 on the target, so a spinup is safe. **Fixing them in the template
retires that repair forever**, and 2 and 4 are one-line link swaps. Ryu has not authorised editing
the template.

### 2b. Auto-provision email is OFF on three verticals

`auto_provision_email_enabled: false` on **Abacus** (`proj_AAABn0Um0Wr19Gj_ql9JHKSh`), **Atria**
(`proj_AAABn3FoIuB1-06gfllLl4Nq`) and **Rampart** (`proj_AAABn4DXkl4vJRwM1aBAzZi7`). Only Cadre is
on. Every Drive share, calendar grant and Google group is addressed to `@mercor.expert` aliases, so
a new member on those three may get no alias and therefore no access. One call each:
`set_project_autoprovision_email(project_id, enabled=true)`. **Ryu was asked and has not answered.**
Unverified: whether existing members already hold aliases, which decides if this is an active
outage or only a risk for new joiners.

### 2c. Two roles are recorded at a loss

- Atria **Healthcare Admin Expert** `8d98f3fc-3a26-415d-8221-ba621510e352`: billable 50, payable 85.
- Abacus **EPM** `87b72b0e-fdb8-4ccc-8cdf-dc4f358d8ef1`: billable 55, payable 90.

Cadre's EPM (1/1) and Atria's EPM (2/1) are placeholders, not real rates.

### 2d. Onboarding docs

- **Cadre's is the platform placeholder**: "Your project onboarding document is currently being
  prepared and will be shared with you shortly." Created 2026-07-28, never replaced. Every Cadre
  expert who signed a contract received that.
- Rampart's is a real welcome letter from Carlota but still carries `[kickoff date TBD]` and
  `[due date TBD]` nine days on.

Read with `get_project_onboarding_doc`, write with `set_project_onboarding_doc`. **No skill
references either tool.**

---

## 3. Facts established today (use these, do not re-derive)

- **Google group suffix = the project id's last 4 characters.** Verified on six projects: Abacus
  `…JHKSh` → `abacus-core-team-HKSh`, Atria `…Ll4Nq` → `l4Nq`, Rampart `…AzZi7` → `zZi7`, Cadre
  `…NRr5G` → `Rr5G`, Panacea `…tL_r3W` → `consulting-epms-_r3W`, Vigil `…Ex4nT` → `vigil-epms-x4nT`.
  Case preserved, including the leading underscore. On Cadre **all four** google groups carry it.
- **The group name PREFIX is arbitrary.** Four different schemes live: Cadre
  `hr.-.sparta.vertical-Rr5G.admins` (slugified Slack workspace name), Rampart `insurance-zZi7`
  (domain), Abacus `abacus-HKSh` (codename), Atria `project.atria-l4Nq` (and its `owner_gw_group`
  is **null**). **Search on the suffix, never the prefix.**
- **The Slack workspace name is not derivable from the API.** `get_project_integrations` returns an
  opaque hashed URL (`ff0e0e6a…`, `f74eede6…`, `b617b7da…`, `2b40893c…`). The name comes from the
  canvas registry in `editing-channel-canvases` or the UI.
- **Drive core-team share is correct on all four verticals** (checked 2026-07-29): each top folder
  lists its own `<vertical>-core-team-XXXX@mercor.expert` as `writer`. Read shares with
  `drive.permissions.list` + `supportsAllDrives`; the plain permissions tool hides group perms and
  shows only you as owner.
- **Platform chain is `create_listing` → `create_role(listing_id=…)` → `create_milestone(role_id=…)`.**
  All three tool descriptions say it independently.
- **`create_listing` publishes immediately.** `status` only accepts `active` or `archived`, so
  archiving is a retraction, not a hold. Neither `create_listing` nor `edit_listing` can set
  `isPrivate` or `disableApplications`; both schemas checked, so the private sourcing-funnel twin
  is UI-only work.
- **A role's `listing_id` is a link, not proof of a funnel.** Abacus has 11 roles and 9 distinct
  listing ids, but one of the nine (`list_AAABn0UjWoMO5Q3iY7hGba0c`, on the General Accountant
  role) is an **intake survey**: "Accounting Domain Intake", private, applications disabled. Of
  three sampled, one is public and open and one is private and closed, both `status: active`. **Two**
  Abacus roles have no listing, `EPM` and `External Expert Consultant`, not one.
- Canonical `function_id`s: Writer `func_AAABmwBg4kBIzamlZHZEqqOh`, EPM
  `func_AAABmwBg4kIrIOarSc5AXLtX`, Reviewer `func_AAABmwBg4j4J-tXfJYxKFK9K`, Team Lead
  `func_AAABmwBg4kOg1nAI-t5IKorI`, Project Consultant `func_AAABmwBg4j2C7sknLZdAxp5L`, Auditor
  `func_AAABmwBg4kGdfCYYRypPeap2`.

### Corrections applied to skills today

- "Only the EPM role has none" was **wrong** (see External Expert Consultant). A null `listing_id`
  is expected on the EPM role and on any invite-filled role; flag it only on roles meant to be
  sourced.
- The Drive-share step was documented as optional. It is required, and it can only run after the
  groups exist.
- `GOTCHAS.md` claimed `verify-vertical-spinup` was still owed (built) and that the mirror reaches
  GitHub (it does not).

---

## 4. THE WORK: vertical copy + numbers

This is what the session was scoping when it ended. Ryu's framing: bonus amounts, office-hours
times, weekly commitments, the instant offer and onboarding copy, and the instructions link
everywhere. **Nothing has been built.**

### 4a. Every number that clones in unconfirmed, and where it lives

| Number | Lives in |
|---|---|
| Onboarding bonus ($800), first-world bonus ($300) | **automations AND canvases** (fix one, miss the other) |
| Office-hours duration and times | canvases, calendars |
| Weekly commitment (15h, or 15-20h) | canvases, the listing's `hours_per_week`, the onboarding doc |
| Listing pay band `rate_min`/`rate_max` | the listing (candidate-facing) |
| Role `expected_billable_hourly` / `expected_payable_hourly` | roles (two inverted, see 2c) |
| Listing `referralAmount` | 240 to 600 across Sparta, no visible rule |
| Milestone `headcount_goal`, `hours_per_head_per_week` | milestones |
| EPM comp: weekly base × throughput multiplier, monthly bonus | see memory `reference_vigil_epm_compensation` |

Origin of the problem: Abacus's **$800 / 2h / 15h** propagated to Atria and Rampart untouched.
**Unverified and worth checking first: whether Atria's and Rampart's canvases still show them.**
If so, writers are reading Abacus's numbers right now.

### 4b. Every piece of copy that clones in and should not

- **Teams onboarding doc** (see 2d).
- **Instant offer text** — `edit_project` exposes `offer_extended_text`. Nothing in the package
  sets it and **no vertical's current value has been checked**.
- **Listing description**, carrying the source vertical's domain wording.
- **Listing rejection template** — Abacus's is titled "An Update To Your Accounting Expert
  Application". Copy that listing to a new vertical and you reject insurance candidates as
  accountants.
- Onboarding email copy.
- Canvas prose: domain wording, channel mentions.

### 4c. Instructions link, all seven destinations

1. Studio world layouts (~10 tasking + 6 GWB) — `replace-world-instructions-link`. **Covered.**
2. Slack canvases, labelled `<Vertical> Instructions` — `sweep-canvas-links`. **Covered.**
3. Drive folder — the tree holds it. **Covered.**
4. **Teams onboarding doc — NOT covered.**
5. **Automation message bodies — NOT covered.** (Ryu raised this; it was not accounted for.)
6. **Instant offer copy — NOT covered.**
7. The template's `[Outdated] Onboarding Document` link, upstream of all of it. **NOT covered.**

`replace-world-instructions-link` is scoped to Studio world layouts only. It does not touch
canvases, Teams, or automations, and it does not add Studio access links (that is the canvas
sweep's Studio access block).

### 4d. Proposed shape, agreed in principle, not started

1. **Read-only audit sweep first.** Establish how bad the four live verticals actually are across
   every surface in 4a to 4c. That shapes the skill. Do this before writing code.
2. **New skill `set-vertical-copy-and-numbers`.** Owns every surface above: inventory what each
   currently says, show the diff, **refuse to write until a human confirms each number**, write,
   re-read. Same interview-first pattern as the two skills built today.
3. **New skill for the instructions doc** (still the one acknowledged gap in the runbook, and
   Cadre's blocker). It creates the doc and fans the link to all seven destinations, replacing
   today's split where one skill does Studio, another does canvases, and nobody does Teams or
   automations.
4. **Two checks added to `verify-vertical-spinup`**: no inherited number on any surface, and the
   onboarding doc is not the placeholder.

**Hard blocker on 2 and 3:** the skill cannot invent a bonus amount or an office-hours time. Ryu
must supply the confirmed numbers per vertical, or a rule for deriving them. Ask before building.

---

## 5. Open questions for Ryu

1. Turn `auto_provision_email_enabled` on for Abacus, Atria and Rampart? (2b)
2. Fix the five `[CLONE ME]` template defects at source, or keep repairing per clone? (2a)
3. The two inverted role rates: intended, or wrong? (2c)
4. The confirmed comp numbers per vertical, for 4a.
5. `git init` plus a remote on `new-project-spinup/`?
6. Doc edits Ryu has not yet approved: step 5 should read `clone-studio-world` alone now that
   hooks are folded in, and step 7's "steps 1 to 7" needs the clarification already applied to the
   local markdown. **Targeted edits only, ask first.**
