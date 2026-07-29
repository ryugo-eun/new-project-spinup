---
name: create-vertical-teams-project
description: >
  Create the Mercor Teams project a new Sparta vertical hangs off: the project itself, its
  roles (one per expert profile plus EPM), auto-provisioned @mercor.expert email, the project
  owner set, and a test contract. This is STEP 0 of a new-vertical spinup, because every other
  step needs the `proj_` id. Inventories first so it can never create a duplicate project, and
  refuses to invent a pay rate. Use for "create the Teams project for <vertical>", "set up the
  new vertical's project", "add the roles to <vertical>", "start a new Sparta vertical".
  For the listing that hangs off a role, use `create-vertical-listing` (run it BEFORE the role).
---

# Create a new Sparta vertical's Teams project

Step 0 of the spinup. Nothing else can run first: tags, audiences, automations, Drive shares,
canvases and bots all key off the `proj_` id this produces.

## Inputs to collect first

Ask for ALL of this in one pass, read it back, and write nothing until the operator confirms.
A missing answer is a question to re-ask, never a blank to fill in from another vertical. Rates
especially: no rate is ever inherited.

| # | Ask | Notes |
|---|---|---|
| 1 | **Vertical name** | the codename and the project `name`, e.g. `Rampart`. Bare codename, not "Project Rampart" |
| 2 | **Domain label** | e.g. `Insurance`. Names the Drive folder `<Domain> (Project <Vertical>)` and the listing copy |
| 3 | **`client_project_name`** | what the client calls it. Required by `create_project` |
| 4 | **Description** | the one-paragraph vertical description. Model it on Abacus / Atria / Cadre, which all read "<Domain> professional-environment vertical: domain experts (...) design realistic scenarios, build data rooms, and author + evaluate ... tasks for an RL training environment" |
| 5 | **`data_acquisition_involved`** | true or false. Required for `humandata` |
| 6 | **The Modality + Data Type skill tag ids** | exactly one of each, required for `humandata`. This skill cannot resolve them for you, see step 2 |
| 7 | **Reference vertical** | which live vertical to model the role structure on. Abacus (9 expert roles) / Cadre (2) / Atria (1) |
| 8 | **The expert roles, per role** | exact `role_title`, taxonomy domain, `expected_billable_hourly`, `expected_payable_hourly`, `milestone_type` (expect `heads`) |
| 9 | **EPM role rates** | billable and payable. Live verticals carry placeholders here (1/1, 2/1), so ask for the real intent |
| 9b | **EPM comp arrangement** | the weekly base, the throughput multiplier, and the monthly bonus. Separate from row 9: row 9 is two numbers on the Teams role record, this is what an EPM actually gets paid. **There is no field and no document that holds it** (checked 2026-07-29: no Sparta skill mentions it, and the EPM Training doc carries no comp section), so it cannot be written anywhere by this skill. Ask anyway, and hand it back so the SPL records it wherever they keep it. An unasked EPM comp arrangement is how an EPM starts work without knowing their own pay |
| 10 | **Milestone, per role** | `start_date`, `end_date` (YYYY-MM-DD, PST), `hours_per_head_per_week`, and the goal matching the type (`headcount_goal` for heads) |
| 11 | **Project owners** | Mercor staff emails for `add_project_secondary_owners` |
| 12 | **Who the test contract goes to** | one real person, step 6. The project is not proven without it |
| 13 | **Whether the listings exist yet** | one per expert role. If not, `create-vertical-listing` runs before step 3 |

Resolve the taxonomy ids yourself rather than asking for raw ids: `list_taxonomy_domains` for
`domain_id`, and the function table below for `function_id`. Read the resolved names back to the
operator so a wrong domain gets caught before it is written.

## Premortem: what goes wrong, and the guard

| Failure | Guard built into the procedure |
|---|---|
| Writing before the intake is complete | The inputs table above. Every field confirmed, nothing inferred |
| A second project for a vertical that already has one, splitting the roster | Step 1 inventories `list_projects` and STOPS on any near-name match |
| Role created before its listing, so `listing_id` is null forever | Step 3 refuses to run before `create-vertical-listing`. The API's own order is listing → role → milestone |
| `auto_provision_email_enabled` left OFF (the platform default) | Step 4, verified by re-read. Without it nobody gets an @mercor.expert address and every Google-group and Drive grant below is inert |
| **Payable rate above billable**, i.e. the role loses money per hour | Step 3 blocks on `expected_billable_hourly > expected_payable_hourly` and makes the operator confirm both numbers out loud |
| Rates copied from another vertical | Every number is operator-confirmed. Never inherit |
| Project created under Mercor internal instead of Sparta | company is pinned, step 0 |
| "Done" reported with no contract ever tested | Step 6 |

