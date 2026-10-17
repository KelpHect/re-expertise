#!/usr/bin/env python3
"""Validate the skills repository layout and the SKILL.md frontmatter.

Checks, per the skills format (vercel-labs/skills; Claude Code / OpenCode):
  - every entry under skills/ is a directory holding a SKILL.md, and nothing is nested deeper (flat layout);
  - frontmatter has `name` and `description`;
  - `name` matches ^[a-z0-9]+(-[a-z0-9]+)*$, is 1-64 chars, and equals the folder name;
  - `description` is 1-1024 chars;
  - every relative link in SKILL.md (references/*.md, scripts/*) resolves on disk.

Exit 0 = all good, 1 = problems (listed). No third-party dependencies.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def parse_frontmatter(text):
    """Top-level `key: value` pairs between the first two '---' lines. Handles YAML block scalars
    (`>`, `>-`, `|`, `|-`): an indented block is folded (`>`) or joined with newlines (`|`)."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    lines = text[3:end].strip("\n").splitlines()
    out = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"([A-Za-z0-9_]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", ">-", ">+", "|", "|-", "|+"):
            fold = val.startswith(">")
            body = []
            while i < len(lines) and (lines[i].strip() == "" or lines[i].startswith((" ", "\t"))):
                body.append(lines[i].strip())
                i += 1
            val = (" ".join(b for b in body if b) if fold else "\n".join(body)).strip()
        elif len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        out[key] = val
    return out


def check_skill(folder, problems):
    name = os.path.basename(folder)
    skill_md = os.path.join(folder, "SKILL.md")
    if not os.path.isfile(skill_md):
        problems.append("%s: no SKILL.md" % name)
        return
    text = open(skill_md, encoding="utf-8").read()
    fm = parse_frontmatter(text)
    if fm is None:
        problems.append("%s: SKILL.md has no YAML frontmatter" % name)
        return
    fname = fm.get("name", "")
    desc = fm.get("description", "")
    if not fname:
        problems.append("%s: frontmatter missing `name`" % name)
    else:
        if not NAME_RE.match(fname):
            problems.append("%s: name %r fails ^[a-z0-9]+(-[a-z0-9]+)*$" % (name, fname))
        if not (1 <= len(fname) <= 64):
            problems.append("%s: name length %d not in 1..64" % (name, len(fname)))
        if fname != name:
            problems.append("%s: name %r != folder %r" % (name, fname, name))
    if not desc:
        problems.append("%s: frontmatter missing `description`" % name)
    elif not (1 <= len(desc) <= 1024):
        problems.append("%s: description length %d not in 1..1024" % (name, len(desc)))

    # links resolve
    body = text[text.find("\n---", 3) + 4:] if text.startswith("---") else text
    for target in LINK_RE.findall(body):
        link = target.split("#")[0].strip()
        if not link or link.startswith(("http://", "https://", "mailto:")):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(folder, link))):
            problems.append("%s: broken link %r" % (name, target))


def main():
    problems = []
    if not os.path.isdir(SKILLS):
        print("no skills/ directory at %s" % SKILLS)
        return 1
    entries = sorted(os.listdir(SKILLS))
    skill_dirs = []
    for e in entries:
        p = os.path.join(SKILLS, e)
        if os.path.isfile(p):
            problems.append("skills/%s is a file; skills must be folders" % e)
        elif os.path.isdir(p):
            skill_dirs.append(p)
    if not skill_dirs:
        problems.append("skills/ holds no skill folders")
    for folder in skill_dirs:
        check_skill(folder, problems)

    if problems:
        print("VALIDATION FAILED (%d problem(s)):" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1
    print("OK: %d skill(s) valid" % len(skill_dirs))
    for folder in skill_dirs:
        print("  - " + os.path.basename(folder))
    return 0


if __name__ == "__main__":
    sys.exit(main())
