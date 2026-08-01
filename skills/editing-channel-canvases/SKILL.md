---
name: editing-channel-canvases
description: Operating manual for editing the Sparta vertical Slack channel-canvas templates (Abacus set) via mercor-mcp. Use when asked to edit, update, fill a TBD in, or add a canvas for an Abacus/vertical Slack channel.
metadata:
  author: ryugo-eun
  outbound_writes: true
---

# Editing channel canvases

Operating manual for maintaining the Slack channel canvases of a Sparta vertical (currently the Abacus set). All canvas IDs, channel IDs, and open TBD slots live in [reference/canvas-registry.md](reference/canvas-registry.md); read it before any edit.

## Tools

Use `mcp__mercor-mcp__slack_read_canvas`, `slack_update_canvas`, `slack_create_canvas`. Every call needs `workspace` (the vertical's Slack workspace name, e.g. `"Abacus"`); reference-canvas reads use that vertical's workspace name from the registry. Do not use the `mcp__claude_ai_Slack__*` variants; they are authed to the Mercor workspace only and cannot see vertical workspaces.

## Edit workflow

1. **Read first.** `slack_read_canvas` for the current body and `section_id_mapping`. Never edit from a remembered or cached copy; the team edits these by hand too.
2. **Pick the safe write mode:**
   - **Full-body replace** (`action=replace`, NO `section_id`) is the default for any content change. Pass the complete corrected body **without the title heading**: the canvas keeps its own title element, and including `# Title` in the body duplicates it.
   - **Append** (`action=append`, no section_id) is safe for adding a section at the end.
   - **Section replace** (`action=replace` + `section_id`) is dangerous on HEADING sections: that block extends from the targeted heading to the next real `#`/`##`, so replacing it takes everything under it with it. Targeting a **single non-heading element** (a paragraph, a link line, a list, a callout) replaces only that element: verified 2026-08-01 across 6 Cadre canvases, including a mid-document link line in Key Links that left the 20+ elements after it untouched. That is the shape to prefer, one element per operation, and it is also the only shape available in vertical workspaces, where a full-body replace is REJECTED (`missing_required_field:section_id`). Probe first on a canvas's LAST element when unsure, then re-read.
3. **Verify.** Re-read the canvas after writing and diff against intent. If a write clobbered content, restore immediately via full-body replace from the pre-edit read (this is why step 1 is mandatory).
4. **Log.** If the edit changes what the template IS (new section type, new canvas), update the registry reference file, the memory `project_abacus_channel_canvases`, and the spinup Essentials checklist note (row "Slack channel canvases" in sheet `1CZqjPsGV2WQoWCcKil89KbPJ2QDqj5V0uzNAFowq46Y`).

## Canvas-flavored markdown rules

- Channel mentions: `![](#C0BG6D7EFNK)` on the ID, never `<#C…>` or the channel name.
- User mentions: `![](@U…)`; inline renders as text, own-line renders as a profile card.
- Images embed only from `*.slack.com/files/*` URLs. To add an image, host it first: `upload_get_url` → curl PUT → `upload_send_to_slack` into the target channel, then embed the returned permalink. The hosting message must stay in the channel or the embed breaks.
- Callouts: `::: {.callout}` … `:::`. Headings max `###`; no headings inside list items; don't nest mixed list types.
- `slack_create_canvas` takes the title as a separate parameter; never repeat it in `content`.

## Content conventions

- Friendly, welcoming tone. No enforcement-threat language ("will not be tolerated", "will be deleted"); state the norm and the reason instead.
- No em dashes anywhere.
- Unresolved facts get an explicit **TBD slot** stating what lands there ("time and link posted here once scheduled"), never an invented value. Fill a TBD only from a value the user supplied or a verified source.
- Comp numbers, call times, and quotas are load-bearing: change them only on explicit instruction, and note the source.
- Every canvas ends with (or contains) routing: where questions of each type actually go, using channel mentions.

## Creating a new canvas

`slack_create_canvas` makes a STANDALONE canvas owned by the caller; the API cannot attach it to a channel. After creating: give the user the URL and remind them to share it into the channel (share icon → channel). The `in:#channel type:canvases` search only finds canvases shared as files, not channel-tab canvases, so absence from search does not mean absence.

When drafting a new channel type, synthesize from the reference canvases of all three source verticals listed in the registry (Panacea, Vigil, Sanctum) rather than porting one vertical's canvas wholesale.
