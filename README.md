# re-expertise

A set of reusable **Agent Skills** that teach the evidence-first method for reverse-engineering native binaries
— for interoperability with, and modding of, software you own. The skills are universal: no single engine or
project is baked in; specific engines appear only as brief, clearly-labelled worked examples.

They install into both **Claude Code** and **OpenCode** from one copy, via the [`skills`
CLI](https://github.com/vercel-labs/skills) (skills.sh).

## What is here

| Skill | Use it when you need to… |
|---|---|
| **re-workflow** | plan or audit RE work the evidence-first way: cite every offset/field/function, cap failed attempts, keep recon docs, engine maps, a gotchas log, and run parallel-agent lanes |
| **re-tooling** | answer questions about a PE (x64) offline — fingerprint, disassemble, function bounds, callers, callees, references, string/import lookups — with capstone + pefile |
| **re-ghidra-mcp** | run Ghidra headless, apply your own labels with prologue checks, and keep a decompiler/analysis MCP server always-on and supervised (with a real health probe) |
| **re-rea** | drive the `rea` Ghidra-backed agent CLI/MCP, and make it reuse an analysed project instead of re-importing on every call (seconds instead of ~20 minutes) |
| **re-hooking** | resolve engine addresses across versions, validate pointers, run on the right thread, and follow a detour contract — with the rule that plugin code must never fault inside the host |
| **re-runtime-introspection** | dump a target's reflection/RTTI metadata, diff those dumps between builds to catch moved offsets, and read live objects safely |
| **re-verification** | make every feature prove itself: diagnostic logs plus an automated self-check, owner-vs-observer lines in the same terms, measured on a calm baseline |

Each skill is a folder `skills/<name>/` with a `SKILL.md` (kept under ~500 lines), deeper material in
`references/*.md`, and any code in `scripts/`.

### The design split (why seven skills)

The skills separate **method** from **mechanics** so an agent loads only what the task needs. `re-workflow` is
the method everything else serves. The mechanics divide along the tool you reach for and the moment you are in:
static offline analysis (`re-tooling`), the heavyweight analysis server (`re-ghidra-mcp`) and its agent CLI
(`re-rea`), attaching to code (`re-hooking`), reading the engine's own metadata and live objects
(`re-runtime-introspection`), and proving the result (`re-verification`). A task like "add one hook" pulls in
`re-workflow` → `re-tooling`/`re-ghidra-mcp` to find the address → `re-hooking` to attach → `re-verification` to
prove it, without ever loading the others.

## Install

Uses the `skills` CLI. Pin a version; `skills@1.7.0` is used in the examples. The owner/repo is a placeholder
until the repository is published somewhere the CLI can fetch it.

```sh
# See what the repo offers (from a published repo)
npx skills@1.7.0 add <owner>/re-expertise --list

# Global install for BOTH tools (one copy serves Claude Code and OpenCode)
npx skills@1.7.0 add <owner>/re-expertise -g -a claude-code -a opencode -y

# One skill, into the current project only, for one tool
npx skills@1.7.0 add <owner>/re-expertise --skill re-ghidra-mcp -a claude-code
```

### Where the CLI puts them

| Tool | Project scope | Global scope |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` (symlink → `~/.agents/skills/`) |
| OpenCode | `.agents/skills/` | `~/.agents/skills/` (also reads `~/.config/opencode/skills/`) |

Observed with `skills@1.7.0` on Windows (`-g -a claude-code -a opencode`): the real folders went to
`~/.agents/skills/<name>/`, which OpenCode reads directly (the CLI calls it "universal"), and
`~/.claude/skills/<name>` became a symlink to them for Claude Code. So one copy serves both tools. Pass
`--copy` to force copies instead of symlinks (useful where symlink creation needs elevation or Developer Mode).

### Install from a local clone (before publishing)

```sh
git clone <this repo> re-expertise && cd re-expertise
npx skills@1.7.0 add . --list                 # discover the skills in the working tree
npx skills@1.7.0 add . -g -a claude-code -a opencode -y
```

Published repos are listed by install count on [skills.sh](https://skills.sh).

## Example prompts that trigger each skill

- re-workflow — "Help me plan this reverse-engineering task evidence-first; I keep guessing at offsets."
- re-tooling — "Which functions in this .exe call the one that references the 'config.json' string? Find the string xref first."
- re-ghidra-mcp — "Set up Ghidra headless analysis and keep the MCP server always-on; it keeps dropping after reboots."
- re-rea — "Make rea reuse my already-analysed Ghidra project instead of re-importing the binary every call."
- re-hooking — "I'm adding a native hook to my mod; how do I resolve the address across versions and keep it from crashing the host?"
- re-runtime-introspection — "Dump the engine's RTTI and diff it against the previous build to find offsets that moved."
- re-verification — "What should this feature log so a tool can confirm it works without me watching?"

## Development

```sh
# One-time: a Python 3.12 venv with pinned deps (keep caches off the system drive)
python -m venv .venv            # or: uv venv --python 3.12 .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux/macOS: .venv/bin/python

# Validate the skill layout + frontmatter, and run the unit tests
python -I tools/validate.py
python -I -m unittest discover -s tests -p "test_*.py"
```

The helper scripts need only `capstone` and `pefile` (pinned in `requirements.txt`). Tests build a tiny PE in
memory (`tests/make_pe.py`) — no compiler and no committed binary.

## Scope and ethics

This repository is for reverse-engineering software **you own**, to make it interoperate with your own tools or
to mod it, within the software's terms of use. It does not cover — and is not intended for — defeating copy
protection or license enforcement, anti-cheat or anti-tamper evasion, or touching processes or systems you do
not own. See the ethics note in `re-workflow`.

## License

MIT — see [LICENSE](LICENSE).
