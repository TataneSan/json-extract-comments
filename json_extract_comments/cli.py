#!/usr/bin/env python3
"""json-extract-comments - Pull comment-like fields out of JSON/JSONL documents.

Many JSON workloads sneak informal comments into objects as "//...", "_comment",
"comment_*" keys, or as plain "//"-prefixed lines between documents. This tool
collects them and prints them (one per line, or grouped as JSON), so the rest
of the pipeline can consume strictly typed JSON.

Exit codes:
    0 - success
    1 - I/O or CLI error
    2 - --check found no comment at all (CI gate)
"""

import argparse
import json
import sys

PROG = "json-extract-comments"
VERSION = "1.0.0"

DEFAULT_KEYS = ["//", "_comment", "comment", "comments", "note", "notes",
                "description", "_note"]


def is_comment_line(line):
    s = line.lstrip()
    return s.startswith("//") or s.startswith("#")


def walk(obj, path, keys, prefix_mode, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = "%s.%s" % (path, k) if path else k
            kl = k.lower()
            matched = False
            if prefix_mode:
                matched = any(kl.startswith(p.lower()) or kl == p.lower()
                              for p in keys)
            else:
                matched = kl in [x.lower() for x in keys]
            if matched and isinstance(v, str):
                out.append((new_path, v))
            elif matched:
                out.append((new_path, v))
            walk(v, new_path, keys, prefix_mode, out)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            walk(item, "%s[%d]" % (path, i), keys, prefix_mode, out)


def parse_documents(text):
    """Return (docs, bare_comments) splitting comment lines from JSON lines."""
    bare = []
    json_part_lines = []
    for line in text.splitlines():
        if is_comment_line(line):
            bare.append(line.strip())
        else:
            json_part_lines.append(line)
    json_part = "\n".join(json_part_lines).strip()
    docs = []
    if json_part:
        try:
            docs = [json.loads(json_part)]
        except json.JSONDecodeError:
            docs = []
            for lineno, line in enumerate(json_part.splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    docs.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError("invalid JSON at line %d: %s" % (lineno, exc))
    return docs, bare


def main(argv=None):
    p = argparse.ArgumentParser(
        prog=PROG,
        description="Extract comment-like fields (//, _comment, comment_*, ...) "
        "from JSON/JSONL documents and standalone comment lines.",
    )
    p.add_argument("file", nargs="?", default="-",
                   help="input JSON/JSONL file (default: stdin)")
    p.add_argument("--keys", metavar="KEY,KEY,...",
                   help="comma-separated keys to look for (default: %s)"
                   % ",".join(DEFAULT_KEYS))
    p.add_argument("--prefix", action="store_true",
                   help="match keys by prefix (comment_* style) instead of exact name")
    p.add_argument("--strip", action="store_true",
                   help="output JSONL with comment fields removed instead of extracting them")
    p.add_argument("--check", action="store_true",
                   help="CI: exit 2 if no comment was found")
    p.add_argument("--json", action="store_true",
                   help="print the extracted comments as a JSON array of {path,value}")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    args = p.parse_args(argv)

    keys = [k.strip() for k in (args.keys.split(",") if args.keys
                                else DEFAULT_KEYS) if k.strip()]
    if not keys:
        print("%s: no keys configured" % PROG, file=sys.stderr)
        return 1

    try:
        if args.file == "-":
            text = sys.stdin.read()
        else:
            with open(args.file, "r", encoding="utf-8") as fh:
                text = fh.read()
    except OSError as exc:
        print("%s: cannot read %s: %s" % (PROG, args.file, exc), file=sys.stderr)
        return 1

    try:
        docs, bare = parse_documents(text)
    except ValueError as exc:
        print("%s: %s" % (PROG, exc), file=sys.stderr)
        return 1

    found = []
    for di, doc in enumerate(docs):
        path = "[%d]" % di
        walk(doc, path, keys, args.prefix, found)

    for line in bare:
        found.append(("(line)", line))

    if args.strip:
        if args.json:
            print("%s: --json not compatible with --strip" % PROG,
                  file=sys.stderr)
            return 1
        for doc in docs:
            stripped = strip_comments(doc, keys, args.prefix)
            print(json.dumps(stripped, ensure_ascii=False))
        return 0

    if args.json:
        report = {
            "file": args.file,
            "documents": len(docs),
            "comments": [{"path": p, "value": v} for (p, v) in found],
            "count": len(found),
        }
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for (p, v) in found:
            print("%s\t%s" % (p, v))

    if args.check:
        if not found:
            if not args.quiet and not args.json:
                print("%s: no comment found in %s" % (PROG, args.file),
                      file=sys.stderr)
            return 2
        if not args.quiet and not args.json:
            print("%s: ok - %d comment(s) found" % (PROG, len(found)),
                  file=sys.stderr)
    return 0


def strip_comments(obj, keys, prefix_mode):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = k.lower()
            if prefix_mode:
                matched = any(kl.startswith(p.lower()) or kl == p.lower()
                              for p in keys)
            else:
                matched = kl in [x.lower() for x in keys]
            if matched:
                continue
            out[k] = strip_comments(v, keys, prefix_mode)
        return out
    if isinstance(obj, list):
        return [strip_comments(x, keys, prefix_mode) for x in obj]
    return obj


if __name__ == "__main__":
    sys.exit(main())
