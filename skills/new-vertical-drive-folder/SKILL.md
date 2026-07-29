---
name: new-vertical-drive-folder
description: >
  Clone the "_CLONEME (New Vertical Template)" Google Drive folder into a full Drive
  folder tree for a new Sparta vertical, renamed to the new vertical/domain. Use when
  standing up a new Sparta vertical and you need its Drive folder created and renamed
  from the template. Triggers on "set up the Drive folder for <vertical>", "spin up the
  <vertical> Drive folder", "clone the vertical Drive template", "new vertical Drive folder".
---

# New Vertical Drive Folder (clone from CLONEME)

Creates a new Sparta vertical's Google Drive folder tree by cloning the `_CLONEME`
template and renaming every placeholder to the new vertical. This is the Drive-folder
step of a new-vertical spinup (Studio/Teams/Slack are separate — see `clone-sparta-campaign`).

## Inputs to collect first

Ask the operator for both, then confirm before writing:
- **VERTICAL** — the project name, e.g. `Rampart`, `Atria`.
- **DOMAIN** — the human domain label, e.g. `Insurance`, `Admin Healthcare`.
- **Target parent** — defaults to the Sparta shared drive `1ZkXpFKOl4EbL7w06EMb64LHEnSF9p3PC`
  (verticals live as sibling folders there). Or the operator may have pre-created an empty
  top folder — if so, use its id and skip step 1.

## Token model

The CLONEME files use three literal placeholder tokens. The clone replaces all three:
- `{{VERTICAL}}` → the VERTICAL input, title case (e.g. `Rampart`)
- `{{VERTICAL_LOWER}}` → the same, lowercased (e.g. `rampart`). **Slack channel names only.** Added
  2026-07-29. Channels are lowercase (`#rampart-epms`) while `{{VERTICAL}}` is title case, so a
  single token cannot serve both, and `#Rampart-epms` is not a channel
- `{{DOMAIN}}`   → the DOMAIN input (e.g. `Insurance`)

There is a fourth token, and it is the one exception to everything below:

- `{{INSTRUCTIONS_DOC_URL}}` → **deliberately NOT substituted by this skill.** It sits in the EPM
  Training doc's "Instructions Doc" line. This skill runs at step 7; the writer instructions doc does
  not exist until step 12, so there is nothing to substitute yet. It is filled by the step-14 link
  pass (`replace-instructions-link`). Leaving it as a token rather than `[TBD]` is deliberate: a
  token is machine-findable, so the link pass can fill it, and a `[TBD]` is only findable by a human.

**So the verify rule is "no `{{` tokens left EXCEPT `{{INSTRUCTIONS_DOC_URL}}`."** Do not "fix" that
one, and do not report it as a defect at step 7. Report it as a defect only if it survives step 14.

Top folder name convention: **`{{DOMAIN}} (Project {{VERTICAL}})`** → e.g. `Insurance (Project Rampart)`.

## CLONEME source tree (do NOT edit these — they are the template)

Top: `_CLONEME (New Vertical Template)` = `1lQpB0OCQFLbkBRp04z1VC00jpfqUzJjT`

