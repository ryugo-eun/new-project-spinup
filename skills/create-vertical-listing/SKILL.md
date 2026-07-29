---
name: create-vertical-listing
description: >
  Create the Mercor job listing a Sparta vertical sources experts through, by copying an existing
  Sparta listing and adapting it: title, description, pay band, commitment, location eligibility,
  application steps, custom pipeline steps and evaluation criteria, then link it to a project role.
  Interviews the operator for the vertical name, domain, role and the source listing to copy from
  before it writes anything. Run ONCE PER EXPERT ROLE, and always BEFORE `create_role`, because the
  platform's chain is listing to role to milestone. Knows the trap that a new listing goes LIVE the
  moment it is created. Use for "create the listing for <vertical>", "make a listing for the <role>
  role", "copy the Abacus listing for the new vertical", "set up the hiring funnel for the new
  vertical". For the project the listing hangs off, use `create-vertical-teams-project`. This is NOT
  the marketplace `sourcing-request` skill, which writes the Slack post asking someone else to source.
---

# Create a Sparta vertical's job listing

Step 0a of the spinup. The listing is the whole candidate-facing funnel and the thing sourcing
runs against, so nothing arrives on the vertical until it exists.

**One listing per expert role, not one per vertical.** Abacus has 11 roles carrying **9 distinct
listing ids**, Cadre 2. But do not read "9 listings" as 9 equivalent open funnels, verified
2026-07-29:

- **Some are closed.** Of three sampled, `Tax Accountant / Specialist` is public and open, while
  `Forensic Accounting & Investigations Specialist` is `isPrivate: true` with
  `disableApplications: true`. Both are `status: active`, so status alone tells you nothing about
  whether anyone can apply.
- **One is not a hiring listing at all.** Abacus's `General Accountant` role points at
  `list_AAABn0UjWoMO5Q3iY7hGba0c`, titled `Accounting Domain Intake — Shape Upcoming Accounting
  Engagements`: a 30-minute written survey, private, applications disabled. A role's `listing_id`
  is a link, not proof that the link is a funnel.
- **Two Abacus roles have no listing**, not one: `EPM` and `External Expert Consultant`. So a
  null `listing_id` is normal for the EPM role AND for any role that is filled by direct invite.

Check what a listing actually is before you copy it. Copying an intake survey as the basis for a
hiring listing is an easy mistake given how they are linked.

**Never author a listing from scratch.** Always start from a live Sparta listing the operator
names, so the structure, tone and section order stay consistent with what already converts.

## Inputs to collect first

Ask for ALL of this in one pass, read it back, and write nothing until the operator confirms.
If any answer is missing, ask again rather than filling it in. Do not infer a rate, a country
list or a domain from another vertical.

| # | Ask | Notes |
|---|---|---|
| 1 | **Vertical name** | the codename, e.g. `Rampart`. Used for nothing candidate-facing, but it scopes everything else |
| 2 | **Domain label** | the human domain, e.g. `Insurance`, `Human Resources` |
| 3 | **Teams project id** | `proj_...`, from `create-vertical-teams-project`. Confirm with `get_project` that the id resolves to the expected name |
| 4 | **Which role is this listing for** | one listing per expert role. Get the exact role title |
| 5 | **SOURCE LISTING to copy from** | required. A `list_` id, or a vertical + role name to resolve. See the pick-list below |
| 6 | **Candidate-facing title** | often the role title verbatim, but confirm. This is what applicants see |
| 7 | **Pay band** | `rate_min` and `rate_max` |
| 8 | **The role's payable rate** | so the band can be reconciled against it (step 3) |
| 9 | **Commitment** | expect `hourly`. Confirm, never assume |
| 10 | **Hours per week** | a number or deliberately none. Live Sparta listings run both |
| 11 | **Eligible countries** | ISO 3166-1 alpha-3, e.g. `["USA"]`. Ask about `ineligible_location` too |
| 12 | **Public, or a private sourcing funnel** | the private twin needs UI work, see Unverified |
| 13 | **What changes in the copy** | which domain wording, sub-domains, credentials and ideal-background bullets differ from the source |
| 14 | **Listing owner** | `owner_ids`, if it should not default to whoever runs this |
| 15 | **Referral amount** | a dollar figure. Live Sparta listings run 240 to 600 with no visible rule, so there is nothing to default to. Not writable by API, see step 7 |
| 16 | **Rejection template** | subject + body. Auto-reject is ON by default at 7 days, so a listing with no template rejects candidates using the platform default. Not writable by API, see step 7 |
| ~~17~~ | ~~**Instant offer text**~~ | **DO NOT ASK. Settled 2026-07-29:** the instant offer email is shared platform-wide and needs no per-vertical work. `offerExtendedText` is null on every Sparta listing including Abacus's flagship Accounting Expert, so null is correct, not a gap. (A separate PROJECT-level `offer_extended_text` exists on `edit_project`, but no tool reads it back, so assert nothing about it.) |

