---
name: setup-spinup-credentials
description: >-
  Step 0 of a Sparta new-vertical spinup: put working credentials on the operator's machine
  before any other spinup skill is run. Collects the one real secret (the Studio RLS API key)
  without it ever reaching the conversation transcript, proves it is live AND write-scoped
  against the real API instead of assuming, derives every non-secret id from the API rather
  than having anyone type it, and writes ~/.claude/credentials/spinup.env at 0600. Use when
  someone says "set up my credentials", "I'm starting a new vertical", "step 0", "where do I
  put my API key", "the spinup skills can't find my key", or when any spinup skill fails with
  401, 403 or "This API key has 'read' access".
metadata:
  author: ryugo-eun
  outbound_writes: false
---

# Step 0: credentials for a new-vertical spinup

Every other skill in this repo assumes credentials already exist and that they sit at a
path on Ryu's laptop. This is the step that makes that true for anyone else. Run it first,
run it once, then re-run it after the campaign exists.

**It writes one file: `~/.claude/credentials/spinup.env`, mode 0600.** Nothing else on the
machine is touched.

## What is actually needed, and what is not

| Thing | Needed? | Where it comes from |
|---|---|---|
| `RLS_API_KEY` (Studio) | **Yes, the only real secret** | Studio → your campaign → Settings → API. Must have **write** access |
| Campaign / company / account ids | Yes, not secret | **Derived from `GET /campaigns/`.** Nobody types them |
| Taiga | For the ops skills, not for steps 1-15 | A Google OAuth browser login, not a key you paste |
| **Teams API key** | **No** | Every Teams action goes through mercor-mcp, which authenticates through the operator's own MCP connection. Minting one creates a secret nothing reads |
| `VERCEL_PROTECTION_BYPASS` | Only at step 11 | The `add-vertical-bots` skill collects it when it needs it |

## Running it

```bash
cd ~/.claude/skills/setup-spinup-credentials

python3 setup_spinup_creds.py                      # first run: paste the key, validate, write
python3 setup_spinup_creds.py --campaign Westwood  # after step 4: pin the campaign's ids
python3 setup_spinup_creds.py --check              # validate what is there, write nothing
python3 setup_spinup_creds.py --list               # every campaign this key can reach
```

**The operator runs it themselves in a terminal.** The key is read with `getpass`, so it is
never echoed, never in shell history, never in `ps`, and never in the transcript. The script
refuses to run when stdin is not a tty rather than falling back to a visible prompt, and it
does not accept the key as a CLI argument for the same reason.

Never paste the key into chat, and never put it in a `Bash` command you hand to Claude: the
literal string lands in the transcript before the shell expands it. Keys have been rotated
over exactly this.

## Run it twice, on purpose

The RLS key is minted per campaign, and at the true start of a spinup the vertical's campaign
does not exist yet (it is cloned at runbook step 4). So:

- **Before step 4**, run it bare. It validates that the key authenticates and writes the file.
  If the operator has a broad Okta-forwarded key it will also confirm write scope against
  another campaign they can already reach. If it cannot, it says so rather than passing.
- **After step 4**, run `--campaign <VerticalName>`. That pins the three ids and re-runs the
  write probe against the vertical's own campaign, which is the one that matters.

A `WARN` that write scope could not be tested is expected on the first run. A `WARN` on the
second run is not: chase it.

## The read-only key trap, which is why the write probe exists

A read-scoped key passes every `GET`. It looks completely fine at step 0, and then fails at
step 4 or 5 on the first `PATCH` with a 403 that reads like a permissions problem with the
campaign rather than with the key. `restamp-taiga-env` documents hitting exactly this.

So the script proves write access rather than assuming it. Verified against a known read key
and a known write key on 2026-08-07 (PT):

| Key scope | `GET /worlds/{id}` | `PATCH /worlds/{id}` with body `{}` |
|---|---|---|
| write | 200 | **400** `At least one field must be provided for update` |
| read-only | 200 | **403** `This API key has 'read' access; this endpoint requires 'write'.` |

**The probe mutates nothing.** The API rejects an empty body before it touches the record;
the target world was byte-identical before and after (490,488 bytes, identical checksum). It
is the only safe write test found: a `PATCH` against a nonexistent world id returns 403
`not authorized for resource` for BOTH key types, so it cannot tell them apart.

## Other things it checks

- **`campaign_admin` role.** `port-vertical-dashboards` reads a **truncated** view set as a
  non-admin, and its write is a PUT that replaces the campaign's entire set, so porting as a
  non-admin silently deletes views. The script warns when the role is anything else.
- **File permissions.** Written 0600 before the file is visible at its final path, then
  re-read and reported.
- **Taiga token presence** at `~/.claude/credentials/taiga_oauth.json`.

## Taiga

Taiga is a Google OAuth login, not a pasted key. The working implementation already exists at
`~/.claude/skills/panacea-taiga-delivery-tagger/lib/connect.py`: it caches an `id_token` at
`~/.claude/credentials/taiga_oauth.json` (0600), refreshes automatically, and runs the browser
flow once when the refresh token is gone. Do not rewrite it.

To force a fresh login, delete that file and run any Taiga command; a browser opens once.

**Nothing in runbook steps 1 to 15 calls Taiga directly.** Step 5a-i is a manual read of the
Taiga UI, and the runs themselves are fired through Studio remixes using the RLS key. Taiga
credentials are for the day-to-day ops skills (`run-in-taiga`, `trigger-taiga-qc`,
`fetch-taiga-qc-result`, the Panacea resync/tagger skills).

## Gotchas this exists to prevent

- **Values must be quoted in the env file.** `set -a; . file; set +a` breaks on a value
  containing `&` or a space, and the failure is quiet: the variable is simply never set and
  the next call goes out unauthenticated, returning 401. `~/Desktop/MERCOR/SVA/.env.local`
  has this defect today. The script single-quotes every value it writes.
- **It never silently discards a working key.** If a key is already present, the default is
  to keep and re-validate it. Replacing requires an explicit `y` at an interactive prompt.
- **It never overwrites unrelated keys** already in the file. Existing entries are preserved.

## Where the other skills read from

The rest of the spinup set was written against `~/Desktop/MERCOR/.env.local`, and one ops
skill (`run-in-taiga`) reads `~/.claude/credentials/panacea.env`, which does not exist on any
machine checked. `~/.claude/credentials/spinup.env` is the single home going forward, chosen
because `~/.claude/credentials/` is already the convention for `taiga_oauth.json`, is outside
every git repo, and does not assume a `~/Desktop/MERCOR` tree.

Loading it is the same one-liner everywhere:

```bash
set -a; . ~/.claude/credentials/spinup.env; set +a
```
