#!/usr/bin/env python3
"""Offline tests for link_pr.py (no network / no token needed).

Uses the real "Test issue for github sync" page id: 390bfd2f-80ba-803d-968d-d95085ebedad
"""
import os
import subprocess
import sys

import link_pr

EXPECT = "390bfd2f-80ba-803d-968d-d95085ebedad"
CASES = [
    # the copy-link URL: page id is in the path; the ?v=<32hex> is a *view* id that must be ignored
    ("https://app.notion.com/p/tutero/Test-issue-for-github-sync-390bfd2f80ba803d968dd95085ebedad?v=390bfd2f80ba80f89f1a000cceffab6f&source=copy_link", EXPECT),
    ("https://www.notion.so/Test-issue-for-github-sync-390bfd2f80ba803d968dd95085ebedad", EXPECT),
    # dashed UUID in the path
    ("https://www.notion.so/Test-issue-390bfd2f-80ba-803d-968d-d95085ebedad", EXPECT),
    # raw ids
    ("390bfd2f80ba803d968dd95085ebedad", EXPECT),
    ("390bfd2f-80ba-803d-968d-d95085ebedad", EXPECT),
    # page opened inside a database view: page id is in ?p=, db id is in the path
    ("https://www.notion.so/team/Issues-DB-11112222333344445555666677778888?p=390bfd2f80ba803d968dd95085ebedad&pm=s", EXPECT),
]

failures = 0
for value, expected in CASES:
    try:
        got = link_pr.extract_page_id(value)
    except Exception as e:  # noqa
        got = "ERROR: %s" % e
    ok = got == expected
    failures += 0 if ok else 1
    print("%s  %-72s -> %s" % ("ok " if ok else "FAIL", value[:72], got))

try:
    link_pr.extract_page_id("https://www.notion.so/just-a-title")
    print("FAIL  no-id case did not raise")
    failures += 1
except ValueError:
    print("ok   no-id case raises ValueError")

print("\n--- CLI error paths ---")


def run(args, env=None):
    return subprocess.run([sys.executable, "link_pr.py"] + args,
                          capture_output=True, text=True, env=env)


env_no_token = {k: v for k, v in os.environ.items() if k != "NOTION_TOKEN"}
r = run(["--notion-url", "https://www.notion.so/Test-issue-390bfd2f80ba803d968dd95085ebedad",
         "--pr-url", "https://github.com/o/r/pull/1"], env=env_no_token)
ok = r.returncode != 0 and "NOTION_TOKEN" in r.stderr
failures += 0 if ok else 1
print("%s  missing-token exits %s: %s" % ("ok " if ok else "FAIL", r.returncode, r.stderr.strip()))

r = run(["--notion-url", "u", "--page-id", "p", "--pr-url", "x"])
ok = r.returncode != 0
failures += 0 if ok else 1
print("%s  mutually-exclusive rejected (exit %s)" % ("ok " if ok else "FAIL", r.returncode))

r = run(["--page-id", "390bfd2f80ba803d968dd95085ebedad"])
ok = r.returncode != 0
failures += 0 if ok else 1
print("%s  missing --pr-url rejected (exit %s)" % ("ok " if ok else "FAIL", r.returncode))

print("\n%d failure(s)" % failures)
sys.exit(1 if failures else 0)
