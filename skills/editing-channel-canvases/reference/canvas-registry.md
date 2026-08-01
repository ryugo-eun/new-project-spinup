# Canvas registry

Slack workspaces (mercor-mcp `workspace` param): `Abacus`, `Project atria` (Atria), `Insurance` (Rampart), `Consulting professional envs` (Panacea), `Vigil`, `Sanctum`. All canvas URLs resolve under `https://mercor.enterprise.slack.com/docs/T057PBFBJUC/<canvas_id>`.

NOTE (2026-07-23): `slack_list-channels` returns `team_access_not_granted` for the project workspaces (confirmed on both `Project atria` and `Insurance`), and `slack_search_channels` only surfaces channels the caller is a member of. So channel IDs cannot be enumerated via the API; they must come from the user or the tables below. `slack_create_canvas` and read/update DO work against these workspaces even when list does not. Full-canvas replace via legacy `action=replace` (no section_id) is REJECTED (`missing_required_field:section_id`); replace a specific paragraph via the `sections` array instead, and source EVERY link/number in that paragraph in `evidence` (the write-judge blocks otherwise, even for links you left unchanged).

## Abacus canvases (the live template set)

| Channel | Channel ID | Canvas | Canvas ID |
|---|---|---|---|
| #abacus-announcements | C0BG55TJA2E | 📣 Abacus Announcements: Start Here | F0BHG96PG92 |
| #abacus-general | C0BGZF3KESC | 🧭 Welcome to Abacus | F0BHCLD64QJ |
| #abacus-epms | C0BG6D02DF1 | 📌 EPM Start Here | F0BHCLZ71B4 |
| #abacus-epms | C0BG6D02DF1 | EPM Roster | F0BH6BL3WR1 |
| #abacus-epms | C0BG6D02DF1 | Key Resources | F0BHGER40HW |
| #abacus-epms | C0BG6D02DF1 | Reimbursements and Bonus Forms | F0BGNB5T3NE (dupe F0BGNB7JXS6 should be deleted) |
| #abacus-onboarding | C0BGKPMB9EJ | ✅ Welcome to the Abacus Onboarding Channel! | F0BHEPDRJKB |
| #abacus-onboarding-support | C0BGFJQ7LDR | 🛟 Onboarding Support: Read Before Posting | F0BGXG772ET |
| #abacus-pod-a | C0BHG4917NU | 🚀 Pod A: Start Here | F0BHGJTE2UC |
| #abacus-pod-a | C0BHG4917NU | 🚀 Information Station | F0BGXJG4H5M |
| #abacus-reviewers | C0BGFKBNKSP | 🔍 Welcome, Abacus Reviewers! | F0BHEQX8W81 |
| #abacus-robot-advice | C0BGFH1AE1Z | 🤖 Meet Maven: How to Use This Channel | F0BHGMSRE2Y |
| #abacus-technical-issues | C0BG6D7EFNK | 🛠️ Technical Issues: How to Get Help | F0BHEU5FB25 |

Other Abacus channels: #abacus-doctor-bot C0BGX94EBB5, #abacus-world-file-upload-bot C0BGDE5A95 (canvases pending their bot deploys; clone Panacea /doc how-to F0BHZGR71PA and world-upload F0BCS3YEKMM), #abacus-help-desk-c08 C0BGZFGP2QY and #abacus-sprint-07-11 C0BGG37SNAD (no canvas by design).

## Atria canvases (Admin Healthcare vertical; workspace `Project atria`, created 2026-07-21)

Cloned from the Abacus set: Abacus→Atria, domain wording accounting→admin healthcare, channel mentions repointed, Google Form/Doc links placeholdered (`_link TBD_`), SVA dashboard repointed to `camp_b0b8421ce5b745f794fb57d9c7560d8a`, org-chart image + EPM roster reset to placeholders. Comp ($800/2h/15h) carried verbatim from Abacus (confirm for Atria).

