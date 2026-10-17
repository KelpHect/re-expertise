#!/usr/bin/env python3
"""petool: command-line front end for pecore (offline PE inspection you own, for modding/interop research).

Run with `python -I petool.py <command> <binary> [args]`. Every command prints a fingerprint line first;
quote it with any address you cite, because addresses are only true for that exact build.

  fingerprint <bin>
  disasm      <bin> <rva> [count] [--before N]
  func        <bin> <rva> [--disasm]
  callers     <bin> <rva> [--max N]
  callees     <bin> <rva>
  refs        <bin> <rva> [--max N]
  strings     <bin> <regex> [--max N] [--utf16]
  imports     <bin> [regex]

Addresses are RVAs in hex (0x1a2b or 1a2b); prefix va: for a virtual address.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # find pecore even under python -I
import pecore  # noqa: E402


def _rva(d):
    return "%#010x" % d


def main(argv=None):
    ap = argparse.ArgumentParser(prog="petool", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fingerprint", "disasm", "func", "callers", "callees", "refs", "strings", "imports"):
        p = sub.add_parser(name)
        p.add_argument("bin")
        if name in ("disasm", "func", "callers", "callees", "refs"):
            p.add_argument("addr")
        if name == "strings":
            p.add_argument("pattern")
            p.add_argument("--utf16", action="store_true")
        if name == "imports":
            p.add_argument("pattern", nargs="?", default=".")
        if name == "disasm":
            p.add_argument("count", nargs="?", type=int, default=40)
            p.add_argument("--before", type=int, default=0)
        if name == "func":
            p.add_argument("--disasm", action="store_true")
        if name in ("callers", "refs", "strings"):
            p.add_argument("--max", type=int, default=0)
    a = ap.parse_args(argv)

    if a.cmd == "fingerprint":
        print(pecore.fingerprint_line(a.bin))
        return 0

    pe = pecore.PE(a.bin)
    print(pecore.fingerprint_line(a.bin))

    if a.cmd == "disasm":
        rva = pecore.parse_addr(a.addr, pe)
        for d in pecore.disasm(pe, rva, a.count, a.before):
            note = ""
            if d["target"] is not None:
                note = "  ; -> %#x" % d["target"] + (' "%s"' % d["string"] if d["string"] else "")
            print("%s: %s %s%s" % (_rva(d["rva"]), d["mnemonic"], d["op_str"], note))
    elif a.cmd == "func":
        rva = pecore.parse_addr(a.addr, pe)
        fn = pecore.func_of(pe, rva)
        if not fn:
            print("no RUNTIME_FUNCTION covers %#x (leaf or not in .pdata)" % rva)
            return 1
        print("function %#x - %#x size %d (contains %#x)" % (fn["begin"], fn["end"], fn["size"], rva))
        print("bytes:", " ".join("%02X" % c for c in fn["bytes"]))
        if a.disasm:
            for d in pecore.disasm(pe, fn["begin"], fn["size"]):
                if d["rva"] >= fn["end"]:
                    break
                note = ("  ; -> %#x" % d["target"]) if d["target"] is not None else ""
                print("%s: %s %s%s" % (_rva(d["rva"]), d["mnemonic"], d["op_str"], note))
    elif a.cmd == "callers":
        rva = pecore.parse_addr(a.addr, pe)
        hits = pecore.callers(pe, rva, a.max)
        print("%d site(s) target %#x" % (len(hits), rva))
        for h in hits:
            fn = ("in %#x" % h["func"]) if h["func"] is not None else "(no func)"
            print("%s: %s %s" % (_rva(h["rva"]), h["mnemonic"], fn))
    elif a.cmd == "callees":
        rva = pecore.parse_addr(a.addr, pe)
        c = pecore.callees(pe, rva)
        for d in c["direct"]:
            print("%s: %s %#x" % (_rva(d["rva"]), d["mnemonic"], d["target"]))
        for d in c["imports"]:
            print("%s: %s [%#x] %s" % (_rva(d["rva"]), d["mnemonic"], d["slot"], d["name"]))
    elif a.cmd == "refs":
        rva = pecore.parse_addr(a.addr, pe)
        r = pecore.code_refs(pe, rva, a.max)
        for d in r["rip"]:
            print("%s: %s %s" % (_rva(d["rva"]), d["mnemonic"], d["op_str"]))
        for d in r["pointers"]:
            print("%s: pointer in %s" % (_rva(d["rva"]), d["section"]))
    elif a.cmd == "strings":
        for d in pecore.strings(pe, a.pattern, a.max, a.utf16):
            print("%s: %r" % (_rva(d["rva"]), d["text"]))
    elif a.cmd == "imports":
        import re
        rx = re.compile(a.pattern, re.I)
        for slot, name in sorted(pecore.import_map(pe).items()):
            if rx.search(name):
                print("%s: %s" % (_rva(slot), name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
