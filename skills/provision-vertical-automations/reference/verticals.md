# Sparta vertical identifiers and live automation coverage

Two rules before you use anything here:

1. **Resolve tag ids at run time from `list_project_audiences(<project>)` anchors.** This file
   deliberately does NOT carry a full per-vertical tag table. Tag ids drift, several were
   repointed on 2026-07-28, and a stale table in a skill file is exactly how the shared-tag
   collisions happened. Only ids verified live in this session are recorded below.
2. **Never match a tag by name.** Abacus, Atria and Rampart each have genuinely distinct tags
   named bare `Active Writer`, `Onboarding` and `Reviewer`. Judge ownership by whether the id
   anchors THIS project's audiences.

## Projects

Company for all of them: Sparta `company_AAABlLQjCsYYoXP4rsZKpY0y`.

| Vertical | Domain | Project id | Role title |
|---|---|---|---|
| Panacea | Consulting | `proj_AAABmxRzIP9-VSjmz0tL_r3W` | (multiple) |
| Abacus | Accounting | `proj_AAABn0Um0Wr19Gj_ql9JHKSh` | `Accounting Expert`, `General Accountant` |
| Atria | Admin Healthcare | `proj_AAABn3FoIuB1-06gfllLl4Nq` | `Healthcare Admin Expert` |
| Rampart | Insurance | `proj_AAABn4DXkl4vJRwM1aBAzZi7` | `Insurance Expert` (no EPM role) |
| Cadre | HR | `proj_AAABn6Z-4irb63tDd_NNRr5G` | `Human Resources Expert` |

Studio: campaign Cadre `camp_35e49895edea4ad7b822d8347dab6c4c`, Abacus
`camp_930d4d8b84d2436497b2f3fcf79d483c`, Atria `camp_b0b8421ce5b745f794fb57d9c7560d8a`,
Rampart `camp_596be6524ff340dba995563562d4ec41`. Shared Studio company / account
`comp_2fa4115109d741cd94a3c409ed89e61f` / `acct_be8f7fcc2c554b33baa5a0c9d05496e3`.

WB golden worlds: Cadre `world_f68670e0b59d4a13b4658a3e1ed2a6ee`, Abacus
`world_044eeb974bad4155ac91d6f28f613133`, Atria `world_a50c1c4b8056465da650480e9fa7f7c3`,
Rampart `world_83dcee872482470b84943a7cd8c49bb3`.

## Cadre tag ids, verified live 2026-07-29

Cadre is the reference vertical: dedicated prefixed tags throughout. Use it as the shape, not
as a source of ids for anyone else.

| Tag | Id |
|---|---|
| Cadre Onboarding | `tags_AAABn6mAB_bxog3d-LlMMKqF` |
| Cadre Active Writer | `tags_AAABn6mAC-UIM3rhyoJO24SB` |
| Cadre Pod A | `tags_AAABn6mAIJq2LF1RIadN25yR` |
| cadre_completed_work_trial | `tags_AAABn6mAHCODg46TUR1A9ZD0` |
| Cadre World Builder | `tags_AAABn6mAGAhaUxkMN-VOHrVy` |
| Cadre Task Writer | `tags_AAABn6mAE1CGbLMn23NPuosU` |
| Cadre Reviewer | `tags_AAABn6mAEBmEoU3XhDlJDZnf` |
| Cadre EPM | `tags_AAABn6mAATXzJa4p4w1D1IKy` |
| Cadre Studio Admin | `tags_AAABn6mALHLEk_rotq5Lwa39` |

## Tags known to be shared across verticals, treat as contaminated

| Tag id | Shared by | State |
|---|---|---|
| `tags_AAABnYiHKEtdOhtigt1IUIft` (Active Writer) | Panacea `auto_AAABnxERowtHlA-dXFRJTIzf`, Rampart `auto_AAABn40grBa_GSbm8pJNgIuV` | **both ACTIVE.** Left alone per Ryu 2026-07-28. No audience anchors it in either project, so no access is mis-granted today, but reporting is contaminated and anchoring an audience on it later turns this into an access bug instantly |
| `tags_AAABnZflw34wRQLVfGVEa7yt` (Onboarding) | Panacea, Rampart | same automation as above |
| `tags_AAABn05fDkO2qNlPVB5HDoFI` (completed_work_trial) | originally Abacus, Atria, Rampart | Atria and Rampart were repointed to their own on 2026-07-28. Abacus's use of it is legitimate, it is Abacus's own id |

Never introduce a new vertical to any of these.

## Live automation state, read 2026-07-29

| Vertical | Total | Active | Notes |
|---|---|---|---|
| Panacea | 50 | 36 | mature, out of scope for this skill |
| Vigil | 50 | 24 | mature, out of scope |
| Abacus | 7 | 1 | active = contract-active tag grant |
| Atria | 11 | 2 | canonical 7 plus 4 out-of-scope comms automations. Active = contract-active tag grant + Pod A |
| Rampart | 7 | 1 | active = contract-active tag grant, and it grants the SHARED tags |
| Cadre | 7 | 1 | active = contract-active tag grant |

**No active bonus or payout automation exists on any Sparta vertical.** There are no live money
paths today. Confirm that is still true before activating anything in the Comp tier.

## Bonus self-ID guard status, audited 2026-07-29

| Vertical | Bonus automation | Guard 2 |
|---|---|---|
| Abacus | `auto_AAABn2MyfUVjGwE2gp5Hvob6` | correct, self-referencing |
| Cadre | `auto_AAABn6tXcR9LSaiyxntOxrQH` | **BROKEN**, names Abacus's id, so it is inert |
| Atria | `auto_AAABn4fZUywNtmIIlm9FD6PI` | **absent**, notes say never installed |
| Rampart | `auto_AAABn40jP2qeKZOWQsJBqJRr` | **absent**, notes say never installed |

All four are drafts, and guard 1 (reason text) still blocks a repeat, so nothing is paying
twice today. Fix all three before any of them is activated.

## Atria onboarding email sources (OUT of the canonical set)

Not part of the vertical launch set (Ryu, 2026-07-29). Listed only so that a vertical is not
wrongly reported as missing them, and so they can be cloned if someone explicitly asks. They
were cloned from Sanctum's active set and stripped per Kaushik Sarkar (TPM/DRI): no bonus-tier
section, no onboarding call times or Meet links, no hour-cap mechanics.

| Email | Atria id | Sanctum source |
|---|---|---|
| 24hr Welcome | `auto_AAABn6k8DDekDwGiunBDJaOZ` | `auto_AAABnmixPldO4nGDZD9PpZS5` |
| 72hr Check-In | `auto_AAABn6k8REecqu3Nar5K9Lba` | `auto_AAABnmixXX3YOHmOxO1N85XM` |
| 168hr One-Week | `auto_AAABn6k8hFsFRTnVZ0BIuZ_g` | `auto_AAABnmixdqUUTv5ykCFB36A4` |

Atria also has `auto_AAABn6lDE17_FN9GckpMxaG_`, a stalled-task reminder for world-building
tasks sitting in Plan or Spec Drafting past 48 hours. Not part of the canonical set, but a good
candidate for promotion into it once its copy has been reviewed.
