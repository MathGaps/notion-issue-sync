#!/usr/bin/env python3
"""Offline tests for link_pr.py (no network / no token needed)."""
import os
import subprocess
import sys

import link_pr

EXPECT = "38bbfd2f-80ba-805f-b7d5-cb4f3a7988f2"
CASES = [
    ("https://app.notion.com/p/Continue-with-Google-is-failing-38bbfd2f80ba805fb7d5cb4f3a7988f2?pvs=8&n=github_linkback", EXPECT),
    ("https://www.notion.so/Continue-with-Google-is-failing-38bbfd2f80ba805fb7d5cb4f3a7988f2", EXPECT),
    # dashed UUID in path (previously misaligned by global dash-stripping)
    ("https://www.notion.so/Title-38bbfd2f-80ba-805f-b7d5-cb4f3a7988f2", EXPECT),
    # slug ends in a hex char right before the id (previously shifted the window)
    ("https://www.notion.so/Continue-38bbfd2f80ba805fb7d5cb4f3a7988f2?v=abc", EXPECT),
    ("38bbfd2f80ba805fb7d5cb4f3a7988f2", EXPECT),
    ("38bbfd2f-80ba-805f-b7d5-cb4f3a7988f2", EXPECT),
    # page opened inside a database view: page id is in ?p=, db id is in the path
    ("https://www.notion.so/team/Issues-DB-11112222333344445555666677778888?p=38bbfd2f80ba805fb7d5cb4f3a7988f2&pm=s", EXPECT),
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
r = run(["--notion-url", "https://www.notion.so/x-38bbfd2f80ba805fb7d5cb4f3a7988f2",
         "--pr-url", "https://github.com/o/r/pull/1"], env=env_no_token)
ok = r.returncode != 0 and "NOTION_TOKEN" in r.stderr
failures += 0 if ok else 1
print("%s  missing-token exits %s: %s" % ("ok " if ok else "FAIL", r.returncode, r.stderr.strip()))

r = run(["--notion-url", "u", "--page-id", "p", "--pr-url", "x"])
ok = r.returncode != 0
failures += 0 if ok else 1
print("%s  mutually-exclusive rejected (exit %s)" % ("ok " if ok else "FAIL", r.returncode))

r = run(["--page-id", "38bbfd2f80ba805fb7d5cb4f3a7988f2"])
ok = r.returncode != 0
failures += 0 if ok else 1
print("%s  missing --pr-url rejected (exit %s)" % ("ok " if ok else "FAIL", r.returncode))

print("\n%d failure(s)" % failures)
sys.exit(1 if failures else 0)
