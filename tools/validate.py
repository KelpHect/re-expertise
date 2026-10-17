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
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
# Backticked references to sibling files (`references/x.md`, `scripts/x.py`) are the common skill convention;
# treat them as links that must resolve too.
BACKTICK_REF_RE = re.compile(r"`((?:references|scripts)/[^`]+?\.[A-Za-z0-9]+)`")


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

    # links resolve: markdown links, and backticked references/ and scripts/ paths
    body = text[text.find("\n---", 3) + 4:] if text.startswith("---") else text
    targets = list(LINK_RE.findall(body)) + list(BACKTICK_REF_RE.findall(body))
    for target in targets:
        link = target.split("#")[0].strip()
        if not link or link.startswith(("http://", "https://", "mailto:")):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(folder, link))):
            problems.append("%s: broken link %r" % (name, target))


def validate(skills_dir):
    """Return a list of problem strings (empty = valid) plus the skill folders found."""
    problems = []
    if not os.path.isdir(skills_dir):
        return ["no skills/ directory at %s" % skills_dir], []
    skill_dirs = []
    for e in sorted(os.listdir(skills_dir)):
        p = os.path.join(skills_dir, e)
        if os.path.isfile(p):
            problems.append("skills/%s is a file; skills must be folders" % e)
        elif os.path.isdir(p):
            skill_dirs.append(p)
    if not skill_dirs:
        problems.append("skills/ holds no skill folders")
    for folder in skill_dirs:
        check_skill(folder, problems)
    return problems, skill_dirs


def resolve_skills_dir(argv):
    """argv[0] may be a repo root (…/skills), a skills dir directly, or absent (default to this repo)."""
    if not argv:
        return os.path.join(ROOT, "skills")
    arg = argv[0]
    if os.path.basename(os.path.normpath(arg)) == "skills":
        return arg
    if os.path.isdir(os.path.join(arg, "skills")):
        return os.path.join(arg, "skills")
    return arg


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    problems, skill_dirs = validate(resolve_skills_dir(argv))
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
