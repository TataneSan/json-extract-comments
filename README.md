# json-extract-comments

[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](pyproject.toml)

Extract **comment-like fields** ( `//`, `_comment`, `comment`, `note`, `description`,
`#`-prefixed standalone lines, ...) from JSON/JSONL documents — or strip them
out with `--strip` — so the rest of the pipeline processes strictly typed JSON.

## Features

- Walks nested objects and arrays, tracks dot-paths (`[0].items[2].note`)
- Default key list: `//`, `_comment`, `comment`, `comments`, `note`, `notes`,
  `description`, `_note` — customize with `--keys`
- `--prefix` matches keys by prefix (e.g. `comment_*`)
- Captures lone comment lines (`//foo`, `# bar`) outside the JSON structure
- `--strip` emits JSONL with the comment fields removed
- `--check` CI gate: exit 2 if no comment was found
- `--json` report (`path`, `value`, `count`)
- Pure Python standard library, no dependencies

## Installation

From source:

```sh
pip install .
```

Or directly from GitHub:

```sh
pip install git+https://github.com/TataneSan/json-extract-comments.git
```

## Usage

```text
usage: json-extract-comments [-h] [--keys KEY,KEY,...] [--prefix] [--strip]
                             [--check] [--json] [-q] [--version] [file]
```

### Extract comments

```sh
$ cat spec.json
{
  "name": "demo",
  "//": "generated file, do not edit",
  "items": [
    {"sku": "A1", "note": "backordered"},
    {"sku": "B2"}
  ]
}

$ json-extract-comments spec.json
[0].//	generated file, do not edit
[0].items[0].note	backordered
```

### Standalone comment lines in JSONL

```sh
$ cat events.jsonl
// daily batch started
{"id": 1, "status": "ok"}
{"id": 2, "status": "fail", "_comment": "handled manually"}
# rotate credentials before next run

$ json-extract-comments events.jsonl
[1]._comment	handled manually
(line)	// daily batch started
(line)	# rotate credentials before next run
```

### Match custom keys (prefix mode)

```sh
json-extract-comments spec.json --keys comment_,todo --prefix
```

### Strip comments back out

```sh
$ json-extract-comments spec.json --strip
{"name": "demo", "items": [{"sku": "A1"}, {"sku": "B2"}]}
```

### CI gate

```sh
json-extract-comments spec.json --check
# exit 0 if at least one comment found | exit 2 otherwise
```

### JSON report

```sh
$ json-extract-comments spec.json --json
{
  "file": "spec.json",
  "documents": 1,
  "comments": [
    {"path": "[0].//", "value": "generated file, do not edit"},
    {"path": "[0].items[0].note", "value": "backordered"}
  ],
  "count": 2
}
```

## Exit codes

| Code | Meaning                                  |
|------|------------------------------------------|
| 0    | success                                  |
| 1    | I/O or CLI error (missing file, bad JSON)|
| 2    | `--check` found no comment               |

## Development

Run the test suite:

```sh
python -m unittest discover -s tests -v
```

## License

MIT - see [LICENSE](LICENSE).
