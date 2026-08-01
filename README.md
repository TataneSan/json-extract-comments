# json-extract-comments

Extract comment-like fields — keys equal to `//` or starting with
`comment_` — from JSONL documents, one match per line. Also provides a
`--strip` mode that removes those fields and prints the cleaned JSONL.

## Features

- Default key matchers: `"//"` exactly, or any key starting with `comment_`.
- Extra matchers via `--patterns` (comma-separated regexes).
- `--recursive` walks nested objects and arrays.
- Output mode: one JSON object per match `{"path": ..., "value": ...}`.
- `--strip` mode: remove comment-like keys and output cleaned JSONL.
- `--check` CI mode: exit 2 when no comment-like key is found.
- `--json` machine-readable summary on stderr.
- Reads stdin by default.

## Install

From a clone:

```sh
pip install .
```

Or directly from git:

```sh
pip install git+https://github.com/TataneSan/json-extract-comments.git
```

## Usage

```sh
json-extract-comments [INPUT] [options]
```

### Options

| Option | Description |
| ------ | ----------- |
| `--recursive` | Walk nested objects/arrays (default: top-level keys only). |
| `--patterns` | Comma-separated extra regexes for key names. |
| `--separator` | Separator in dotted key paths (default `.`). |
| `--strip` | Remove comment keys instead of extracting them; output cleaned JSONL. |
| `--check` | Exit 2 when no comment-like key is found. |
| `--json` | Print a JSON summary to stderr. |

### Examples

Extract top-level comment fields:

```sh
$ printf '%s\n' '{"name":"x","//":"todo"}' '{"a":1}' '{"comment_note":"ping"}' | json-extract-comments
{"path": "//", "value": "todo"}
{"path": "comment_note", "value": "ping"}
```

Recursive extraction with path in nested structures:

```sh
$ printf '%s\n' '{"a":{"b":{"comment_why":"nested"}}}' | json-extract-comments --recursive
{"path": "a.b.comment_why", "value": "nested"}
```

Strip comment fields:

```sh
$ printf '%s\n' '{"a":1,"//":"x","comment_note":"y"}' | json-extract-comments --strip
{"a": 1}
```

CI guard that fails when no comment key is found:

```sh
$ printf '%s\n' '{"a":1}' | json-extract-comments --check
# exit code: 2
```

Custom matchers:

```sh
$ printf '%s\n' '{"note":"y","_debug":1,"b":2}' | json-extract-comments --patterns '^note$,^_debug'
{"path": "note", "value": "y"}
{"path": "_debug", "value": 1}
```

## Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | Success |
| 1 | CLI / I-O / JSON parse error |
| 2 | `--check` and no comment-like key found |

## License

MIT — see [LICENSE](LICENSE).