| Channel | Channel ID | Canvas | Canvas ID |
|---|---|---|---|
| #atria-announcements | C0BJK8HNDQS | 📣 Atria Announcements: Start Here | F0BK0J67KC4 |
| #atria-general | C0BJ393FCMC | 🧭 Welcome to Atria | F0BJTJ8D961 |
| #atria-epms | C0BJJUV6D4J | 📌 EPM Start Here | F0BJFGMRUET |
| #atria-epms | C0BJJUV6D4J | EPM Roster | F0BKR7JULQG |
| #atria-epms | C0BJJUV6D4J | 🔗 Key Links | F0BKR7LJ4JC |
| #atria-epms | C0BJJUV6D4J | Reimbursements and Bonus Forms | F0BJQLCFGSF |
| #atria-onboarding | C0BJ3JQF3B9 | ✅ Welcome to the Atria Onboarding Channel! | F0BJWSXAUBU |
| #atria-onboarding-support | C0BJFLUT4MB | 🛟 Onboarding Support: Read Before Posting | F0BJYQLSCTT |
| #atria-pod-a | C0BJCN35HM1 | 🚀 Pod A: Start Here | F0BK0JYHJKW |
| #atria-pod-a | C0BJCN35HM1 | 🚀 Information Station | F0BJWTG3FC2 |
| #atria-reviewers | C0BJJVAMR26 | 🔍 Welcome, Atria Reviewers! | F0BJFGCUQ79 |
| #atria-robot-advice | C0BJFLZU2J1 | 🤖 Meet Maven: How to Use This Channel | F0BJYR545UH |
| #atria-technical-issues | C0BJ3JY338X | 🛠️ Technical Issues: How to Get Help | F0BK0K0FS4C |

