#!/usr/bin/env python3
"""Link a GitHub PR to a Notion issue.

Given a Notion issue URL and a PR URL, it does BOTH:
  1. inserts a row into the Pull Requests database (URL + relation to the issue) — the
     two-way relation surfaces the linked PRs on the issue, and
  2. posts a comment on the GitHub PR linking back to the Notion issue.
Auth: NOTION_TOKEN (Notion API) + an authenticated `gh` CLI (for the GitHub comment).

Works for issues in Tech Issues (ISSUE-) and Task List (TASK-) — the relation column is
chosen from the issue page's parent database.

Usage:
    NOTION_TOKEN=... python link_pr.py --notion-url <issue url> --pr-url <pr url> [--status Open] [--pr-title "..."] [--force]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

PRS_DB = "390bfd2f-80ba-80f3-88b0-ce0b805397da"    # Pull Requests DB
PR_URL_PROP = "URL"
PR_STATUS_PROP = "Status"

# Which PRs-DB relation column to set, keyed by the issue page's parent database id
# (dashless, lowercase).
RELATION_BY_DB = {
    "0cabad237e624481bd8c48c8a4a08a7b": "\U0001f41b Tech Issues",  # 🐛 Tech Issues
    "49b66499784e46729d650e98f6e0a402": "✅ Task List",         # ✅ Task List
}

# A Notion page id is either a dashed UUID or a bare 32-char hex run. Match it in
# the ORIGINAL string (never strip dashes globally, or a hex-ending slug like
# "...Continue-<id>" would merge into the id and misalign it). The id trails the
# slug, so take the LAST match.
_ID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"|[0-9a-fA-F]{32}"
)


def _find_id(text):
    if not text:
        return None
    matches = _ID_RE.findall(text)
    if not matches:
        return None
    return matches[-1].replace("-", "").lower()


def extract_page_id(value):
    """Return the page id as a dashed UUID. Handles the clean `.../Title-<id>`
    form, a raw id, and the in-database form `.../DB-<dbid>?p=<pageid>` (page id
    is the `p` query param; the path holds the database id, which we must NOT use)."""
    parsed = urllib.parse.urlparse(value)
    query = urllib.parse.parse_qs(parsed.query)
    raw = _find_id(query["p"][0]) if query.get("p") else None
    if raw is None:
        raw = _find_id(parsed.path or value)
    if raw is None:
        raise ValueError(
            "could not find a 32-character Notion page id in: {!r}".format(value)
        )
    return "{}-{}-{}-{}-{}".format(
        raw[0:8], raw[8:12], raw[12:16], raw[16:20], raw[20:32]
    )


def request(method, path, token, body=None):
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise SystemExit(
            "Notion API {} {} failed: HTTP {}\n{}".format(method, path, e.code, detail)
        )
    except urllib.error.URLError as e:
        raise SystemExit("Notion API {} {} failed: {}".format(method, path, e.reason))


# --- Pull Requests DB row -----------------------------------------------------

def find_pr_row(pr_url, token):
    res = request("POST", "/databases/%s/query" % PRS_DB, token,
                  {"filter": {"property": PR_URL_PROP, "url": {"equals": pr_url}}, "page_size": 1})
    results = res.get("results", [])
    return results[0] if results else None


def relation_for_issue(page_id, token):
    """Pick the PRs-DB relation column from the issue page's parent database."""
    res = request("GET", "/pages/" + page_id, token)
    db = ((res.get("parent") or {}).get("database_id") or "").replace("-", "").lower()
    rel = RELATION_BY_DB.get(db)
    if not rel:
        raise SystemExit("issue page is not in a known database (parent: {}).".format(db or "?"))
    return rel


def create_pr_row(pr_url, issue_page_id, relation, name, status, token):
    body = {
        "parent": {"database_id": PRS_DB},
        "properties": {
            "Name": {"title": [{"text": {"content": name}}]},
            PR_URL_PROP: {"url": pr_url},
            relation: {"relation": [{"id": issue_page_id}]},
            PR_STATUS_PROP: {"status": {"name": status}},
        },
    }
    return request("POST", "/pages", token, body)


# --- GitHub PR comment (linkback to the Notion issue) -------------------------

def pr_has_comment(pr_url, needle):
    r = subprocess.run(
        ["gh", "pr", "view", pr_url, "--json", "comments", "--jq", ".comments[].body"],
        capture_output=True, text=True,
    )
    return needle in r.stdout


def comment_on_pr(pr_url, issue_url):
    try:
        r = subprocess.run(
            ["gh", "pr", "comment", pr_url, "--body", "Notion issue: " + issue_url],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        raise SystemExit("`gh` CLI not found; install + authenticate it to post the PR comment.")
    if r.returncode != 0:
        raise SystemExit("gh pr comment failed: " + (r.stderr.strip() or r.stdout.strip()))


def pr_title(pr_url):
    try:
        r = subprocess.run(
            ["gh", "pr", "view", pr_url, "--json", "title", "--jq", ".title"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        raise SystemExit("`gh` CLI not found; pass --pr-title or install/authenticate gh.")
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit(
            "could not read PR title via gh (pass --pr-title): "
            + (r.stderr.strip() or r.stdout.strip())
        )
    return r.stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Link a GitHub PR to a Notion issue (row + comment).")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--notion-url", help="Notion issue URL (page id is extracted from it)")
    src.add_argument("--page-id", help="Notion issue page id (32-hex or dashed UUID)")
    parser.add_argument("--pr-url", required=True, help="GitHub PR URL to link")
    parser.add_argument("--status", default="Open", help="PR row status: Draft | Open | Merged | Closed")
    parser.add_argument("--pr-title", help="PR row name (defaults to the GitHub PR title via gh)")
    parser.add_argument("--force", action="store_true",
                        help="re-post the PR comment even if it already links the issue")
    args = parser.parse_args(argv)

    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise SystemExit("NOTION_TOKEN environment variable is not set.")

    page_id = extract_page_id(args.notion_url or args.page_id)

    # 1) Insert the Pull Requests DB row (idempotent — never duplicates a URL).
    if find_pr_row(args.pr_url, token):
        print("PR row already exists; skipping insert.")
    else:
        relation = relation_for_issue(page_id, token)
        name = args.pr_title or pr_title(args.pr_url)
        create_pr_row(args.pr_url, page_id, relation, name, args.status, token)
        print("Inserted PR row {!r} -> {} ({}) via {!r}.".format(name, args.pr_url, args.status, relation))

    # 2) Comment the Notion issue link back on the GitHub PR.
    issue_url = args.notion_url or ("https://www.notion.so/" + page_id.replace("-", ""))
    if not args.force and pr_has_comment(args.pr_url, issue_url):
        print("GitHub PR already links the Notion issue; skipping comment.")
    else:
        comment_on_pr(args.pr_url, issue_url)
        print("Commented Notion issue link on {}.".format(args.pr_url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