## Fixed context

- Company is always **Sparta** `company_AAABlLQjCsYYoXP4rsZKpY0y`. Never Mercor internal
  (`company_AAABnoo-tWquhOQciSJPdrCE`).
- Sparta verticals are `project_type: humandata`, `annotation_platform: rl_studio`.
- **The project id's last 4 characters become the vertical's group/audience suffix.** Cadre is
  `proj_AAABn6Z-4irb63tDd_NNRr5G` and its groups are `cadre-core-team-Rr5G@mercor.expert`,
  `hr.-.sparta.vertical-Rr5G.admins@mercor.expert`. So the id you create here silently names
  every Google group later. Record it.

### Canonical role functions (`list_project_functions`, whole list, 2026-07-29)

| Function | id |
|---|---|
| Writer | `func_AAABmwBg4kBIzamlZHZEqqOh` |
| Expert Project Manager | `func_AAABmwBg4kIrIOarSc5AXLtX` |
| Reviewer | `func_AAABmwBg4j4J-tXfJYxKFK9K` |
| Team Lead | `func_AAABmwBg4kOg1nAI-t5IKorI` |
| Project Consultant | `func_AAABmwBg4j2C7sknLZdAxp5L` |
| Auditor | `func_AAABmwBg4kGdfCYYRypPeap2` |

Every live vertical uses exactly two of these: **Writer** for each expert role and **Expert
Project Manager** for the single `EPM` role. Confirmed on Abacus, Atria and Cadre. Do not
introduce Reviewer or Team Lead roles unless the operator asks; reviewers are a Studio subrole
and a team tag, not a Teams role.

## Procedure

**0. Run the intake above and confirm the company is Sparta.** Read the whole set back, including
each role with its two rates side by side, and wait for a yes.

**1. Inventory. Never skip.**
```
list_projects(company_id=Sparta, query="<vertical>")
```
Also query the domain word (`query="human resources"`). If anything plausibly matches, STOP and
show it. `create_project` rejects an exact duplicate active name, but it happily creates
`Cadre HR` next to `Cadre`, and a split roster is not something you can cleanly undo.

**2. Create the project.**
```
create_project(
  company_id = Sparta,
  name = "<Vertical>",                    # bare codename, e.g. "Cadre". Not "Project Cadre"
  client_project_name = <what the client calls it>,
  project_type = "humandata",
  annotation_platform = "rl_studio",
  data_acquisition_involved = <ask>,
  description = <the one-paragraph vertical description>,
  skills = [<one Modality tag id>, <one Data Type tag id>],
  screenshot_enabled = true,
)
```
- `project_type=humandata` makes `annotation_platform`, `data_acquisition_involved` and the
  skills pair REQUIRED. **The two skill tag ids are the one thing this skill cannot hand you.**
  Read them off a live vertical or let the API's validation error enumerate the valid values,
  and never guess a tag id. If you cannot resolve them, say so and stop; do not drop the field
  and hope.
- Name convention: live projects are the bare codename (`Abacus`, `Atria`, `Cadre`), while the
  Drive folder is `<Domain> (Project <Vertical>)`. Keep both conventions.
- **Insightful project creation must succeed or the whole call fails and writes nothing.** A
  failure here is not "partially created", it is not created. Re-run after fixing.
- Record the returned `proj_` id and its last 4 characters.

**3. Roles, one per expert profile, plus EPM. AFTER the listing exists.**

`create_role` is step 2 of the platform's 3-step sourcing chain: **`create_listing` →
`create_role(listing_id=...)` → `create_milestone(role_id=...)`**. All three tools state this
independently. So run `create-vertical-listing` first and bring back its `list_` id.

