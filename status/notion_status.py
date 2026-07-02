#!/usr/bin/env python3
"""Update Notion from a GitHub PR event: the PR row's Status in the Pull Requests
DB, and the linked issue's Status in Tech Issues.

PR row Status (Pull Requests DB):
    opened(draft) / converted_to_draft            -> Draft
    opened(non-draft) / ready_for_review / reopened -> Open
    closed + merged                               -> Merged
    closed (not merged)                           -> Closed

Issue Status (Tech Issues):
    opened(non-draft) / ready_for_review / reopened -> In PR
    pull_request_review submitted = changes_requested -> Fixes Required
    closed + merged, and every OTHER linked PR row is Merged/Closed -> For QA

Issue resolution: PR html_url -> Pull Requests DB row -> its "🐛 Tech Issues" relation.
Fallback (un-linked PR): parse [ISSUE-N] from the PR body -> unique_id query on Tech Issues.
Auth: NOTION_TOKEN. Non-fatal by design (never fails a PR check); idempotent.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

CONFIG = {
    "issues_db": "0cabad23-7e62-4481-bd8c-48c8a4a08a7b",   # Tech Issues
    "id_prop": "ID",                                        # unique_id (prefix ISSUE)
    "issue_status_prop": "Status",
    "prs_db": "390bfd2f-80ba-80f3-88b0-ce0b805397da",       # Pull Requests DB
    "pr_url_prop": "URL",
    "pr_issue_relation": "\U0001f41b Tech Issues",          # "🐛 Tech Issues"
    "pr_status_prop": "Status",
    "issue_status": {"in_pr": "In PR", "fixes_required": "Fixes Required", "for_qa": "For QA"},
    "pr_status": {"draft": "Draft", "open": "Open", "merged": "Merged", "closed": "Closed"},
}

_ID_RE = re.compile(r"\b(ISSUE|TASK)-(\d+)\b", re.I)


def log(msg):
    print(msg, file=sys.stderr)


def notion(method, path, token, body=None):
    """Notion request that never raises: returns parsed JSON, or an {object:error} dict."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(NOTION_API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"object": "error", "status": e.code, "message": str(e)}
    except urllib.error.URLError as e:
        return {"object": "error", "message": str(e.reason)}


# --- resolution ---------------------------------------------------------------

def find_pr_row(pr_url, token):
    if not pr_url:
        return None
    res = notion("POST", "/databases/%s/query" % CONFIG["prs_db"], token,
                 {"filter": {"property": CONFIG["pr_url_prop"], "url": {"equals": pr_url}}, "page_size": 1})
    if res.get("object") == "error":
        log("  Pull Requests DB unavailable (%s)." % res.get("code", res.get("message")))
        return None
    results = res.get("results", [])
    return results[0] if results else None


def issue_id_from_row(row):
    rel = row.get("properties", {}).get(CONFIG["pr_issue_relation"], {}).get("relation", [])
    return rel[0]["id"] if rel else None


def resolve_issue_via_body(pr_body, token):
    if not pr_body:
        return None
    m = _ID_RE.search(pr_body)
    if not m:
        return None
    res = notion("POST", "/databases/%s/query" % CONFIG["issues_db"], token,
                 {"filter": {"property": CONFIG["id_prop"], "unique_id": {"equals": int(m.group(2))}},
                  "page_size": 1})
    results = [] if res.get("object") == "error" else res.get("results", [])
    return results[0]["id"] if results else None


# --- event -> statuses --------------------------------------------------------

def pr_row_status_key(event):
    if event.get("review") is not None:
        return None
    pr = event.get("pull_request") or {}
    a = event.get("action")
    if a == "closed":
        return "merged" if pr.get("merged") else "closed"
    if a == "converted_to_draft":
        return "draft"
    if a in ("opened", "reopened"):
        return "draft" if pr.get("draft") else "open"
    if a == "ready_for_review":
        return "open"
    return None


def issue_status_key(event):
    review = event.get("review")
    pr = event.get("pull_request") or {}
    a = event.get("action")
    if review is not None:
        if a == "submitted" and review.get("state") == "changes_requested":
            return "fixes_required"
        return None
    if a in ("opened", "ready_for_review", "reopened") and not pr.get("draft"):
        return "in_pr"
    if a == "closed" and pr.get("merged"):
        return "for_qa"
    return None


# --- writes / gate ------------------------------------------------------------

def set_status(page_id, prop, name, token):
    res = notion("PATCH", "/pages/" + page_id, token,
                 {"properties": {prop: {"status": {"name": name}}}})
    if res.get("object") == "error":
        log("  FAILED to set %r -> %r: %s" % (prop, name, res.get("message")))
        return False
    return True


def others_all_done(issue_id, current_row_id, token):
    """True if every linked PR row OTHER than the current one is Merged/Closed.
    Returns None if the rows can't be read (caller decides)."""
    done = {CONFIG["pr_status"]["merged"], CONFIG["pr_status"]["closed"]}
    res = notion("POST", "/databases/%s/query" % CONFIG["prs_db"], token,
                 {"filter": {"property": CONFIG["pr_issue_relation"], "relation": {"contains": issue_id}}})
    if res.get("object") == "error":
        return None
    open_others = []
    for row in res.get("results", []):
        if row.get("id") == current_row_id:
            continue
        st = (row.get("properties", {}).get(CONFIG["pr_status_prop"], {}).get("status") or {}).get("name")
        if st not in done:
            open_others.append((row.get("properties", {}).get(CONFIG["pr_url_prop"], {}).get("url"), st))
    if open_others:
        log("  sibling PR(s) not done: %s" % open_others)
        return False
    return True


def run(event, token, dry_run=False):
    pr = event.get("pull_request") or {}
    pr_url = pr.get("html_url")
    row = find_pr_row(pr_url, token)
    issue_id = issue_id_from_row(row) if row else resolve_issue_via_body(pr.get("body"), token)

    # 1) PR row Status (Draft / Open / Merged / Closed)
    rk = pr_row_status_key(event)
    if rk:
        if row:
            name = CONFIG["pr_status"][rk]
            log(("would set" if dry_run else "set") + " PR row -> %r" % name)
            if not dry_run:
                set_status(row["id"], CONFIG["pr_status_prop"], name, token)
        else:
            log("  no PR row for %s (link it first); skipping PR-row status." % pr_url)

    # 2) Issue Status (In PR / Fixes Required / For QA)
    ik = issue_status_key(event)
    if not ik:
        log("No issue-status transition for this event.")
        return 0
    if not issue_id:
        log("Could not resolve a Notion issue for %s; skipping issue status." % pr_url)
        return 0
    if ik == "for_qa":
        done = others_all_done(issue_id, row["id"] if row else None, token)
        if done is False:
            log("Merged, but sibling PRs are still open; leaving issue status unchanged.")
            return 0
        if done is None:
            log("  couldn't read sibling rows; leaving issue status unchanged (fail-safe).")
            return 0
    name = CONFIG["issue_status"][ik]
    log(("would set" if dry_run else "set") + " issue -> %r" % name)
    if not dry_run:
        set_status(issue_id, CONFIG["issue_status_prop"], name, token)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Sync Notion (PR row + issue Status) from a GitHub PR event.")
    p.add_argument("--event-file", default=os.environ.get("GITHUB_EVENT_PATH"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    token = os.environ.get("NOTION_TOKEN")
    if not token:
        log("NOTION_TOKEN not set; skipping (non-fatal).")
        return 0
    if not args.event_file or not os.path.exists(args.event_file):
        log("No event file; skipping.")
        return 0
    with open(args.event_file) as f:
        event = json.load(f)
    return run(event, token, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