Standalone canvases (API can't attach to a channel) — must be shared into each channel by hand. Bot-channel canvases (#atria-doctor-bot C0BJCMNQZ7D, #atria-world-file-upload-bot C0BJLTAL397) NOT cloned: no Abacus source, clone Panacea /doc how-to F0BHZGR71PA + world-upload F0BCS3YEKMM. Duplicate Atria channels exist (Shaswat's #atria-epm C0BJV76E9M0, #atria-reviewer C0BJRSZ278V) — canvases target Ryu's plural -epms/-reviewers to match the Abacus template.

## Rampart canvases (Insurance vertical; workspace `Insurance`, created 2026-07-23)

Cloned from the Abacus set: Abacus→Rampart, domain wording accounting→insurance, Instructions Hub → `/rampart`, SVA dashboard → `camp_596be6524ff340dba995563562d4ec41`, calendars → Rampart Writer/Onboarding (see Fixed assets), EPM roster reset to placeholders, org-chart + all Drive/form/EPM-training/reviewer-guide links placeholdered (`link TBD`), except Rampart top Drive folder `1WkWUayAXIOcFrpEZmCMHxrjwhMAHKfhu`. Office-hours TIMES carried verbatim from Abacus (welcome 9am/4pm PT; support+pod-a 9am/3pm PT) — CONFIRM for Rampart. All 13 are STANDALONE (owned by Ryu); user attaches each to its channel by hand.

Channel IDs (resolved 2026-07-23 via `slack_search_channels` query "rampart" with `channel_types=public_channel,private_channel` — most Rampart channels are PRIVATE, so a public-only search misses them): #rampart-announcements `C0BJP6HKS5A`, #rampart-general `C0BJKE9GA1Y`, #rampart-onboarding `C0BK3TZ7S8N`, #rampart-onboarding-support `C0BJZLHHUJF`, #rampart-pod-a `C0BK4AMU7K8`, #rampart-technical-issues `C0BJG6FKMV3`, #rampart-robot-advice `C0BK9JYK98C`, #rampart-epms `C0BK7R5TTMX`, #rampart-reviewers `C0BK7RGDZEV`, #rampart-doctor-bot `C0BK9K03WAG`, #rampart-world-file-upload-bot `C0BJZLLSZ1R`. All cross-channel references in the onboarding-welcome, onboarding-support, general, and Pod A canvases were CONVERTED from plain text to live `![](#C…)` mentions 2026-07-23. (Remaining canvases — announcements, EPM Start Here, Key Links, reviewers, robot-advice, Information Station — still carry plain-text refs if any; convert as needed.)

| Target channel | Canvas | Canvas ID |
|---|---|---|
| #rampart-announcements | 📣 Rampart Announcements: Start Here | F0BJV6MCGBZ |
| #rampart-general | 🧭 Welcome to Rampart | F0BK78FJH37 |
| #rampart-epms | 📌 EPM Start Here | F0BK4AU92KV |
| #rampart-epms | EPM Roster | F0BJV7BPTCP |
| #rampart-epms | 🔗 Key Links | F0BKCFU1TED |
| #rampart-epms | Reimbursements and Bonus Forms | F0BKAJ6DU74 |
| #rampart-onboarding | ✅ Welcome to the Rampart Onboarding Channel! | F0BK78XA7EZ |
| #rampart-onboarding-support | 🛟 Onboarding Support: Read Before Posting | F0BKAHJF4BU |
| #rampart-pod-a | 🚀 Pod A: Start Here | F0BKE8TMWSY |
| #rampart-pod-a | 🚀 Information Station | F0BJV70T287 |
| #rampart-reviewers | 🔍 Welcome, Rampart Reviewers! | F0BKCFG4L2D |
| #rampart-robot-advice | 🤖 Meet Maven: How to Use This Channel | F0BJV72KFK9 |
| #rampart-technical-issues | 🛠️ Technical Issues: How to Get Help | F0BK8HPDX0W |

## Cadre canvases (Human Resources vertical; workspace `Hr - sparta vertical`, created 2026-07-28)

Cloned from the Abacus set: Abacus→Cadre, domain accounting→Human Resources (Cadre's writer role = "Human Resources Expert" per get_project), channel mentions repointed to Cadre's IDs, SVA dashboard → `camp_35e49895edea4ad7b822d8347dab6c4c`, and every Cadre-specific link (instructions doc, Drive folders, forms, calendars, EPM training doc, automations sheet, expert tracker, office-hours times, org-chart image, EPM roster) left as an explicit TBD (Cadre's instructions doc + Drive folder don't exist yet). Insightful timer set to the convention "Sparta - Cadre - World" / "Taskwriting" (CONFIRM the exact Insightful project name). 15 canvases total = the 13 standard + two extras Ryu added on Cadre (Reviewer Roster in #cadre-reviewers, Weekly Availability); all STANDALONE (owned by Ryu), user attaches each to its channel by hand. NOTE: Reviewer Roster + Weekly Availability are NOT yet in the 13-canvas `create-vertical-canvases` default set — consider folding them in.

Cadre channel IDs (workspace URL `ff0e0e6a7578518.slack.com`; resolved via `slack_search_channels` query "cadre"): #cadre-announcement `C0BL42735QV` (public, all-members), #cadre-maven-support `C0BLEA2TNCR` (public), #cadre-epms `C0BM1LER10Q`, #cadre-pod-a `C0BL64S6ZAP`, #cadre-reviewers `C0BKX15BK55`, #cadre-onboarding `C0BLF04SU4R`, #cadre-doctor-bot `C0BL652SQQK`, #cadre-technical-issues `C0BM1LRQ42U`, #cadre-world-file-upload-bot `C0BM6NB5L56`.

**Cadre channel PROVENANCE (renames, 2026-07-28).** Three of Cadre's channels are renamed IT-Admin defaults, not fresh creations, which is why their topics/purposes read wrong and why some Teams audience target NAMES are stale: workspace **general -> #cadre-announcement** (singular; convention is PLURAL `-announcements`, so this one still needs renaming); **random -> #cadre-epms** (still carries the "Non-work banter and water cooler" topic/purpose); **help-desk -> #cadre-technical-issues** (`C0BM1LRQ42U`). Consequence to remember: the Cadre `Everyone` audience still has a target *named* `Cadre-help-desk` whose externalId resolves to `C0BM1LRQ42U`, i.e. #cadre-technical-issues. The routing is CORRECT; only the label is stale. Do not "fix" it as a misconfiguration. Same trap applies to any renamed channel: always resolve a target by its externalId channel id, never by its target name.

**There is NO Slack-channel skill and NO Slack-channel API.** Neither mercor-mcp (739 tools) nor the claude.ai Slack connector exposes channel create / rename / archive / set-topic. Only canvases, messages, search, read. Channel creation for every vertical has been, and remains, manual in the Slack UI. Skills stop at canvases (`create-vertical-canvases`) and calendars (`add-vertical-calendars`).

**Cadre channel-set differences vs Rampart:** Cadre has NO separate #cadre-general (the all-members channel is #cadre-announcement), NO separate #cadre-onboarding-support (both onboarding canvases live in #cadre-onboarding per Ryu), and the Maven channel is #cadre-maven-support (not "robot-advice"). Onboarding-welcome + onboarding-support routing was reworked so setup refs point to #cadre-onboarding and content refs to the pod channel.

| Target channel | Canvas | Canvas ID |
|---|---|---|
| #cadre-epms | 📌 Cadre EPM Start Here | F0BLF7J4HDX |
| #cadre-epms | Cadre EPM Roster | F0BL72F79PD |
| #cadre-epms | 🔗 Cadre Key Links | F0BM7KK5U6L |
| #cadre-epms | Cadre Reimbursements and Bonus Forms | F0BLF7MQVAM |
| #cadre-pod-a | 🚀 Cadre Pod A: Start Here | F0BM7KRS872 |
| #cadre-pod-a | 🚀 Cadre Information Station | F0BLD9ULH4J |
| #cadre-onboarding | ✅ Welcome to the Cadre Onboarding Channel! | F0BKXUTGB4P |
| #cadre-onboarding | 🛟 Cadre Onboarding Support: Read Before Posting | F0BLBAUREQN |
| #cadre-reviewers | 🔍 Welcome, Cadre Reviewers! | F0BLBAX73JS |
| #cadre-announcement | 📣 Cadre Announcements: Start Here | F0BL73JRC59 |
| #cadre-announcement (or a future #cadre-general) | 🧭 Welcome to Cadre | F0BL73JQG4T |
| #cadre-maven-support | 🤖 Cadre Maven Support: How to Use This Channel | F0BKXV9TAJ3 |
| #cadre-technical-issues | 🛠️ Cadre Technical Issues: How to Get Help | F0BLDAU8VPU |
| #cadre-reviewers | Cadre Reviewer Roster | F0BLCRCQQP8 |
| #cadre-epms + #cadre-reviewers | Cadre Weekly Availability | F0BLBGRBJJZ (day-of-week grid: intro "Weekdays 9-5 unless otherwise stated." + table EPM Name \| Sunday…Saturday + ~20 blank rows; matches the Abacus EPM availability canvas) |

Bot-channel canvases (#cadre-doctor-bot, #cadre-world-file-upload-bot) NOT created: clone Panacea /doc how-to F0BHZGR71PA + world-upload F0BCS3YEKMM once those bots point at Cadre. Every title carries "Cadre" (Ryu's rule, so it's obvious which canvas goes in which channel).

## Fixed assets and constraints

- Org chart image: Slack file `F0BHESJ76C9`, hosted via a message in #abacus-pod-a. Embedded by the Information Station canvas. Do not delete the hosting message.
- **REVERSED 2026-07-23 for Abacus + Atria + Rampart:** at the user's instruction, every instructions link in the Abacus canvases (7 canvases), Atria canvases (9 canvases), and Rampart canvases (9 canvases) was repointed FROM the Instructions Hub BACK to a per-vertical Google Doc. Abacus doc `1u-Go8CrHhzLwss4p1SqX9WiTNs3vJVmmG5bdKvBByws`; Atria doc `1iyyef-zgJcIu0vnwjvk9qVFsPaMoanRGmIlJ5KFs-SU`; Rampart doc `1WcKj4snqF4yHX1LdS1VWV6AOpsjGbseGUrBbRq_Mkcs` (URL uses `/mobilebasic`). Link label standardized to "<Vertical> Instructions" (dropped "Hub"). Rampart reversal touched 9 canvases (announcements, general, EPM Start Here, Key Links, onboarding welcome, onboarding support, Pod A Start Here, Information Station, reviewers); also de-"hub"-ed adjacent prose (onboarding-welcome step-1 heading → "Read the Instructions", "reading through the hub" → "the instructions"; Info Station "the hub's FAQ" → "the instructions doc's FAQ"; onboarding-support dropped the now-false "the Hub itself opens without sign-in" and folded the link into the @mercor.expert access guidance). The 7/21 note below is now historical for Abacus/Atria.
- **Source of truth = the Instructions Hub, not Google Docs (changed 2026-07-21).** Abacus hub `https://sparta-instructions-hub.vercel.app/abacus`, Atria hub `https://sparta-instructions-hub.vercel.app/atria`. The old Abacus onboarding doc (`1u-Go8...`) and instructions doc (`1x6WJoAT...`) are RETIRED; there is no longer a separate onboarding doc, and every canvas instructions/onboarding-doc LINK was repointed to the hub across all Abacus + Atria canvases on 2026-07-21 (Key Links onboarding-doc rows deleted; onboarding-welcome step-1 renamed "Read the Instructions Hub"). NOTE: a few generic PROSE mentions of "instructions doc" (reviewers "How we work"; Pod A "Project flow") were left as-is (not links).
- Abacus EPM Training doc: `1_UhqBfjjLZjKhTX0t1ZUHeiw-ngaf-DceGlBb60MD1A` (Abacus Drive folder `1tWBDFknQcg0n4zilASotpiXn1zxjJsCZ`)
- Abacus writer calendar: `https://calendar.google.com/calendar/u/0?cid=Y180ODZhODZjMWU0MWEzMzQ0ZGJjMTY4Y2RjZTAwOTcyNDc2ODNlOTZhN2Q0OTM2NTBiMzQzNTNkMDU5NmJiYzRkQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20` (office hours + syncs). Added 2026-07-21 to onboarding welcome, onboarding-support, general, Pod A Start Here, Information Station.
- Abacus onboarding calendar: `https://calendar.google.com/calendar/u/0?cid=Y19mNjEwOWJhNWFjNjk1ZTBhMTM0ODRjMzQ4ZTQ0OTk3Mjg0YmU4ZDFlMTY3YjU3ZjdlZGVjNTY1YTRhNzE3YmY4QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20` (onboarding sessions). Added 2026-07-21 to onboarding welcome, onboarding-support, general.
- Atria writer calendar: `https://calendar.google.com/calendar/u/0?cid=Y19mODFjZmI4OWNhMzgwN2IwM2ZiNmExMzFjMDRlYWUzMGY4NWU5YTQ2YzM4NjAyNmNmNTkyOTJhNjQwZTZmNjRhQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20` — decoded cid `c_f81cfb89ca3807b03fb6a131c04eae30f85e9a46c386026cf59292a640e6f64a`. Added 2026-07-21 to the same 5 Atria canvases as Abacus.
- Atria onboarding calendar: `https://calendar.google.com/calendar/u/0?cid=Y180NWZhZmVkZDk3YmY1MjlkYjRlNjI4YmRlMzg4MzlmNjY2ODg2MWRmZWNhNTM2NzFmNTZhYzk1NTAzZDFhZjk0QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20` — decoded cid `c_45fafedd97bf529db4e628bde38839f6668861dfeca53671f56ac95503d1af94`. Added 2026-07-21 to Atria onboarding welcome, onboarding-support, general. **CORRECTED 2026-07-23:** the value first written here + into all 3 canvases had a transcription typo (`...668821...`, a dead link); fixed to the real id `...668861...` from live Google Calendar in all 3 Atria canvases 2026-07-23.
- **ALL vertical calendar cids verified against live Google Calendar (`list_calendars`) 2026-07-23.** Rampart writer calendar: cid `Y18yMzg3OGEwYjA4ODQyNTFjZTZjM2M2MjEzZDk3Nzc1MmMwY2E3YWZkYWQ4YWE0YTBiYjYyNzk3MmQzNDA0Njc2QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20` (id `c_23878a0b0884251ce6c3c6213d977752c0ca7afdad8aa4a0bb627972d3404676`). Rampart onboarding calendar: cid `Y18xZTA0NzA4Y2E1OTM2MWQ1ODIyMTVhNzk2MDljMzAxYmEzNjU0NGQ4ZjlhMzUwM2RlZDJkNDlmNDE1ZWM3N2Y4QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20` (id `c_1e04708ca59361d582215a79609c301ba36544d8f9a3503ded2d49f415ec77f8`). Both baked into the Rampart canvases at creation. Abacus writer/onboarding + Atria writer cids all matched live (no change needed).
- **Cadre calendars CREATED + baked in 2026-07-28.** Cadre onboarding calendar cid `Y19iYWVjNTJlNjhhYjNlNjAwNGZjOTNmYWYyNGIyZDhiNWZiN2M5YmViZDEyZjY2ZThhNWViZTg0YzJkNDI5Nzk1QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20` (id `c_baec52e68ab3e6004fc93faf24b2d8b5fb7c9bebd12f66e8a5ebe84c2d429795`). Cadre writer calendar cid `Y18xZDE4MTFmZTQ3YTE2ZDU3N2I4NjlkZDA2OTgxZGU3MTg4YWM0YWY1NTE1NmFiOGRlM2M2ODI2NzQzMjg5MzNmQGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20` (id `c_1d1811fe47a16d577b869dd06981de7188ac4af55156ab8de3c682674328933f`). Both cids base64-decode-verified against the live calendar ids before writing (the 7/23 Atria dead-link typo is why). Filled into **6 Cadre canvases**: onboarding welcome F0BKXUTGB4P, onboarding support F0BLBAUREQN, Welcome to Cadre F0BL73JQG4T (all three carry BOTH calendars), Pod A Start Here F0BM7KRS872 + Information Station F0BLD9ULH4J (writer calendar only, inside their callouts), and **Key Links F0BM7KK5U6L (NEW: two link rows appended)**. Key Links is a Cadre-only addition — the Abacus/Atria/Rampart Key Links canvases still have NO calendar rows; consider backfilling them.
- **`edit_type: append` in the `sections` array REQUIRES `section_id`** (`missing_required_field:section_id` otherwise) even though appending to the canvas end conceptually needs no target. Anchor to the LAST element's section_id; content lands after it.
- **Cadre form links REWRITTEN to responder URLs 2026-08-01 ~9:40am PT.** All 7 form links across 6 canvases (Reimbursements & Bonus F0BLF7MQVAM, Key Links F0BM7KK5U6L, Pod A F0BM7KRS872, Onboarding Welcome F0BKXUTGB4P, Welcome to Cadre F0BL73JQG4T, Announcements F0BL73JRC59) had shipped in the file-id shape `/forms/d/<fileId>/viewform`, and Key Links had BOTH rows pointing at `/edit` (form editor, one behind viewform display text). Now `https://docs.google.com/forms/d/e/<responderId>/viewform?usp=sharing&ouid=114776486065354327206`: bonus `1FAIpQLSeF0XMwJLd3aL-Xsqmq80yAwvwSXAguFz71Z_nUgtNMueOnGg`, reimbursement `1FAIpQLSeaTEr7246aySpgqeEFH4Itbft8g6la_WCSnHRzdsrQoZ6iNQ`. Rule + trap live in `sweep-canvas-links` step 2 and `create-vertical-canvases` link backfill.
- **`slack_read_canvas` denormalizes live channel mentions `![](#C…)` back to `<#C…>` in its output.** Do NOT read that as "the mention is broken plain text." When rewriting a block that contains one, write it as `![](#C…)`; it round-trips correctly (verified on Cadre Pod A F0BM7KRS872 2026-07-28).
- SVA Abacus dashboard: `https://sva-pi.vercel.app/campaigns/camp_930d4d8b84d2436497b2f3fcf79d483c/` (pass: sparta-va)
- Onboarding facts come from the Abacus onboarding doc (NOT Panacea): no quiz; onboarding = video + doc + Plan Doc (Writer Input Template) + Spec Doc approved; single $800 payment at spec doc approval; 2h starting Insightful cap; 15 hr/wk minimum (30 preferred); domain office hours 9:00 AM + 3:00 PM PT daily plus 24/7 logistics OH (links still TBD); Insightful timers "Sparta - Abacus - World" and post-pod "Taskwriting"; justinbot answers in #abacus-technical-issues.

## Open TBD slots

Pod lead name(s) (Start Here, Information Station); office-hours/onboarding-call CALENDARS filled 2026-07-21 (writer + onboarding calendars on the 5 canvases above, both verticals); the recurring daily Google Meet links are still posted in-channel, not on the canvases; reviewer guide + interactive tutorial + recorded call (reviewers); reviewer syncs cadence/link/incentives (reviewers); Maven bot mention, pending Maven deploy to the Abacus workspace (robot-advice); help-request form + status tracker (technical-issues); EPM training tracker (EPM Training doc). (Automations sheet: filled by Ryu, `1w8G_WTl0A3FVIKe-dJEUVZ_stkNo-3_ECuOsSFkvo60`.)

## Reference canvases (source material for new drafts)

| Vertical (workspace) | Canvas | ID | Good for |
|---|---|---|---|
| Panacea (Consulting professional envs) | Active Experts, Read Me! | F0BAYNA2GJ3 | announcements / production orientation |
| Panacea | New Experts, Read me! | F0B9K683Q5S | onboarding welcome, comp structure |
| Panacea | 🚀 Information Station | F0BBHEU0DSS | pod resources callout |
| Panacea | Getting Tasks Through | F0BEUD2SWCX | operational how-to (QC flags, FA/GA/PL rules, review pushback); tabled for Abacus |
| Panacea | New reviewers, read me! | F0B9HC81JD7 | reviewer onboarding |
| Panacea | Reviewer Roster | F0B50FMAHGF | roster format |
| Panacea | Help instructions | F0BDN2ZMC8J | tech channel (Slack Workflow form + List tracker pattern) |
| Panacea | Hi, team! (Maven intro) | F0ABAAU7F40 | robot/Maven channel |
| Panacea | Key Resources | F0B661W53EZ | EPM link hub |
| Vigil | Welcome to the Vigil Onboarding Channel! | F0AU26DSMUN | onboarding structure (tools, process, contacts, timeline) |
| Vigil | Pod Resources | F0B76AVHMRB | channel norms, walkthrough-video library |
| Vigil | Resources (EPM) | F0B26N0GX53 | EPM trackers + roster |
| Vigil | EPM Roster | F0B5GR21AKV | roster with roles/timezones/coverage |
| Vigil | Offboarding Process | F0BAASC12H4 | offboarding runbook (adopt once Abacus has an offboard flow) |
| Vigil | Reviewer Resources | F0B327UQTQB | reviewer queue/tracking/incentives links |
| Sanctum | 🏥 Start Here | F0B5DB7DKU7 | pod canvas structure (soften the tone; its enforcement wording is deliberately not ported) |
| Sanctum | Reviewer Resources | F0BA031DZSA | pass/fail review checklist, sync recordings archive |
