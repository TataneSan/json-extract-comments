import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(args, stdin_text=""):
    return subprocess.run(
        [sys.executable, "-m", "json_extract_comments"] + args,
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=HERE,
    )


class TestExtract(unittest.TestCase):
    def test_inline_key(self):
        r = run_cli(["-q", "-"], '{"//": "note one", "x": 1}')
        self.assertEqual(r.returncode, 0)
        self.assertIn("note one", r.stdout)

    def test_nested(self):
        r = run_cli(["-q", "-"],
                    '{"a": {"note": "deep"}}')
        self.assertIn("[0].a.note", r.stdout)

    def test_jsonl_comments_lines(self):
        r = run_cli(["-q", "-"],
                    '// hello\n{"id": 1}\n{"_comment": "found"}\n')
        self.assertIn("hello", r.stdout)
        self.assertIn("found", r.stdout)

    def test_hash_comment_lines(self):
        r = run_cli(["-q", "-"], "# rotation needed\n{}\n")
        self.assertIn("rotation needed", r.stdout)

    def test_prefix_mode(self):
        r = run_cli(["-q", "--keys", "comment_", "--prefix", "-"],
                    '{"comment_a": "one", "comment_b": "two", "x": 1}')
        self.assertIn("one", r.stdout)
        self.assertIn("two", r.stdout)

    def test_strip(self):
        r = run_cli(["--strip", "-"],
                    '{"a": 1, "//": "drop me", "b": {"note": "bye"}}')
        doc = json.loads(r.stdout.strip())
        self.assertNotIn("//", doc)
        self.assertNotIn("note", doc["b"])
        self.assertEqual(doc["a"], 1)

    def test_check_none(self):
        r = run_cli(["--check", "-q", "-"], '{"a": 1}')
        self.assertEqual(r.returncode, 2)

    def test_check_found(self):
        r = run_cli(["--check", "-q", "-"], '{"a": 1, "note": "yes"}')
        self.assertEqual(r.returncode, 0)

    def test_json_report(self):
        r = run_cli(["--json", "-"], '{"note": "x", "y": 1}')
        report = json.loads(r.stdout)
        self.assertEqual(report["count"], 1)
        self.assertEqual(report["comments"][0]["value"], "x")

    def test_bad_json(self):
        r = run_cli(["-"], "{not json}")
        self.assertEqual(r.returncode, 1)

    def test_missing_file(self):
        r = run_cli(["/nonexistent/x.json"])
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