### Source listings to offer (live, ids read 2026-07-29 PT)

| Vertical | Role | Listing id |
|---|---|---|
| Cadre (HR) | HR Administrative Specialist | `list_AAABn6uMUYyPrNM3gPhHkK9u` |
| Cadre (HR) | Human Resources Expert | `list_AAABn6aBpdG_oTdx-CFL6a7r` |
| Atria (Admin Healthcare) | Healthcare Admin Expert | `list_AAABn3FrsqJqPFplFuhEEYix` |
| Abacus (Accounting) | General Accountant | `list_AAABn0UjWoMO5Q3iY7hGba0c` |
| Abacus (Accounting) | Accounting Expert | `list_AAABn0XwSkw51Y_6zq5InYan` |
| Abacus (Accounting) | Tax Specialist | `list_AAABn4HHtJldqWqSCV1OX4hO` |
| Abacus (Accounting) | Audit & Controls Specialist | `list_AAABn4HIBZaY-jR66IBCV58B` |

Re-resolve rather than trusting this table if it has aged: `list_project_roles(project_id)`
returns each role's `listing_id`, which is the authoritative pairing.

## Premortem: what goes wrong, and the guard

| Failure | Guard |
|---|---|
| **The listing goes live before anyone meant it to.** `create_listing` creates with `status=active` and there is no draft state | Step 4. Publish only when the copy is approved. If it went out early, `edit_listing(status="archived")` is the only way back |
| A listing written from scratch that reads nothing like the others | Step 2 requires a source listing |
| `commitment` defaults to `full-time` | Step 3 pins the confirmed value. Every live Sparta vertical listing is hourly |
| Pay band contradicts what the role actually pays | Step 3 reconciles the band against the role's `expected_payable_hourly` and stops on a mismatch. Candidates read the band as their pay |
| Source vertical's domain wording left in the copy | Step 2 diffs the description out loud, section by section |
| Description reuses standardized Mercor referral/contract/payment copy | Step 3 runs `validate_listing_description` and will not save while `isValid` is false |
| Role created first, so the two never link | This skill runs before `create_role`; the link is made from the role side with `listing_id` |
| A duplicate listing quietly competing for the same candidates | Step 1 inventories `list_listings` |

## Fixed context

- Company is **Sparta** `company_AAABlLQjCsYYoXP4rsZKpY0y`.
- The platform's 3-step chain, stated independently by all three tools:
  **`create_listing` → `create_role(listing_id=...)` → `create_milestone(role_id=...)`.** Do not
  reorder, do not skip.

### The live shape (Cadre "HR Administrative Specialist" `list_AAABn6uMUYyPrNM3gPhHkK9u`, read 2026-07-29 PT)

