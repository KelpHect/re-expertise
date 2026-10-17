"""Tests for tools/validate.py: it accepts the real repo and rejects malformed skills."""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))

import validate  # noqa: E402


GOOD = """---
name: my-skill
description: A valid skill used to exercise the validator.
---

# My skill

See `references/notes.md` and `scripts/run.py`.
"""


def _make_skill(root, name, text, with_refs=True):
    d = os.path.join(root, name)
    os.makedirs(os.path.join(d, "references"))
    os.makedirs(os.path.join(d, "scripts"))
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(text)
    if with_refs:
        open(os.path.join(d, "references", "notes.md"), "w").close()
        open(os.path.join(d, "scripts", "run.py"), "w").close()
    return d


class ValidateTests(unittest.TestCase):
    def test_real_repo_is_valid(self):
        problems, dirs = validate.validate(os.path.join(REPO, "skills"))
        self.assertEqual(problems, [])
        self.assertTrue(dirs)

    def test_good_skill_passes(self):
        with tempfile.TemporaryDirectory() as root:
            _make_skill(root, "my-skill", GOOD)
            problems, dirs = validate.validate(root)
            self.assertEqual(problems, [])
            self.assertEqual(len(dirs), 1)

    def test_name_folder_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as root:
            _make_skill(root, "wrong-folder", GOOD)  # frontmatter name is my-skill
            problems, _ = validate.validate(root)
            self.assertTrue(any("!= folder" in p for p in problems))

    def test_bad_name_regex_fails(self):
        with tempfile.TemporaryDirectory() as root:
            _make_skill(root, "Bad_Name", GOOD.replace("name: my-skill", "name: Bad_Name"))
            problems, _ = validate.validate(root)
            self.assertTrue(any("fails ^[a-z0-9]" in p for p in problems))

    def test_broken_link_fails(self):
        with tempfile.TemporaryDirectory() as root:
            _make_skill(root, "my-skill", GOOD, with_refs=False)  # the referenced files do not exist
            problems, _ = validate.validate(root)
            self.assertTrue(any("broken link" in p for p in problems))

    def test_missing_description_fails(self):
        with tempfile.TemporaryDirectory() as root:
            _make_skill(root, "my-skill", "---\nname: my-skill\n---\n# x\n")
            problems, _ = validate.validate(root)
            self.assertTrue(any("description" in p for p in problems))

    def test_skill_as_file_fails(self):
        with tempfile.TemporaryDirectory() as root:
            open(os.path.join(root, "loose.md"), "w").close()
            problems, _ = validate.validate(root)
            self.assertTrue(any("must be folders" in p for p in problems))

    def test_block_scalar_description_is_read(self):
        text = "---\nname: my-skill\ndescription: >-\n  One line\n  folded into another.\n---\n# x\n"
        fm = validate.parse_frontmatter(text)
        self.assertEqual(fm["description"], "One line folded into another.")


if __name__ == "__main__":
    unittest.main()
