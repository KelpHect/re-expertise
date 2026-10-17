---
name: re-tooling
description: >-
  Dependency-light offline disassembly and inspection helpers for PE (x64) binaries you own, for
  interoperability and modding research. Use to answer, without launching the target: what a build's fingerprint
  is, what instructions sit at an address, which function contains it, who calls a function, which imports it
  calls, what references an address, and which code uses a string. Needs only capstone and pefile; every output
  starts with the binary's fingerprint. Notes where ELF/Mach-O differ.
license: MIT
---

# Offline PE inspection helpers

Two Python files in `scripts/`:

- **`pecore.py`** — pure functions over a `PE` built from a file path. Import these from your own code and
  tests. No binary is modified and no process is touched.
- **`petool.py`** — a thin CLI over `pecore`. Run `python -I petool.py <command> <binary> [args]`.

They need only `capstone` and `pefile` (pin them: see the repo `requirements.txt`). The design ideas are
general; these are written fresh, not copied from any project.

Run untrusted binaries' tooling with `python -I` so the target's directory cannot inject a module; `petool.py`
adds its own directory to `sys.path` explicitly so it still finds `pecore` under `-I`.

## The fingerprint comes first

Every command prints one line before its answer:

```
# bin <name> size <n> sha256 <16hex> format <pe|elf|macho|raw> machine 0x8664 tds 0x<timestamp> base 0x<imagebase>
```

Quote that line with any address you cite. An address is only true for that exact build. Addresses are RVAs in
hex (VA = image base + RVA); inputs accept `0x1a2b`, `1a2b`, or `va:0x14001a2b`.

## Commands

| Command | Question it answers |
|---|---|
| `fingerprint <bin>` | identity of any file (PE/ELF/Mach-O detected; size + sha256 for all) |
| `disasm <bin> <rva> [count] [--before N]` | instructions here; a rip-relative operand shows its target and the string there |
| `func <bin> <rva> [--disasm]` | the function containing rva (from `.pdata`, chained unwind followed), its first 32 bytes (your `expect` prologue) |
| `callers <bin> <rva> [--max N]` | direct `call`/`jmp` (E8/E9) sites that target rva, each with its function |
| `callees <bin> <rva>` | direct calls and import-slot calls the containing function makes |
| `refs <bin> <rva> [--max N]` | rip-relative code references to rva, plus absolute 8-byte pointers to it (vtable slots, function tables) |
| `strings <bin> <regex> [--max N] [--utf16]` | strings in non-executable sections with their RVA |
| `imports <bin> [regex]` | import slots: IAT RVA → `dll!name` |

`pecore` exposes the same as functions: `fingerprint`, `fingerprint_line`, `PE`, `disasm`, `func_of`,
`callers`, `callees`, `code_refs`, `strings`, `import_map`, `parse_addr`. See their docstrings.

## How scanning works (and why it is fast)

Decoding every byte of a big `.text` is slow. The helpers **match a byte pattern first, then confirm each hit
with capstone** at that offset:

- `callers` scans for `E8`/`E9` opcodes, decodes each candidate, and keeps the ones whose rel32 resolves to the
  target. It does **not** truncate the result list (a well-known helper once capped output at 40 hits and hid
  the rest — do not do that; use `--max` only when you ask for it).
- `refs` decodes executable sections for rip-relative operands, and scans data sections for the literal 8-byte
  VA (vtable slots and function-pointer tables).
- A data "reference" from an exception/unwind section is usually an unwind-table row, not a pointer — read the
  bytes before trusting it (see `re-workflow` evidence notes).

## A typical derivation

1. `strings <bin> "<a string the function uses>"` — find a string near the behaviour.
2. `refs <bin> <string rva>` — the code that uses it.
3. `func <bin> <that code rva>` — the function bounds and its first bytes (copy these as the `expect` prologue
   for `re-hooking`).
4. `callers <bin> <func begin>` and `callees <bin> <func begin>` — place it in the call graph.
5. `disasm <bin> <func begin> <size>` — read it; cross-check float/vector args against a decompiler (they can
   be dropped from decompiler argument lists).

## ELF and Mach-O

`fingerprint` detects all three. The disassembly/scan ideas carry over (capstone is format-agnostic), but the
structure differs and `pecore`'s section and unwind logic is PE-specific:

- **Function bounds.** PE uses `.pdata` RUNTIME_FUNCTION rows. ELF uses `.eh_frame`/`.eh_frame_hdr` (DWARF CFI)
  or the symbol table's `st_size`; Mach-O uses `__TEXT,__unwind_info` / compact unwind or `LC_FUNCTION_STARTS`.
- **Imports.** PE uses the IAT + import descriptors. ELF uses the PLT/GOT with `.rela.plt` relocations; Mach-O
  uses stubs + `LC_DYLD_INFO`/chained fixups.
- **Build id.** PE: `TimeDateStamp` (+ a file hash). ELF: the `.note.gnu.build-id`. Mach-O: the `LC_UUID`.
- **Position independence.** ELF shared objects and Mach-O images are PIE; "RVA" means file-relative, and rip-
  relative decoding still works, but there is no fixed image base to turn RVAs into the loaded VAs.

To extend to those, add a parser alongside `pecore.PE`; keep the same return shapes so the tests and CLI stay.