| Field | Value | Note |
|---|---|---|
| `commitment` | `hourly` | NOT the `full-time` default |
| `rateMin` / `rateMax` | 50 / 60 | matches the role's payable 60 |
| `hoursPerWeek` | null | Sparta finance listings use 15; ask, do not assume |
| `location` / `workArrangement` | `Remote` / `remote` | |
| `eligibleLocation` | `["USA"]` | ISO 3166-1 alpha-3 |
| `status` on creation | `active` | there is no draft |
| `automaticRejectionsOn` / `timeToAutoReject` | true / 604800 | API default, 7 days |
| application steps | `resume` pos 1, `work-authorization` pos 2, both required | the API's default pair |
| custom steps | none | |

## Procedure

**1. Inventory.** `list_listings(company_id=Sparta, sort_by=created_at)` and scan for this
vertical or role. It pages: the response carries `next_offset` and `total_items`, and Sparta has
hundreds, so page until you have actually looked rather than judging off the first screen.

**2. Read the source and diff it out loud.**
```
get_listing(listing_id=<source>)
get_listing_application_steps(listing_id=<source>)
get_listing_custom_steps(listing_id=<source>)
```
Show the operator the source description and name every change: role overview, the sub-domain
bullet list, credentials, ideal backgrounds, the "not looking for" caveat, and any sentence
naming the source vertical's domain. **Every occurrence of the old domain has to go.** Get the
adapted description approved as text before any write.

**3. Assemble and validate.** Build the argument set from the intake, then:
```
validate_listing_description(description=<adapted>, title=<title>)
```
Returns `isValid` plus an `issues` list of excerpts that collide with standardized Mercor
candidate copy about referrals, contracts or payment. While `isValid` is false, revise the
flagged excerpts and run it again.

**Reconcile the band with the role before writing:** the role's `expected_payable_hourly` should
sit inside `[rate_min, rate_max]`. Cadre's does (payable 60, band 50-60). If they disagree, one
of the two is wrong and it is worth ten seconds to ask which.

**4. Create it. This publishes.**
```
create_listing(
  company_id = Sparta,
  title = <confirmed>,
  description = <adapted, validated>,
  rate_min = <n>, rate_max = <n>,
  commitment = "hourly",               # PIN THIS. default is full-time
  hours_per_week = <n or omit>,
  work_arrangement = "remote",
  location = "Remote",
  eligible_location = ["USA"],         # or the agreed list, alpha-3
)
```
Then `get_listing(new_id)` and confirm every field landed. Anything that did not can be patched
with `edit_listing` (it accepts title, description, rate_min/max, commitment, hours_per_week,
location, work_arrangement, eligible/ineligible_location, owner_ids and status).

**Alternative path, `duplicate_listing`.** Right for a near-identical sibling role in the SAME
vertical, e.g. Abacus adding a ninth accounting profile. `duplicate_listing(listing_id,
new_title=...)` copies title, steps and evaluation criteria, and **keeps the source's status**,
so duplicating an active listing gives you a second live listing immediately. Its documented copy
set does not mention description, band, commitment or eligibility, so whether those carry is
UNVERIFIED: read the duplicate back with `get_listing` and patch whatever is wrong with
`edit_listing`. For a different vertical, prefer the explicit create above, where every field is
one you passed.

**5. Application steps.** The API seeds `resume` + `work-authorization`. Match the source's
pipeline from step 2, only changing what the operator asked for:
```
get_listing_application_steps(listing_id)                       # always look first
manage_application_steps(listing_id, action="add", type="form", config_id=<form id>, position=3)
```
Valid types: `resume`, `interview`, `form`, `cognitive`, `work-authorization`, `availability`,
`additional-information`, `id-verification`. `is_required` defaults true. A `form`, `interview`
or `cognitive` step needs a real `config_id`, so the form or interview must exist first.

