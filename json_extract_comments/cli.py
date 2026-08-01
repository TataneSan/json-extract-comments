"""json-extract-comments: extract comment-like fields from JSONL documents.

Keys are considered comment-like when they equal ``//`` or start with
``comment_`` (configurable via --patterns as extra regexes). Only top-level
keys are scanned by default; use --recursive to walk nested objects and arrays.

Output: one JSON object per match, as JSONL, with the shape
{"path": <dotted key path>, "value": <original JSON value>}.

Exit codes:
  0  success
  1  CLI / I-O / JSON parse error
  2  --check condition not satisfied (no comment-like field found)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Iterator, List, Optional, Sequence, Tuple

DEFAULT_PATTERNS = [r"^//$", r"^comment_"]


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="json-extract-comments",
        description=(
            "Extract comment-like fields ('//', 'comment_*') from JSONL "
            "documents, one match per line as JSON."
        ),
    )
    p.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input JSONL file (default: stdin). Use '-' for stdin.",
    )
    p.add_argument(
        "--recursive",
        action="store_true",
        help="Walk nested objects and arrays (keys inside them are matched too).",
    )
    p.add_argument(
        "--patterns",
        default=None,
        help=(
            "Comma-separated extra regexes matched against keys. "
            "Defaults: keys equal to '//' or starting with 'comment_'."
        ),
    )
    p.add_argument(
        "--separator",
        default=".",
        help="Separator used in dotted key paths (default: '.').",
    )
    p.add_argument(
        "--strip",
        action="store_true",
        help="Instead of extracting, remove comment-like fields and output the cleaned JSONL.",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 2 when no comment-like field is found.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable summary to stderr.",
    )
    return p.parse_args(argv)


def _iter_matches(
    node: Any,
    path: List[str],
    compiled: List[re.Pattern],
    recursive: bool,
    separator: str,
) -> Iterator[Tuple[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            new_path = path + [key]
            if any(rx.search(key) for rx in compiled):
                yield separator.join(new_path), value
            if recursive and isinstance(value, (dict, list)):
                yield from _iter_matches(value, new_path, compiled, recursive, separator)
    elif isinstance(node, list) and recursive:
        for i, value in enumerate(node):
            new_path = path + [f"[{i}]"]
            if isinstance(value, (dict, list)):
                yield from _iter_matches(value, new_path, compiled, recursive, separator)


def _strip_in_place(node: Any, compiled: List[re.Pattern], recursive: bool) -> int:
    removed = 0
    if isinstance(node, dict):
        drop: List[str] = []
        for key, value in node.items():
            if any(rx.search(key) for rx in compiled):
                drop.append(key)
                removed += 1
            elif recursive and isinstance(value, (dict, list)):
                removed += _strip_in_place(value, compiled, recursive)
        for key in drop:
            del node[key]
    elif isinstance(node, list) and recursive:
        for value in node:
            removed += _strip_in_place(value, compiled, recursive)
    return removed


def _compile_patterns(extra: Optional[str]) -> List[re.Pattern]:
    raw = list(DEFAULT_PATTERNS)
    if extra:
        raw.extend(s for s in (part.strip() for part in extra.split(",")) if s)
    compiled = []
    for pattern in raw:
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            raise ValueError(f"invalid pattern {pattern!r}: {exc}") from exc
    return compiled


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)

    try:
        compiled = _compile_patterns(args.patterns)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.input == "-":
        fin = sys.stdin
        close = False
    else:
        try:
            fin = open(args.input, "r", encoding="utf-8")
            close = True
        except OSError as exc:
            print(f"error: cannot open input: {exc}", file=sys.stderr)
            return 1

    total_docs = 0
    total_matches = 0
    parse_errors: List[str] = []
    kept_docs: List[str] = []

    try:
        for lineno, raw in enumerate(fin, 1):
            raw = raw.strip()
            if not raw:
                if args.strip:
                    kept_docs.append("")
                continue
            try:
                doc = json.loads(raw)
            except json.JSONDecodeError as exc:
                parse_errors.append(f"line {lineno}: {exc.msg}")
                if args.strip:
                    kept_docs.append(raw)
                continue
            total_docs += 1
            if args.strip:
                removed = _strip_in_place(doc, compiled, args.recursive)
                total_matches += removed
                kept_docs.append(json.dumps(doc, ensure_ascii=False))
            else:
                for path, value in _iter_matches(
                    doc, [], compiled, args.recursive, args.separator
                ):
                    total_matches += 1
                    print(
                        json.dumps(
                            {"path": path, "value": value}, ensure_ascii=False
                        )
                    )
    finally:
        if close:
            fin.close()

    if parse_errors:
        for err in parse_errors:
            print(f"error: {err}", file=sys.stderr)
        # Parse errors are reported but do not abort: still exit 1 flagging them.
        # The tool outputs what it could parse.
        if args.strip:
            for line in kept_docs:
                print(line)
        return 1

    if args.strip:
        for line in kept_docs:
            print(line)

    if args.json:
        summary = {
            "ok": True,
            "documents": total_docs,
            "matches": total_matches,
            "mode": "strip" if args.strip else "extract",
            "recursive": bool(args.recursive),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2), file=sys.stderr)

    if args.check and total_matches == 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