```
_CLONEME (New Vertical Template)                                  1lQpB0OCQFLbkBRp04z1VC00jpfqUzJjT
├── [INT] Project {{VERTICAL}}                                    1AQKs5eoZKKgkpQxm6o9uFqEUrlM40m2r   [folder]
│   ├── {{VERTICAL}} EPM Training                                 1WJbvFBSQ-ViMPq4Css43GNCmrdnfTpPd8uGpq4JqAac   [doc]
│   ├── New Project Spinup                                        1FAKaxJ68HjxUtNq5zQYVYmSo4NRwdahe   [folder]
│   │   ├── {{VERTICAL}} Startup Playbook                         1qTPI6yWHC_GuJn-mRIgCpIBvn_6-jxqUpCGLi_wZYOE   [doc]
│   │   ├── Vertical Setup Menu + Automation Inventory (Sparta)   1neyX6eru67RZQwyPow6otYzlVo1vzSKwkN285r9-V_M   [sheet]
│   │   └── {{VERTICAL}} Startup Essentials                       1dli4X-Kggiu1ztMRXacAVl-XmdWqvke2CF_pKE0ZhMk   [sheet]
│   └── Ops                                                       1TmF5G2ildBvQsy0Fy3qEqQ5xquwXV8A-   [folder]
│       ├── Automations                                          1335cE8XLAuNdXzyKX29-FrpzVE8TLUXW   [folder]
│       │   └── {{VERTICAL}} Automations                         1Z3ei_zxZjsh2Se-LT7ky-3JjUNHzHwWCQ15f_13dvBc   [sheet]
│       └── Bonus and Reimbursements                             1ZkgMOW5tTFWPwNaYhl1_iTf0hh4MDwxm   [folder, empty]
└── Expert Facing                                                 1tDkN-XrTHEcxINKENpkloKYcqcn9VCIO   [folder]
    ├── LLM Usage Reimbursement Request - Project {{VERTICAL}}    1YxQNWgqZskBFW75uI-mRpKRCvdW7tSeLDUqrmLqVUh0   [form]
    └── Bonus Compensation - Project {{VERTICAL}}                 1vEsjioZYZRuZ79qpvZHVITANYaRElgJe89UnumwuNqY   [form]
```

Bodies that carry the token: `{{VERTICAL}} Automations` sheet (Atria-derived), both forms
(title/description/confirmation).

**The EPM Training doc carries tokens too, as of 2026-07-29.** It did not before, and this skill
used to claim it was generic. The template's copy
(`1WJbvFBSQ-ViMPq4Css43GNCmrdnfTpPd8uGpq4JqAac`) was **Abacus's document verbatim**, with no token
in it anywhere: the heading, `#abacus-epms` three times, `real-world accounting workflows`,
`Abacus is a Sparta vertical`, `(Abacus tracker: TBD)`, the `"Sparta - Abacus - World"` Insightful
timer, a live link to Abacus's writer onboarding doc carrying its `$800` payment / `2h` cap /
`15-30 hr/wk` / `9am/3pm PT` numbers, and a live **hyperlink** to Abacus's instructions doc.

**It was tokenized in place 2026-07-29**, 14 occurrences, so a fresh clone now inherits tokens and
`[TBD]`s instead of Abacus. Re-read after the edit confirms zero `Abacus` and zero `accounting` left
in the template. The comp and commitment values are deliberately `[TBD]` and NOT tokens: they are
per-vertical decisions an operator confirms, not values derivable from a vertical's name.

**Step 4b still runs anyway, for two reasons that do not go away:**

1. **The rename made the defect invisible.** The template's filename was ALREADY
   `{{VERTICAL}} EPM Training`, so Cadre's copy sat in Drive correctly titled `Cadre EPM Training`
   with an Abacus body underneath. A check on the filename PASSES. Only reading the body catches it,
   which is exactly why this survived a spinup and an Essentials-sheet tick.
2. **Templates get re-contaminated.** This one broke because a working vertical's doc was used as
   the starting point. Nothing stops that recurring, so the clone verifies rather than trusts.

The Startup Playbook, Startup Essentials and Vertical Setup Menu do appear generic, but that was
the same assumption that turned out false here, so step 4b greps them too rather than trusting it.

## Why not just `copy_file` the top folder?

The Drive API does **not** recursively copy folders. You must recreate each folder and copy
each file individually. That is what the steps below do.

## Procedure

Tools: `mcp__claude_ai_Google_Drive__create_file` (folders), `mcp__claude_ai_Google_Drive__copy_file`
(files, with the renamed `title`), and `mcp__mercor-mcp__google_workspace_drive_call` (body
find-replace on Docs/Sheets/Forms). Capture each returned id — later steps need parent ids.

**1. Top folder.** `create_file` folder, title `{{DOMAIN}} (Project {{VERTICAL}})`,
parent = target parent (default Sparta drive). Skip if the operator pre-made it.

**2. Folder tree** (create in order, each under the id from the prior step):
- under top: `[INT] Project {{VERTICAL}}`, and `Expert Facing`
- under `[INT] Project {{VERTICAL}}`: `New Project Spinup`, and `Ops`
- under `Ops`: `Automations`, and `Bonus and Reimbursements`