**6. Custom pipeline steps** (the recruiter-facing columns between "Applying Started" and "Ready
to Hire", e.g. "Review Candidates"). Cadre has none. Add only if the source had them or the
operator runs a review stage: `get_listing_custom_steps` first for ids and ordering, then
`manage_custom_steps`.

**7. Evaluation criteria.** Read the current rubric first, then save the FULL list back:
`update_eval_criteria(listing_id, criteria_list=[{criteria, hardFilter, status, evaluationCriteriaId?}])`.
Omitting `evaluationCriteriaId` creates a criterion; `status="archived"` soft-deletes one. Passing
a partial list is how criteria get lost. Mark a criterion `hardFilter` only when the operator
means it to auto-reject.

**8. The two candidate-facing fields no write tool can set.** `referralAmount` and the rejection
template (subject + body) both appear on the `get_listing` record and NEITHER is a parameter on
`create_listing` or `edit_listing` (both schemas re-checked 2026-07-29). `offerExtendedText` is on
the record too but is deliberately NOT in scope: that email is shared platform-wide and is null on
every Sparta listing, Abacus's flagship included.
So this skill cannot write them, and must not silently skip them either. Collect all three in the
intake, then hand them back as a named manual UI step on the listing page, quoting the exact values
the operator confirmed. Say in the handback that until someone does it:

- referral pays nothing, so nobody refers,
- the listing auto-rejects candidates at 7 days using the platform default copy, because
  `automaticRejectionsOn` defaults true and `timeToAutoReject` to 604800.

**Live proof this is not theoretical:** Cadre's flagship `Human Resources Expert`
`list_AAABn6aBpdG_oTdx-CFL6a7r` has `rejectionTemplateSubject`/`Body` null with auto-reject ON,
`hoursPerWeek` null (which is the norm, not a defect), while its sibling `list_AAABn6uMUYyPrNM3gPhHkK9u`
does carry a correctly-titled rejection template. Same vertical, same week, one has it and one does
not, which is exactly what an unasked field looks like.

**9. Hand the `list_` id to `create-vertical-teams-project` step 3**, which creates the role with
`listing_id` set. Then the milestone. Verify afterwards with `list_project_roles(project_id)`:
every expert role should show a non-null `listing_id`.

## Verify

```
get_listing(listing_id)                        # band, commitment, eligibility, status
get_listing_application_steps(listing_id)      # ordered pipeline
list_project_roles(project_id)                 # the role points at this listing
```
Report the listing id, its public title, the band, the source it was copied from, and the role it
is linked to.

## Unverified, do not state as fact

- **`isPrivate` and `disableApplications` are real fields that neither `create_listing` nor
  `edit_listing` can set.** Both schemas were checked. Sparta runs a private-twin pattern, e.g.
  `Government & Public Policy Expert — Sourcing Funnel (Private)` `list_AAABn6uRcb4s2pOom5RHPpLV`
  with `isPrivate: true`, `disableApplications: true` and 9,667 candidates alongside the public
  listing. So a private funnel is UI work; do not promise it through the API.
- **`referralAmount`**, the **rejection template** and **`offerExtendedText`** are not parameters on
  either write tool. That much is verified (both schemas, 2026-07-29) and is handled by step 8. What
  remains unverified is HOW they get set: presumably the listing UI, but nobody has watched it
  happen. Same for **`taxonomy` domain/subdomain**.
- **Why the referral figures differ is unknown.** Cadre alone runs 360 on its Expert listing and 240
  on its Specialist listing. Two roles, one vertical, one week apart, different amounts. Ask, never
  pattern-match.

## Gotchas

- **There is no draft.** Creating is publishing. `status` only accepts `active` or `archived`, so
  archiving is a retraction, not a hold.
- **`list_listings` returns compact rows** with `steps: []` and no templates, which does not mean
  the listing has no steps. Use `get_listing` plus `get_listing_application_steps`.
- **The marketplace `sourcing-request` skill is a different job.** It builds the Slack post to
  `#sourcing-requests` (`C09FHRX3JEQ`) asking a sourcing DRI for experts, and its field 10 is the
  listing link. This skill produces that link. They hand off to each other; neither replaces the
  other.

## Hand off

1. `create-vertical-teams-project` step 3, to create the role against this listing.
2. The marketplace `sourcing-request` skill once the listing exists and sourcing needs to start.
3. `verify-vertical-spinup` area A.
