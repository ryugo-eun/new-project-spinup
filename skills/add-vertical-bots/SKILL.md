---
name: add-vertical-bots
description: Add the Studio Doctor bot (/doc + automation crons) AND the World File Upload bot to a new Sparta vertical, end to end. Interactive and human-in-the-loop - gathers the vertical's IDs, wires both repos (code only, committed + pushed), writes both Slack app manifests in the chat with the naming conventions baked in, PAUSES while the human adds Vercel/GitHub secrets and creates the Slack apps, then checks the deploys (redeploy-after-env for the doctor bot; the GitHub Action for the upload bot). Use during a new-vertical spinup, or when someone says "add the doctor bot to <vertical>", "add the world file upload bot to <vertical>", "wire the bots for the new vertical", "set up Studio Doctor for <vertical>".
---

# Add the Doctor + World File Upload bots to a new Sparta vertical

Two bots, both multi-tenant off one shared deployment each. Adding a vertical is code + Slack-app + env, in that order. This skill does the code, hands you the manifests, and pauses on the human-only steps (Slack apps, Vercel/GitHub secrets), then verifies the deploys. It was distilled from the Abacus/Atria/Rampart/Cadre rollouts; the two repos' own `CLAUDE.md` files are canonical if anything here drifts.

- **Doctor bot** — repo `ryugo-eun/panacea-cli-slack`, local `~/Desktop/MERCOR/doctor-bot`, one shared Vercel deploy `panacea-cli-slack.vercel.app` (project `prj_MEVMVf5bbzvN5udKlHYxhpYS4KqC`, team `team_JkY6AoDXM6vNYKG0nX4zdWPM`). Push `origin master`.
- **Upload bot** — repo `ryugo-eun/panacea-world-upload-bot`, local `~/Desktop/MERCOR/panacea-world-upload-bot`, shared Vercel receiver `panacea-world-upload-bot-zeta.vercel.app` + a GitHub Action worker. Push `origin main`.

Every commit is authored `Ryu Go-eun <ryugo-eun@mercor.com>` (Vercel blocks other authors). Both repos usually carry unrelated in-flight working-tree changes — **stage only this skill's files**, never `git add -A`.

## HARD RULES

- **Naming conventions (verify before publishing any manifest):**
  - Upload bot: app name AND bot-user display name = **`<Vertical> World File Upload Bot`** (e.g. `Rampart World File Upload Bot`).
  - Doctor bot: app name = **`Studio Doctor (<Vertical>)`**, bot-user handle = **`<vertical>-doctor`** (e.g. app `Studio Doctor (Rampart)`, bot `rampart-doctor`).
  - Channels: `#<vertical>-doctor-bot`, `#<vertical>-world-file-upload-bot`.
- **Never paste a secret value in chat or in a Bash command.** Name the env var and where to copy it from. Secrets are set by the human (or via `gh secret set NAME` with a hidden prompt they run themselves).
- **Vercel bakes env at build time.** Any env change needs a REDEPLOY or it does nothing. The doctor bot's `/doc` returning "app did not respond" after you set its signing secret is almost always a missing redeploy.
- **Pause and wait** at every step marked ⏸ — you cannot set Vercel/GitHub secrets or create Slack apps yourself. Ask the human to do it, then continue only once they confirm.
- **PASTE BOTH MANIFESTS AS FULL CODE BLOCKS IN THE CHAT REPLY.** Saving them to `docs/` is necessary but NOT sufficient, and a file path is not a deliverable. The human's next action is copy-paste into Slack's "From a manifest" box, so the complete, filled-in text has to be in the reply they are already reading. Naming a file and telling them to open it is a failure of this step (it happened on Cadre).

## Step 0 — Gather inputs (ask the human)

Ask for, and confirm, all of these before touching code:

