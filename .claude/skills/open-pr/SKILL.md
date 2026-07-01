---
name: open-pr
description: Open (or detect) the PR for the current OpenSpec change and link it to its Notion issue. Use when the user asks to open/raise a PR for work planned via OpenSpec.
compatibility: Requires the `gh` CLI (authenticated), `python3`, and a `NOTION_TOKEN` environment variable (an internal Notion integration shared with the issues database).
metadata:
  author: notion-issue-sync
  version: "1.0"
---

Open the pull request for the current OpenSpec change and attach the PR link to
its Notion issue. The Notion API call is done by the colocated deterministic
script `link_pr.py` (no LLM in the API path); this skill only orchestrates.

## Prerequisites

- `gh` authenticated for the target repo.
- `python3` available.
- `NOTION_TOKEN` set to an internal Notion integration token that has been shared
  with the issue's database. Without it, `link_pr.py` exits with a clear error.

## Steps

1. **Identify the change.** Determine the active OpenSpec change (from the current
   git branch, the conversation, or `openspec list`). Note its directory:
   `openspec/changes/<change>/`. Announce which change you are using.

2. **Read the Notion issue URL.** Read `notion:` from
   `openspec/changes/<change>/.openspec.yaml`.
   - If the field is **missing or empty**, ask the user for the Notion issue URL
     before continuing (do NOT guess or silently skip). Offer to record it under
     `notion:` in that `.openspec.yaml` so future runs are automatic.

3. **Ensure a PR exists.** On the current branch:
   ```bash
   gh pr view --json url,number,state
   ```
   - If a PR exists, use its `url`.
   - If none exists, create one, drafting the title and body from the change's
     `proposal.md` (title = a concise summary of the change; body = the "Why" and
     "What Changes"):
     ```bash
     gh pr create --draft --title "<summary>" --body "<from proposal.md>"
     ```
   Capture the resulting PR URL.

4. **Link the PR to the Notion issue.** Run the colocated linker (idempotent):
   ```bash
   python3 "<this skill dir>/link_pr.py" --notion-url "<notion url>" --pr-url "<pr url>" --once
   ```
   - Default behavior posts a comment on the Notion issue with the PR link.
   - To write a URL property instead of a comment, add `--property "<Property Name>"`.

5. **Report.** Show the PR URL and the linker's result. If `link_pr.py` exits
   non-zero, surface its message verbatim and stop:
   - `NOTION_TOKEN environment variable is not set` → ask the user to export it.
   - An HTTP error mentioning comment capability → the integration lacks comment
     access; retry with `--property "<Property Name>"` or fix the integration.

## Notes

- This skill only **links** the PR. It does **not** change the Notion issue's
  status (that is handled separately, on PR merge — out of scope here).
- Re-running is safe: `--once` skips when the PR link is already present.