```
create_role(
  project_id = <new>,
  role_title = "<Expert profile title>",       # e.g. "HR Administrative Specialist"
  function_id = Writer,
  domain_id = <taxonomy tagId from list_taxonomy_domains>,
  listing_id = <from create-vertical-listing>,
  milestone_type = "heads",
  expected_billable_hourly = <operator>,
  expected_payable_hourly  = <operator>,
)
```
Then the EPM role: `role_title="EPM"`, `function_id=Expert Project Manager`, **no
`listing_id`** (EPMs are not sourced through a public listing), rates operator-confirmed.

**HARD GUARD: `expected_billable_hourly` must be greater than `expected_payable_hourly`.**
Bill above pay. Two live roles violate this and are recorded at a loss (see Known defects), so
this is a real failure mode, not a hypothetical. If the operator's numbers invert it, do not
write. Say the numbers back plainly ("you would be paying 85 an hour and billing 50") and wait.

Live reference shape, for sanity only, never to copy: Abacus expert roles bill 175 and pay 90;
Cadre's HR Expert 165/90 and HR Administrative Specialist 145/60.

Rejects a duplicate role title within the project, so re-running is safe on that axis.

**4. Auto-provision email.** Ships OFF. Every live vertical needs it ON, and every Google
group, Drive share and calendar grant downstream is addressed to `@mercor.expert`, so an expert
without one has access to nothing.
```
set_project_autoprovision_email(project_id=<new>, enabled=true)
→ get_project_integrations(project_id=<new>)   # must show auto_provision_email_enabled: true
```
`get_project` does NOT expose this flag. Only `get_project_integrations` does, which is exactly
why it gets missed.

**5. Owners.** `add_project_secondary_owners(project_id, owner_emails=[...])`. Additive and
idempotent, so safe to re-run. Inspect first with `list_project_secondary_owners`.

**6. Milestone and a test contract.** `create_milestone(project_id, role_id, type=<the role's
milestone_type>, start_date, end_date, hours_per_head_per_week, headcount_goal)` with dates
YYYY-MM-DD, PST. Then put ONE real person on a contract and confirm they land: the project is
not proven until a contract exists and the expert can actually reach the work.

## Verify before handing off

```
get_project(project_id, include=['roles'])       # roles, titles, rates, listing links
get_project_integrations(project_id)             # auto_provision_email_enabled: true
list_project_secondary_owners(project_id)
```
Report the `proj_` id, its 4-character suffix, each role with its function and its
billable/payable pair, and which roles carry a `listing_id`.

**A null `listing_id` is not automatically a defect.** It is expected on the EPM role and on any
role filled by direct invite rather than sourcing: Abacus has two such roles, `EPM` and
`External Expert Consultant` (verified 2026-07-29). Ask the operator which roles are meant to be
sourced, and flag a null only on those. Sourcing cannot run against a role with no listing.

## Known defects in live verticals (found 2026-07-29 PT, unfixed)

Two roles have payable above billable, i.e. negative margin as recorded:
- **Atria "Healthcare Admin Expert"** `8d98f3fc-3a26-415d-8221-ba621510e352`: billable 50,
  payable 85.
- **Abacus "EPM"** `87b72b0e-fdb8-4ccc-8cdf-dc4f358d8ef1`: billable 55, payable 90.

Cadre's EPM (1/1) and Atria's EPM (2/1) are placeholders, not real rates. Flag all of these to
the operator when auditing; do not copy any of them onto a new vertical.

## Gotchas

- **Roles are not tags.** This creates the *contract* structure. The Studio role, Slack
  channels, Google group and Insightful project all come from `provision-vertical-teams-integrations`,
  driven by vertical-prefixed team tags. Both are needed; neither substitutes.
- **`create_role` needs both `function_id` and `domain_id`**, and both are mandatory even
  though the schema types them nullable. Validation errors list the valid values.
- **`milestone_type` must match** what `create_milestone` is later called with, and type-specific
  goal fields are exclusive: HEADS wants `headcount_goal`, HOURS `hours_goal`, TASKS
  `tasks_goal` + `aht`. Passing another type's goal field is rejected.
- **Studio-to-Teams project link is still a documented gap.** There is no
  `enable_project_integration` slug for Studio and the campaign clone sets no project id. Do not
  claim the link exists because the project and campaign both do.

## Hand off

1. `create-vertical-listing` (must precede step 3 above).
2. `provision-vertical-slack-channels`, then `provision-vertical-teams-integrations`, which
   turns tags into real access using this project id.
3. `verify-vertical-spinup` area A checks this project's roles, owner and the
   auto-provision flag.