| Need | Example | Used for |
|------|---------|----------|
| Vertical name + short key | `Rampart` / `rampart` | naming, registry keys, env suffixes |
| Human label | `Rampart (Insurance)` | `CAMPAIGN_LABELS`, roster |
| Studio campaign id | `camp_596be65…` | both bots' campaign registry |
| Golden WB world id | `world_83dcee87…` | upload bot `PROTECTED_WORLD_IDS` (do not trust notes, read it live — Step 3) |
| Tasking world id | `world_84be26de…` | lineage verification (below) |
| Slack workspace | Insurance grid workspace | where the two apps get created |
| Doctor channel id | `C0BK9K03WAG` (if it exists yet) | `/doc channel set` later |
| Upload channel id | `C0BJZLLSZ1R` (if it exists yet) | upload-bot `adminChannel` |

**Look up the channel ids before asking.** If the vertical's canvases were already built, `~/.claude/skills/editing-channel-canvases/reference/canvas-registry.md` carries a per-vertical channel-id table (including `#<vertical>-doctor-bot` and `#<vertical>-world-file-upload-bot`) — grep it first. It saved a round trip on Cadre.

The shared Sparta Studio company `comp_2fa4115109d741cd94a3c409ed89e61f` + account `acct_be8f7fcc2c554b33baa5a0c9d05496e3` are the same for every vertical; only the campaign id differs. If channel ids don't exist yet, proceed - the upload bot can DM an admin id instead, and the doctor ops channel is set later with `/doc channel set`.

## Step 1 — Verify the clone lineage (so the sweep set is honest)

The doctor crons fire shared remix/status ids that only exist on a verbatim Studio clone. Confirm the tasking world carries them before claiming the sweep set, via the `studio` MCP tool (`GET /worlds/<tasking_world_id>` with the campaign/company/account headers), then grep the result for each id:

- remixes: `a5cef9a0` (faga), `397f4a07` (pref), `4e2078da` (external-QA); pairwise module `efeeb9d8`
- statuses: `661a23e6` (FA), `9bc7a08c` (pref labels), `ad72f317` (FA AutoQC review), `75a801ec` (PL AutoQC review), `ba9f81f7` (RFD)
- also check `SER Heal` (remix `45eb4adf`): present → `/doc heal` and the advance sweep's `heal` verdict can refill a short run; absent (Rampart) → both hand back to a person instead, which is correct, not a bug. Never carry Rampart's "lacks SER Heal" comment onto a vertical that has it.
- `a5cef9a0` and `397f4a07` are no longer fired by any sweep (see the sweep list below), but they ARE fired by the world's four `Auto-sync on ready for delivery` hooks, which is what guarantees nothing ships unsynced. Still check them; the reason is the hooks, not the crons.

`GET /worlds/<id>` returns ~500k chars, so the MCP tool spills it to a file. Grep that file for the ids rather than trying to read it.

All present → it's the Abacus/Atria/Rampart/Cadre lineage; the standard sweep set applies. If some are missing, STOP and flag it - the vertical may be a different lineage and the sweeps need review. Also confirm `RLS_API_KEY` is scoped to the new campaign (a Studio call 403ing "not scoped to the requested campaign" means the shared key predates this vertical - re-mint scoped to ALL campaigns).

## Step 2 — Wire the Doctor bot (code)

In `~/Desktop/MERCOR/doctor-bot`, mirror the most recent vertical (diff `git show` for the last `feat(<vertical>): wire … multi-campaign bot` commit as the template):

