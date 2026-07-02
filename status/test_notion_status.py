#!/usr/bin/env python3
"""Offline tests for notion_status.py (no network)."""
import sys

import notion_status as ns

fail = 0


def check(name, got, want):
    global fail
    ok = got == want
    fail += 0 if ok else 1
    print("%s  %-46s got=%r want=%r" % ("ok " if ok else "FAIL", name, got, want))


def ev(action, **pr):
    return {"action": action, "pull_request": dict(pr)}


review = lambda state: {"action": "submitted", "review": {"state": state}, "pull_request": {}}

print("--- pr_row_status_key (Pull Requests DB row) ---")
check("opened non-draft", ns.pr_row_status_key(ev("opened", draft=False)), "open")
check("opened draft", ns.pr_row_status_key(ev("opened", draft=True)), "draft")
check("converted_to_draft", ns.pr_row_status_key(ev("converted_to_draft")), "draft")
check("ready_for_review", ns.pr_row_status_key(ev("ready_for_review", draft=False)), "open")
check("reopened", ns.pr_row_status_key(ev("reopened", draft=False)), "open")
check("closed merged", ns.pr_row_status_key(ev("closed", merged=True)), "merged")
check("closed not merged", ns.pr_row_status_key(ev("closed", merged=False)), "closed")
check("review (no row change)", ns.pr_row_status_key(review("changes_requested")), None)

print("--- issue_status_key (Tech Issues) ---")
check("opened non-draft", ns.issue_status_key(ev("opened", draft=False)), "in_pr")
check("opened draft (skip)", ns.issue_status_key(ev("opened", draft=True)), None)
check("ready_for_review", ns.issue_status_key(ev("ready_for_review", draft=False)), "in_pr")
check("reopened non-draft", ns.issue_status_key(ev("reopened", draft=False)), "in_pr")
check("reopened draft (skip)", ns.issue_status_key(ev("reopened", draft=True)), None)
check("closed merged", ns.issue_status_key(ev("closed", merged=True)), "for_qa")
check("closed not merged", ns.issue_status_key(ev("closed", merged=False)), None)
check("review changes_requested", ns.issue_status_key(review("changes_requested")), "fixes_required")
check("review approved", ns.issue_status_key(review("approved")), None)

print("--- [ISSUE-N] extraction ---")
check("issue tag", bool(ns._ID_RE.search("body\nNotion: ISSUE-21360")), True)
m = ns._ID_RE.search("see TASK-42")
check("task number", int(m.group(2)) if m else None, 42)
check("no tag", ns._ID_RE.search("nothing here"), None)

print("--- others_all_done (gate reads sibling row Status) ---")


def rows(*specs):
    def _notion(method, path, token, body=None):
        return {"object": "list", "results": [
            {"id": rid, "properties": {"URL": {"url": u}, "Status": {"status": {"name": s}}}}
            for (rid, u, s) in specs]}
    return _notion


ns.notion = rows(("r1", "u1", "Merged"), ("cur", "u2", "Open"))
check("sibling merged, current excluded", ns.others_all_done("iss", "cur", "t"), True)
ns.notion = rows(("r1", "u1", "Open"), ("cur", "u2", "Merged"))
check("sibling still open", ns.others_all_done("iss", "cur", "t"), False)
ns.notion = rows(("r1", "u1", "Closed"), ("r2", "u2", "Merged"), ("cur", "u3", "Merged"))
check("all siblings done", ns.others_all_done("iss", "cur", "t"), True)
ns.notion = lambda m, p, t, b=None: {"object": "error", "message": "x"}
check("rows unreadable -> None", ns.others_all_done("iss", "cur", "t"), None)

print("\n%d failure(s)" % fail)
sys.exit(1 if fail else 0)