**3. Copy the 7 files** (`copy_file`, set `title` with `{{VERTICAL}}` replaced by VERTICAL, `parentId` = the matching new folder):
| CLONEME file id | new parent | new title |
|---|---|---|
| 1WJbvFBSQ-ViMPq4Css43GNCmrdnfTpPd8uGpq4JqAac | [INT] Project <V> | `<V> EPM Training` |
| 1qTPI6yWHC_GuJn-mRIgCpIBvn_6-jxqUpCGLi_wZYOE | New Project Spinup | `<V> Startup Playbook` |
| 1neyX6eru67RZQwyPow6otYzlVo1vzSKwkN285r9-V_M | New Project Spinup | `Vertical Setup Menu + Automation Inventory (Sparta)` |
| 1dli4X-Kggiu1ztMRXacAVl-XmdWqvke2CF_pKE0ZhMk | New Project Spinup | `<V> Startup Essentials` |
| 1Z3ei_zxZjsh2Se-LT7ky-3JjUNHzHwWCQ15f_13dvBc | Ops/Automations | `<V> Automations` |
| 1YxQNWgqZskBFW75uI-mRpKRCvdW7tSeLDUqrmLqVUh0 | Expert Facing | `LLM Usage Reimbursement Request - Project <V>` |
| 1vEsjioZYZRuZ79qpvZHVITANYaRElgJe89UnumwuNqY | Expert Facing | `Bonus Compensation - Project <V>` |

(`<V>` = VERTICAL.) Leave `Bonus and Reimbursements` empty (see step 6).

**4. Replace tokens in the copied Docs/Sheets.** For each copied Doc use
`docs.documents.batchUpdate` with three `replaceAllText` requests; for each copied Sheet use
`sheets.spreadsheets.batchUpdate` with three `findReplace` requests (`allSheets: true`). Replace
`{{VERTICAL_LOWER}}` → the lowercased vertical **first**, then `{{VERTICAL}}` → VERTICAL, then
`{{DOMAIN}}` → DOMAIN, all `matchCase: true`. Run it on all copied Docs/Sheets (harmless where a
token is absent). Expect ~8 changes in the Automations sheet and ~14 in the EPM Training doc.

**Order matters: `{{VERTICAL_LOWER}}` before `{{VERTICAL}}`.** `{{VERTICAL}}` is a substring of
`{{VERTICAL_LOWER}}`, so replacing the short token first turns `{{VERTICAL_LOWER}}` into
`Rampart_LOWER}}`. A leftover `_LOWER}}` in a live doc is the tell that this ran in the wrong order.

**4b. Recast the source vertical OUT of every copied Doc, then prove it.** Token replacement is not
enough, because the template's EPM Training doc carries **Abacus's identity as literal text, not as
a token** (see the table above). Skipping this ships a doc titled for the new vertical that sends
its EPMs to Abacus's channels, Abacus's docs and the wrong Insightful timer.

Do it in two calls, in this order. The order matters:

1. **The hyperlink first, by index.** The Abacus instructions-doc URL is a real hyperlink, so
   `replaceAllText` would change the visible text and leave the link pointing at Abacus, which is
   strictly worse than an obvious error. `docs.documents.get` with a `fields` mask of
   `body.content(paragraph(elements(startIndex,endIndex,textRun(content,textStyle(link)))))` to find
   the run, then `deleteContentRange` + `insertText` the replacement + `updateTextStyle` with
   `fields: "link"` and an empty `textStyle` to clear the link. Index-based edits must be their own
   call, because `replaceAllText` in the same batch shifts every index after it.
2. **Then the text**, one `replaceAllText` per row of the table above, **longest and most specific
   string first**. Never a bare `Abacus` → `<Vertical>` sweep: that would rewrite
   `Read the writer-facing Abacus Onboarding Doc: <abacus url>` into a line labelled for the new
   vertical still pointing at Abacus's doc. Replace the whole sentence, URL included.

**Every number the source doc states is the SOURCE's number.** The onboarding payment, the starting
hours cap, the weekly commitment and the office-hours times all get `[TBD]` unless the operator
confirms them for this vertical. Do not carry them across, and do not treat Abacus as a fallback:
Abacus states its own weekly commitment as 15 to 20 in its onboarding doc, 15 to 30 in this EPM doc,
and 15 in its canvases, and its office hours as 9am/3pm PT against a live 9am/4pm PT calendar.

