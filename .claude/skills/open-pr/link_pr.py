#!/usr/bin/env python3
"""Attach a GitHub PR link to a Notion issue page.

Deterministic, stdlib-only. Given a Notion issue URL (or page id) and a PR URL,
it either posts a comment on the page (default) or writes the PR URL into a URL
property. Auth via the NOTION_TOKEN environment variable.

Usage:
    python link_pr.py --notion-url <issue url> --pr-url <pr url>
    python link_pr.py --page-id <32-hex or uuid> --pr-url <pr url> --once
    python link_pr.py --notion-url <issue url> --pr-url <pr url> --property "Pull Requests"
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

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


def already_linked_comment(page_id, pr_url, token):
    res = request("GET", "/comments?block_id=" + page_id, token)
    for comment in res.get("results", []):
        for rt in comment.get("rich_text", []):
            if pr_url in rt.get("plain_text", ""):
                return True
    return False


def post_comment(page_id, pr_url, token):
    body = {
        "parent": {"page_id": page_id},
        "rich_text": [
            {"text": {"content": "PR: "}},
            {"text": {"content": pr_url, "link": {"url": pr_url}}},
        ],
    }
    request("POST", "/comments", token, body)


def property_already_set(page_id, prop, pr_url, token):
    res = request("GET", "/pages/" + page_id, token)
    current = res.get("properties", {}).get(prop, {})
    return current.get("url") == pr_url


def set_url_property(page_id, prop, pr_url, token):
    body = {"properties": {prop: {"url": pr_url}}}
    request("PATCH", "/pages/" + page_id, token, body)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Attach a PR link to a Notion issue page.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--notion-url", help="Notion issue URL (page id is extracted from it)")
    src.add_argument("--page-id", help="Notion page id (32-hex or dashed UUID)")
    parser.add_argument("--pr-url", required=True, help="GitHub PR URL to attach")
    parser.add_argument("--property", dest="prop", metavar="NAME",
                        help="write to this URL property instead of posting a comment")
    parser.add_argument("--once", action="store_true",
                        help="skip if the PR link is already present")
    args = parser.parse_args(argv)

    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise SystemExit("NOTION_TOKEN environment variable is not set.")

    page_id = extract_page_id(args.notion_url or args.page_id)

    if args.prop:
        if args.once and property_already_set(page_id, args.prop, args.pr_url, token):
            print("Already set on property {!r}; skipping.".format(args.prop))
            return 0
        set_url_property(page_id, args.prop, args.pr_url, token)
        print("Set PR link on property {!r} of page {}.".format(args.prop, page_id))
    else:
        if args.once and already_linked_comment(page_id, args.pr_url, token):
            print("PR already linked in a comment; skipping.")
            return 0
        post_comment(page_id, args.pr_url, token)
        print("Posted PR link comment on page {}.".format(page_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
