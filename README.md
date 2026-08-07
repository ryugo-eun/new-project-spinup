# Sparta new-vertical spinup

Everything needed to stand up a new Sparta vertical end to end: 20 Claude Code skills, the
step-by-step runbook they follow, and the accumulated list of things that go wrong.

Built from the Abacus, Atria, Rampart, Cadre, Delphi, Capitol and Westwood spinups. The
governing lesson, and the reason most of this exists:

> **A clone always looks finished and is not.** Studio clones, Drive clones, automation
> clones and canvas clones all produce something that reads correct and behaves wrong,
> usually by still pointing at the vertical it was cloned from.

## Install

The skills have to sit in `~/.claude/skills/` to be usable. Cloning this repo does not
install them.

```bash
git clone https://github.com/ryugo-eun/new-project-spinup.git
cd new-project-spinup

mkdir -p ~/.claude/skills
cp -R skills/* ~/.claude/skills/
```

Restart Claude Code, then confirm they registered by asking it to list your skills. You
should see `setup-spinup-credentials` among them.

Then **run step 0 before anything else**:

```bash
cd ~/.claude/skills/setup-spinup-credentials
python3 setup_spinup_creds.py
```

Run that yourself in a terminal. It asks for your Studio API key with echo off, proves the
key is live and write-scoped against the real API, derives the ids it needs, and writes
`~/.claude/credentials/spinup.env` at 0600. **Never paste an API key into a chat message or
into a command you hand to Claude**: the literal value lands in the transcript before the
shell ever expands it.

## Start here

| File | What it is |
|---|---|
| **[SPINUP-RUNBOOK.md](SPINUP-RUNBOOK.md)** | **The main document.** Sixteen ordered steps, 0 to 15. Per step: which skill runs it, what it does, what to confirm, what goes wrong |
| [GOTCHAS.md](GOTCHAS.md) | Why the runbook says what it says. Every entry cost someone real time |
| [SKILLS.md](SKILLS.md) | Inventory of every skill, plus the gap list of steps that still have none |
| `skills/` | The skills themselves, one directory each |

## The run order, in brief

Read the runbook for the real version. The dependencies that set this order are not obvious.

```
 0  Credentials on this machine        setup-spinup-credentials
 1  Teams project and roles            create-vertical-teams-project
 2  Listing, one per expert role       create-vertical-listing
 3  Slack workspace                    manual
 4  Studio campaign                    clone-sparta-campaign
 4a   Studio dashboards                port-vertical-dashboards
 5  Extra worlds / hook gaps           clone-studio-world
 5a   Taiga env is this vertical's     restamp-taiga-env
 5b   Prove the campaign RUNS          create-smoke-test-task
 6  The nine Slack channels            provision-vertical-slack-channels
 7  Drive tree and the two forms       new-vertical-drive-folder
 8  Tags, audiences, targets           provision-vertical-teams-integrations
 9  Drive share and two calendars      add-vertical-calendars
10  Automations                        provision-vertical-automations
11  Doctor and upload bots             add-vertical-bots
12  The domain recast                  manual, and the step that matters most
13  Canvas set                         create-vertical-canvases
14  Swap the inherited links           replace-instructions-link
15  Audit                              verify-vertical-spinup
```

Three rules set that order: the listing must exist before the role that points at it,
channel ids must exist before audiences and canvases and bots, and the core-team Google
group only exists after step 8, so the Drive share cannot run earlier.

## The failures that read as done

The whole point of step 15. Each of these is present, wired, and silently useless:

- **A world with zero hooks.** Tasks strand in "Running Task AutoQC" and never reach the runner.
- **A campaign with zero dashboards.** Reviewers open Studio to an empty sidebar and read it as "no work".
- **An audience with zero targets.** The tag confers nothing.
- **An automation sitting in draft.** It exists, it never fires.
- **A Drive tree shared to nobody**, because the group and the share are separate steps.
- **A rubric that grades on the source domain.** 199 QC dimensions arrive wired, passing, and worded for someone else's job. Nothing errors; the scores are just meaningless.
- **A campaign that is fully configured and cannot run a task.** Hooks, verifier, agent, environment and file sync each fail silently and separately. Step 5b is the only thing that catches it.

## Conventions

- **Installed is the source of truth**, `skills/` here is the mirror. Sync one way only,
  installed to backup. Diff both before trusting either.
- **Never commit a secret.** Credentials live in `~/.claude/credentials/`, outside every repo.
- **Inventory before you create.** Almost nothing here is cleanly reversible.
- No em dashes anywhere, by house style.