**Prove it.** Re-read every copied Doc and Sheet with `read_file_content` and grep for: each other
live vertical's name (`Abacus`, `Atria`, `Rampart`, `Cadre`, `Panacea`, `Vigil`), `#<source>-`, the
source domain's vocabulary, and both Abacus doc ids `1u-Go8Cr` and `1x6WJoAT`. Report the counts.
A non-zero count is a FAIL, not a note. This is check K7 in `verify-vertical-spinup`.

**5. Replace tokens in the two copied Forms** (`forms.forms.batchUpdate` on each new form id):
- **LLM Reimbursement form** — two requests in one batch:
  1. `updateFormInfo`, `updateMask: "title,description"`, info.title
     `LLM Usage Reimbursement Request - Project <V>`, info.description
     `Submit this form to request reimbursement for costs associated with Large Language Model (LLM) usage specific to Project <V>.`
  2. `updateItem`, `location.index: 7`, `updateMask: "title"`, item MUST include the full
     `questionItem` (id `15896343`, questionId `0d79f613`, CHECKBOX option `I agree`, required)
     or the API rejects it ("cannot be changed into a non question Item type"); title
     `Confirmation: I certify that the costs claimed are exclusively for LLM usage related to Project <V> and comply with Project and Company reimbursement policy.`
- **Bonus Compensation form** — one `updateFormInfo`, `updateMask: "title"`, info.title
  `Bonus Compensation - Project <V>`.

**6. PAUSE for response-sheet linking (cannot be automated).** The forms have NO linked
response sheets — the Forms/Drive API cannot create a response destination, and copying the
template's response sheets makes dead sheets, so never do that.

**RECOMMENDED ORDER (confirmed cleanest on Cadre 2026-07-28): link while the forms are in
`Bonus and Reimbursements`, not Expert Facing.** A form's `(Responses)` sheet + `(File responses)`
folder are always created in the form's CURRENT folder. So: move BOTH forms into
Ops/Bonus and Reimbursements first, have the operator link there, then move ONLY the forms back to
Expert Facing (step 7 becomes a no-op for the responses — they're already home, and the sensitive
response sheets never sit in the writer-readable Expert Facing folder). Hand the operator this,
then wait:

> Open each form (now in Bonus and Reimbursements) → **Responses → Link to Sheets → Create a new
> spreadsheet**, for both forms. Tell me when both are linked.

(Legacy order — forms left in Expert Facing at link time — still works but then you must run step 7
to relocate the response artifacts. Do not proceed until the operator says linking is done.)