1. `lib/doctor/config.ts` — add `<key>: "<camp_id>"` to `CAMPAIGNS` and `<key>: "<Label>"` to `CAMPAIGN_LABELS`.
2. `lib/panacea/cron-campaigns.ts` — add `<KEY>_CRONS` (**the three live sweeps: `unclaim-reviews`, `advance`, `nudge-writer-to-hand-off`**), extend `ALL_CRONS`, add the `CRON_CAMPAIGNS.<key>` entry (`botTokenEnv: "SLACK_BOT_TOKEN_<KEY>"`, `digestTitle`), and add `<key>` to the prefix-strip regex in **`baseActionOf`** (which is what `labelFor` and `describeCron` call). `api/slack.ts` strips the prefix generically (`/^[a-z]+-/`) and needs no edit.
3. `lib/panacea/cron-campaigns.test.ts` — extend the union-length, `cronCampaignOf`, `CRON_CAMPAIGNS`, `labelFor`, and full-set assertions.
4. `lib/slackApps.ts` — add `{ key: "<key>", suffix: "_<KEY>", defaultCampaign: "<key>" }` to `APP_DEFS`.
5. `api/cron-<key>-*.ts` — **4** endpoint files (the 3 sweeps + `digest`). Fastest: `for f in advance digest nudge-writer-to-hand-off unclaim-reviews; do sed 's/rampart/<key>/g; s/Rampart/<Vertical>/g; s/RAMPART/<KEY>/g' cron-rampart-$f.ts > cron-<key>-$f.ts; done` (the uppercase arm catches the digest file's `SLACK_BOT_TOKEN_RAMPART` comment). The filename MUST equal the registered cron name in `makeCronHandler(...)` and the `vercel.json` path, or the cron 404s in silence.
6. `vercel.json` — add 4 cron schedules, on the **fixed offset convention**, NOT by hunting for free minutes:

   > **Sweeps at :00, :15, :30 and the digest at :50, plus 2 minutes per vertical in join order.**

   | | unclaim-reviews | advance | nudge-writer-to-hand-off | digest |
   |---|---|---|---|---|
   | Panacea +0 | :00 | :15 | :30 | :50 |
   | Abacus +2 | :02 | :17 | :32 | :52 |
   | Atria +4 | :04 | :19 | :34 | :54 |
   | Rampart +6 | :06 | :21 | :36 | :56 |
   | Cadre +8 | :08 | :23 | :38 | :58 |

   A new vertical takes the next free offset (+10, then +12, …). Three things this protects, all of which the old "pick any unused minute" rule got wrong by accident:
   - **The digest must run LAST for its own vertical**, or it reports an empty hour. It reads `cron:lastrun:*`, which the sweeps write. The +N offset preserves that ordering automatically; a hand-picked minute does not (Panacea's `heal-grade` sat at :50 against a :45 digest for a week, so its result always landed an hour late).
   - **All five verticals share ONE Studio key**, and `/tasks/bulk-transition` rate-limits at ~5 requests/min. Same-minute sweeps across every vertical sit right at that ceiling. The 2-minute wave keeps each sweep type close together for readability without stacking them.
   - **`advance` is the heavy one** (live grading-platform reads plus a grading plan per task, capped at 50), so it never shares a minute with another vertical's `advance`.

   Verify with a script that walks `vercel.json` and confirms (a) every cron path has a matching `api/*.ts` file, (b) every endpoint is scheduled, and (c) each endpoint's registered `makeCronHandler` name equals its filename. A path/file mismatch fails silently — the cron just never runs.

Verify: `node --test --experimental-strip-types lib/panacea/cron-campaigns.test.ts` and `npx tsc --noEmit` (ignore any pre-existing errors in untracked `scripts/*` probe files - they aren't yours). Then commit **only these files** (`git add` them explicitly) with a `feat(<key>): wire the <Vertical> vertical into the multi-campaign bot` message noting the crons ship OFF, and `git push origin master`.

All crons ship OFF (Redis switch, off by default). Nothing fires until each is enabled BY EXACT NAME — **`/doc cron enable` takes one full cron id and rejects anything not in `ALL_CRONS`; there is no wildcard.** So it is three commands: `/doc cron enable <key>-unclaim-reviews`, `<key>-advance`, `<key>-nudge-writer-to-hand-off`.

## Step 3 — Wire the Upload bot (code)

In `~/Desktop/MERCOR/panacea-world-upload-bot` (template = the last `feat(<vertical>): add the … tenant` commit):

1. `scripts/constants.ts` — add `<key>: "<camp_id>"` to `CAMPAIGN_IDS`, then add **the vertical's Golden World Building world** to `PROTECTED_WORLD_IDS` (one commented line: `// <Vertical> (camp_…) [LIVE] Golden World Building`). **This is a required step on every new upload-bot install, not an optional hardening pass.** A mis-pasted WB task link resolves to that scaffold, and the upload is a FULL REPLACE, so an unprotected scaffold is one paste away from being clobbered for every writer in the vertical.

   Scope is **that one world per vertical**, not every golden-named world in the campaign. A golden tasking / reference / consensus world is a legitimate upload target; listing it would block real work.

   **Read the id live, never from notes or another vertical's list:**

   ```bash
   set -a; . ~/Desktop/MERCOR/.env.local; set +a   # RLS_API_KEY, never echoed
   CAMP=<camp_id>
   curl -s "https://api.studio.mercor.com/worlds/?campaign_id=$CAMP" \
     -H "Authorization: Bearer $RLS_API_KEY" -H "X-Campaign-Id: $CAMP" \
     -H "X-Company-Id: comp_2fa4115109d741cd94a3c409ed89e61f" \
     -H "X-Account-Id: acct_be8f7fcc2c554b33baa5a0c9d05496e3" \
   | jq -r '(if type=="array" then . else (.worlds // []) end)
            | "total=\(length)", (.[]
            | select((.world_name|ascii_downcase)
              | test("golden|world building|world creation and planning|scaffold|template"))
            | [.world_id, .world_name] | @tsv)'
   ```

   Both headers are required (`X-Campaign-Id` missing → `{"detail":"X-Campaign-Id header required"}`, which `jq` renders as a silent `total=0`, so check the total is non-zero before believing an empty hit list). Take the `[LIVE] Golden World Building` hit (Sanctum's is named `[LIVE] World Creation and Planning`; Rampart's is `- Copy`). If the campaign has no WB world at all, STOP and ask — a vertical whose writers build worlds must have one, so an empty hit list means the wrong campaign id or an unwired clone. Leave the other golden worlds out.

2. **Then prove the guard actually fires for the new vertical** — this is the step whose absence caused the 2026-07-30 Abacus clobber. Run the guard over every live world in the campaign and read the output:

   ```bash
   cd ~/Desktop/MERCOR/panacea-world-upload-bot && npm test    # includes tests/worker/protected-world.test.ts
   ```

   then a live sweep using `checkProtectedWorld` + `extractSpecWorldIds` from `scripts/protected-world.ts` against the campaign's real world list and real `GET /campaigns/<camp_id>` config (see RUNBOOK §9 "Golden-world backstop"). The vertical's WB world must come back BLOCKED and no per-writer world may. `spec=(none)` in that output is acceptable (Rampart's real state) but means signal 3 is unavailable for the vertical, so the id and the name pattern are carrying it alone: double-check the id.

   The guard has three OR'd signals (id list, `PROTECTED_WORLD_NAME_RE` on the world name, and the campaign's `spec_world_id`), so a vertical is not defenceless if you miss the id. Do not treat that as licence to skip it: a WB world renamed off-pattern with no spec pointer is covered by nothing but the list.
3. `scripts/slack-worker.ts` — add the `CAMPAIGNS.<key>` row. **If the upload channel exists:** `adminIds: "", adminChannel: "<channel_id>"` (notices post to the channel, no DMs - the Atria/Rampart pattern). **If not yet:** `adminIds: process.env.<KEY>_ADMIN_SLACK_ID ?? ""` (DM an admin until the channel exists).
4. `api/slack/events.ts` — add the `<key>` tenant row (`<KEY>_SLACK_SIGNING_SECRET` / `_BOT_TOKEN` / `_INTAKE_CHANNEL_ID`). **Do NOT re-import shared constants here** - the Edge bundler breaks on it; keep values inline.
5. `.github/workflows/upload.yml` — pass `<KEY>_SLACK_BOT_TOKEN` (and `<KEY>_ADMIN_SLACK_ID` only if using DMs, not a channel).
6. `CLAUDE.md` — add the config-table row + a status entry (channel routing + remaining setup steps).

Verify: `npx tsc --noEmit` and `npm test` (expect the full suite green). Commit **only these files**, `git push origin main`.

## Step 4 — PASTE the manifests in the chat (with the names baked in)

**The deliverable of this step is two code blocks in your reply, not two files.** Save them to the repos' `docs/` as well (they belong in version control), but the human is about to paste them into Slack's "From a manifest" box, so the full text goes in the chat. Do not substitute a file path, a diff, or "the manifest is ready at …". Both manifests, complete, in the reply.

Fill in the vertical's real values and apply the naming conventions.

**Upload bot (JSON)** — save as `panacea-world-upload-bot/docs/<key>-slack-manifest.json`. Fill `name` + `bot_user.display_name` = `<Vertical> World File Upload Bot`. Scopes `commands`, `chat:write`, `files:read`, `channels:history`, `groups:history`; bot events `message.channels` + `message.groups` (covers public OR private channel); slash `/worldfilesupload`; all three Request URLs = `https://panacea-world-upload-bot-zeta.vercel.app/api/slack/events`.

**Doctor bot (YAML)** — save as `doctor-bot/docs/slack-app-manifest-<key>.yaml`. `display_information.name` = `Studio Doctor (<Vertical>)`; `bot_user.display_name` = `<vertical>-doctor`; slash `/doc`; scopes `commands`, `chat:write`, `chat:write.public`, `users:read`, `app_mentions:read`, `reactions:write`; event `app_mention`; all three Request URLs = `https://panacea-cli-slack.vercel.app/api/slack?x-vercel-protection-bypass=YOUR_BYPASS_SECRET`. Tell the human to replace `YOUR_BYPASS_SECRET` with the Vercel protection-bypass secret and to NOT append `&x-vercel-set-bypass-cookie=true`.

Copy the exact shapes from the two most recent per-vertical manifests in each repo's `docs/`.

Alongside each pasted block, state where its Signing Secret and Bot Token go (the exact env var names, per repo, Vercel vs GitHub Actions) and which channel to invite the bot to — so the human never has to scroll back to Step 5 to act on what they just pasted.

## Step 5 — ⏸ PAUSE: human creates the Slack apps + sets secrets

Hand the human this checklist and WAIT for confirmation of each before proceeding.

**Slack (both apps, in the vertical's workspace):** Create app → From manifest → paste the manifest → Install → invite each bot to its channel. For the doctor app, replace the bypass secret in the three Request URLs first.

**Vercel — doctor bot** (project `panacea-cli-slack`): set `SLACK_SIGNING_SECRET_<KEY>` (Basic Information → Signing Secret) and `SLACK_BOT_TOKEN_<KEY>` (OAuth & Permissions → Bot User OAuth Token, `xoxb-…`).

**Vercel — upload bot** (project `panacea-world-upload-bot`): set `<KEY>_SLACK_SIGNING_SECRET`, `<KEY>_SLACK_BOT_TOKEN`, `<KEY>_INTAKE_CHANNEL_ID`.

**GitHub Actions — upload bot** (repo Settings → Secrets and variables → Actions): add secret `<KEY>_SLACK_BOT_TOKEN` (same `xoxb-` token). They can run `gh secret set <KEY>_SLACK_BOT_TOKEN` from the repo and paste at the hidden prompt (keeps it out of chat). Add variable `<KEY>_ADMIN_SLACK_ID` ONLY if the worker row uses DMs (no `adminChannel`).

> **Do not try to copy the token from Vercel for the GitHub secret.** `vercel env pull` returns BLANK for these encrypted vars, so you'd set an empty secret (this bit us on Rampart). The human copies the real token from the Slack app.

## Step 6 — Redeploy + check the deploys

**Doctor bot — REDEPLOY (this is the step people forget):** env set in Step 5 postdates the last build, and Vercel bakes env at build, so the live build has no `SLACK_SIGNING_SECRET_<KEY>` and `/doc` from the new app fails signature verify → "app did not respond". Confirm it: `vercel env ls production | grep <KEY>` timestamps vs `vercel ls panacea-cli-slack` top deploy age - if the deploy is OLDER than the env, redeploy. Trigger with an empty commit (`git commit --allow-empty -m "chore(<key>): redeploy to bake <KEY> Slack env"` → `git push origin master`) and poll `vercel ls` until the new production deploy is **Ready**. Then have the human retry `/doc` from `#<vertical>-doctor-bot`.

- Crons: you do NOT need the new app to run them - from any existing Studio Doctor app, `/doc cron dry-run <key>-advance` then `/doc cron enable <key>-advance` (switches are global by cron name). **One exact id per command, no wildcard** — `<key>-*` replies "Unknown cron". But `SLACK_BOT_TOKEN_<KEY>` IS required for the digest to post into the channel.
- Ops channel is Redis, NOT an env var: in the workspace, run `/doc channel set` inside `#<vertical>-doctor-bot` (from the vertical's app so it scopes to `<key>`), and invite the bot. Only ACTIONS + the hourly digest post there; read-only diagnoses DM the invoker (by design).
- Members: **`/doc grant` is NOT a command** (folded into `access` 2026-07-28, and it is not in `RETIRED_ALIASES`, so typing it silently DMs usage text — the exact trap the registry gotcha below describes). Use **`/doc access`**, then pick `grant` in the modal. Membership is **GLOBAL**, not per-campaign: the Redis key is `member:<slackId>` with no campaign in it, so it does not matter which vertical's app you run it from, and one grant covers every vertical. (Contrast `/doc channel`, which IS per-campaign — see the deadlock gotcha below.)

**Upload bot — trigger a test + read the Action:** have the human drop a `world_<id>.zip` (filename must contain the target world id) in `#<vertical>-world-file-upload-bot`, or run `/worldfilesupload`. Then `gh run list --limit 3` and, on failure, `gh run view <id> --log-failed`. The classic first-run failure is an empty `<KEY>_SLACK_BOT_TOKEN:` in the Action env → `chat.postMessage ok=false error=not_authed` AND `push failed: not a zip` (the file download also needs that token for `files:read`) - both fixed by setting the GitHub Actions secret. Confirm a clean run posts the success notice to the channel.

## Step 7 — Naming + wiring checklist (confirm before calling it done)

- [ ] Upload app + bot user named `<Vertical> World File Upload Bot`
- [ ] Doctor app `Studio Doctor (<Vertical>)`, bot user `<vertical>-doctor`
- [ ] Both bots invited to `#<vertical>-doctor-bot` / `#<vertical>-world-file-upload-bot`
- [ ] Doctor: production deploy Ready and POSTDATES the env timestamps; `/doc` responds
- [ ] Doctor: ops channel set (`/doc channel`), `SLACK_BOT_TOKEN_<KEY>` set, crons dry-run clean
- [ ] Upload: a real `world_<id>.zip` uploads → replaces → syncs → channel notice; `RLS_API_KEY` scoped to the campaign
- [ ] Upload: the golden-world guard proven for THIS vertical — its Golden World Building world is in `PROTECTED_WORLD_IDS` and comes back BLOCKED in the live sweep (Step 3.2). An unproven guard is how Abacus's live scaffold got full-replaced on 2026-07-30.
- [ ] Both repos: only the vertical's files were committed (in-flight WIP left alone), pushed as `ryugo-eun@mercor.com`

## Gotchas (all seen for real)

- **"app did not respond"** on `/doc` = env not baked (redeploy) OR the Request URL is missing `?x-vercel-protection-bypass=<secret>` / has the bad `&x-vercel-set-bypass-cookie=true` (307 Slack won't follow).
- **"This command is not available in this channel"** = Enterprise-Grid app-channel restriction, not our code, and **NOT fixed by `/invite`**. Grid tracks "the bot user is a member" and "the app is allowed in this channel" separately; only the second gates slash-command dispatch. So "the bot is already in the channel" is not evidence against this diagnosis (Cadre 2026-07-28). Fix via channel name → **Integrations → Apps → Add an App**; if the app is already listed there and it still blocks, it is an org-admin app policy on that channel and needs an IT request (`it-help` skill).
  - **Confirm it's Slack-side before touching anything:** `npx vercel logs <prod-deploy-url> --json` and look for a `POST /api/slack`. If no request arrived, Slack blocked it pre-dispatch and there is nothing to fix in the code or env. That same log tail also shows the new vertical's crons logging `cron.disabled — skipping`, which is free proof the cron wiring deployed correctly.
  - **Scope it in one step:** run the command in a DIFFERENT channel of the same workspace. Works elsewhere → channel-level restriction. Fails workspace-wide → the app isn't installed there, or another vertical's Studio Doctor app already owns `/doc` in that workspace (check the app name in the autocomplete dropdown; one `/doc` per workspace is the invariant).
  - **Not a blocker for launch.** The digest posts via `chat.postMessage` with `SLACK_BOT_TOKEN_<KEY>`, which needs bot MEMBERSHIP only, not slash permission. And cron switches are global by cron name, so `/doc cron enable <key>-advance` works from any existing Studio Doctor app in any workspace (one exact id per command; no wildcard). Ship the crons; chase the channel permission separately.
- **The `/doc channel set` deadlock (Cadre 2026-07-28).** `set` uses the channel you invoke it FROM, but the channel you want is `#<vertical>-doctor-bot`, which is exactly where the restriction above blocks `/doc`. It can never succeed there. **Use the raw-id form from any channel where `/doc` does work: `/doc channel C0BL652SQQK`.** The parser accepts `<#C…>` or a bare `C…` id. Run it from the VERTICAL's app — the Redis key is scoped by `app.defaultCampaign`, so running it from the Panacea app would set Panacea's channel instead. Success logs `step:"opschannel", msg:"set"` with the campaign, so you can verify it landed in `vercel logs` instead of taking the user's word for it.
- **"Command X works but Y doesn't" is a registry question first, not a permissions one.** Only names in `lib/kernel/registry.ts` (plus `access` / `channel` / `audit-channel` / `cron`, the manage set in `lib/commands.ts`) are real. Anything else hits `if (!cmd) { replyDm(usage(name)); return; }`, which sits BEFORE the `authorize` call and so always "works" — it DMs the usage text with no auth and no Redis. On Cadre, `/doc list` (not a command) appearing to work while `/doc channel` did not was read as a permissions split; it was just the unknown-command fallback. Check the registry before theorising about tiers.
- **Zero log lines is a diagnostic signal, not an absence of one.** Several handler paths return 200 and log NOTHING: unknown command, denied manage command, and `/doc channel` with no argument. A denied *doctor* command DOES log `outcome:"denied"`, and a Redis/handler error DOES log. So an empty-message 200 in `vercel logs` narrows the cause to that specific short list — it does not mean the request failed.
- **Every reply is a DM, never in-channel** (ephemerals retired 2026-07-16). "The command did nothing" almost always means "the answer is in the DM with `<vertical>-doctor`". Ask the user to read that DM before diagnosing anything else; its text names the exact failure.
- **`vercel env pull` returns blank** for encrypted vars - never source a token from it for a GitHub secret.
- **Cron minutes are a convention, not a scavenger hunt** - use the +2-per-vertical offset table in Step 2.6. The old advice here was "pick any unused minute", which is how the schedule became five unrelated patterns and how one digest ended up firing before a sweep it was meant to report.
- **Stage explicitly.** Both repos carry unrelated WIP; `git add` only the files you changed. If a shared file (e.g. `render.ts`) also has WIP, stage just your hunk (`git diff <file> | awk '/^@@ /{h++; if(h>1) exit} {print}' | git apply --cached`).
- **Another session may be committing in the same repo.** On Cadre, `doctor-bot`'s HEAD moved and a stash appeared mid-task (a parallel session committing its own WIP). Re-read `git log -1` before committing, and never `git checkout`/`stash` to "clean up" a working tree you didn't dirty.
- **Prefix git with `GIT_CONFIG_NOSYSTEM=1`** in this workspace — a stale `/Volumes/Ryu` entry in the system config hangs every git call otherwise.