**7. Relocate the response artifacts into Ops/Bonus and Reimbursements.** Linking in the UI
creates the `(Responses)` sheet(s) and a `... (File responses)` folder as children of the
**form's own folder — i.e. `Expert Facing`, not** `Bonus and Reimbursements`. Also, the
`(File responses)` folder is often born with a STALE name carried from the template/source
vertical (Rampart's read "Project Atria"). So:
- `search_files parentId = '<Expert Facing id>'` and pick out everything that is NOT one of the
  two forms: the two `... (Responses)` spreadsheets and the `... (File responses)` folder.
- For each, `drive.files.update` with `addParents = <Ops/Bonus and Reimbursements id>`,
  `removeParents = <Expert Facing id>`, `supportsAllDrives: true` to move it.
- On the `(File responses)` folder, also set `body.name` to
  `LLM Usage Reimbursement Request - Project <V> (File responses)` in the same update, to
  scrub any stale source-vertical name.
Confirm afterward that `Bonus and Reimbursements` holds the 2 response sheets + the file-responses
folder and `Expert Facing` holds only the 2 forms — this is the Atria layout, confirmed the
intended one on Cadre 2026-07-28 (forms stay in `Expert Facing`; only the response sheets move).

**8. Share the folders to the vertical's Google groups (Abacus model). REQUIRED, not optional.**
A fresh clone is owned only by you; EPMs and writers get nothing until you share, and the Teams
side creating the group does NOT share anything to it. Match Abacus: the **core-team group gets
`writer` on the TOP folder** (the whole tree inherits), the writer/everyone groups get **reader**
on `Expert Facing` only.

Live core-team shares, all confirmed present 2026-07-29 (PT):

| Vertical | Top folder | Core-team group (role `writer`) |
|---|---|---|
| Abacus | `Accounting (Project Abacus)` `1tWBDFknQcg0n4zilASotpiXn1zxjJsCZ` | `abacus-core-team-HKSh@mercor.expert` |
| Atria | `Admin Healthcare (Project Atria)` `16o0nu1kcAi6GwPJEPdw1ZzgMax_2I1yv` | `atria-core-team-l4Nq@mercor.expert` |
| Cadre | `Human Resources (Project Cadre)` `1q0FoJQIx1ptbavnq6qExc1aj9pV1HdSh` | `cadre-core-team-Rr5G@mercor.expert` |
| Rampart | `Insurance (Project Rampart)` `1WkWUayAXIOcFrpEZmCMHxrjwhMAHKfhu` | `rampart-core-team-zZi7@mercor.expert` |

- **Find the groups** via `list_project_audiences(project_id)` — the tag-driven audiences expose
  Google-group targets whose `externalId` follows `<vertical>-<name>-<projSuffix>@mercor.expert`.
  These are the RIGHT groups; do NOT use the `hr.-.sparta.vertical-<suffix>.admins/.epms` names
  from `get_project_integrations` (different, provisioning-level naming). You want:
  - EPM group = the google target on the "`<V> EPM`" tag audience (name `<v>-core-team`), e.g.
    `cadre-core-team-Rr5G@mercor.expert`.
  - everyone group = the google target on the **everyone-anchored** audience (name `<v>-everyone`).
    NOTE: the everyone audience often has only Insightful/Slack targets and NO google target until
    the operator adds one — if it's missing, ask the operator to create the everyone group first.
  - writer groups = `<v>-completed-wt` (active writers) + `<v>-onboarding`.
- **Apply** with `drive.permissions.create`, `supportsAllDrives: true`, `sendNotificationEmail: false`,
  body `{type:"group", role, emailAddress}`:
  - TOP folder → EPM/core-team group, role `writer` (cascades to the whole tree).
  - `Expert Facing` folder → everyone group (+ `<v>-completed-wt` + `<v>-onboarding`), role `reader`.
- Abacus ALSO shares to the three legacy Sparta EPM groups (`consulting-epms-_r3W`,
  `vigil-epms-x4nT`, `healthcare-epms-873f`) as writer for cross-vertical EPM visibility — optional,
  add only if the operator wants every Sparta EPM to see it.
- **Verify** with `drive.permissions.list` + `supportsAllDrives:true` (the basic
  `get_file_permissions` HIDES group/inherited perms and shows only you as owner — use
  `permissions.list` with `supportsAllDrives` to see the real group shares).

## Verify

List children of the new top folder and each subfolder; confirm 6 folders + 5 docs/sheets +
2 forms, all titled with the vertical name and no `{{` tokens left in titles or bodies, with the
single deliberate exception of `{{INSTRUCTIONS_DOC_URL}}` in the EPM Training doc (see Token model).

Grep for `_LOWER}}` specifically as well as `{{`. A stray `Rampart_LOWER}}` means step 4 replaced
the tokens in the wrong order. `{{INSTRUCTIONS_DOC_URL}}` surviving is CORRECT at this step.

**Titles are not enough, and reporting on titles alone is how this skill shipped a broken doc.**
Also confirm, by READING each copied Doc and Sheet: zero mentions of any other live vertical, zero
mentions of the source domain, and zero occurrences of Abacus doc ids `1u-Go8Cr` / `1x6WJoAT`. Report
the grep counts, not a summary judgement.

## Notes

- Studio IDs, comp amounts ($), pod tags, and Teams project ids do NOT exist for a brand-new
  vertical — the Startup Playbook/Essentials/Menu and Automations sheet keep their fill-in
  placeholders. That is expected; the operator completes them once identity is provisioned.
- First real use: **Rampart (Insurance)**, cloned 2026-07-22. Rampart top folder
  `1WkWUayAXIOcFrpEZmCMHxrjwhMAHKfhu`.
- If a `copy_file` on a Form ever fails, re-run it; Forms occasionally 500 on copy.
