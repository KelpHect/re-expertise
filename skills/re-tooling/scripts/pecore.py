"""pecore: dependency-light PE (x64) inspection for interoperability and modding research.

Pure functions over a binary you own. Every public function takes a `PE` built from a file path and returns
plain data; the CLI in `petool.py` wraps them. No binary is modified and no process is touched. Addresses are
RVAs (VA = image base + RVA). Needs only `pefile` and `capstone` (see requirements.txt); the fingerprint works
on any file.
"""
from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path

import capstone
import pefile


def fingerprint(path) -> dict:
    """Identity of any file, so a cited address names the exact build it came from."""
    data = Path(path).read_bytes()
    out = {
        "file": Path(path).name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if data[:2] == b"MZ":
        try:
            pe = pefile.PE(data=data, fast_load=True)
            out["format"] = "pe"
            out["machine"] = hex(pe.FILE_HEADER.Machine)
            out["timedatestamp"] = hex(pe.FILE_HEADER.TimeDateStamp)
            out["image_base"] = hex(pe.OPTIONAL_HEADER.ImageBase)
        except pefile.PEFormatError:
            out["format"] = "unknown"
    elif data[:4] in (b"\x7fELF",):
        out["format"] = "elf"
    elif data[:4] in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe"):
        out["format"] = "macho"
    else:
        out["format"] = "raw"
    return out


def fingerprint_line(path) -> str:
    fp = fingerprint(path)
    extra = ""
    if fp.get("format") == "pe":
        extra = " machine %s tds %s base %s" % (fp["machine"], fp["timedatestamp"], fp["image_base"])
    return "# bin %s size %d sha256 %s format %s%s" % (
        fp["file"], fp["size"], fp["sha256"][:16], fp["format"], extra)


class PE:
    """A PE in memory with the section helpers the queries need. PE32+ (x64) only."""

    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        self.pe = pefile.PE(data=self.data, fast_load=True)
        self.pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXCEPTION"],
        ])
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.sections = self.pe.sections

    # -- address mapping -------------------------------------------------------------------------------
    def rva2off(self, rva):
        for s in self.sections:
            size = max(s.Misc_VirtualSize, s.SizeOfRawData)
            if s.VirtualAddress <= rva < s.VirtualAddress + size:
                off = rva - s.VirtualAddress
                if off < s.SizeOfRawData:
                    return s.PointerToRawData + off
                return None  # in virtual padding, not on disk
        return None

    def off2rva(self, off):
        for s in self.sections:
            if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
                return off - s.PointerToRawData + s.VirtualAddress
        return None

    def section_of(self, rva):
        for s in self.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
                return s.Name.rstrip(b"\0").decode("latin1")
        return None

    def is_exec(self, rva):
        for s in self.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
                return bool(s.Characteristics & 0x20000000)  # MEM_EXECUTE
        return False

    def text(self):
        for s in self.sections:
            if s.Characteristics & 0x20000000:
                return s
        return self.sections[0]

    def read(self, rva, n):
        o = self.rva2off(rva)
        return self.data[o:o + n] if o is not None else b""

    def string_at(self, rva, limit=120, minlen=2):
        o = self.rva2off(rva)
        if o is None:
            return None
        end = self.data.find(b"\0", o, o + limit)
        if end <= o:
            return None
        raw = self.data[o:end]
        try:
            s = raw.decode("ascii")
        except UnicodeDecodeError:
            return None
        if len(s) < minlen or not all(32 <= ord(c) < 127 for c in s):
            return None
        return s


_md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
_md.detail = True


def _rip_target(ins):
    """RVA an instruction's rip-relative memory operand points at, or None."""
    for op in ins.operands:
        if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
            return ins.address + ins.size + op.mem.disp
    return None


def disasm(pe: PE, rva, count=40, before=0):
    """List of dicts {rva, mnemonic, op_str, target, string} starting `before` bytes before rva."""
    start = rva - before
    o = pe.rva2off(start)
    if o is None:
        raise ValueError("rva %#x is not backed by file data" % start)
    out = []
    for ins in _md.disasm(pe.data[o:o + count * 16 + 16], start):
        if len(out) >= count:
            break
        tgt = _rip_target(ins)
        out.append({
            "rva": ins.address, "mnemonic": ins.mnemonic, "op_str": ins.op_str,
            "target": tgt, "string": pe.string_at(tgt) if tgt is not None else None,
        })
    return out


def func_of(pe: PE, rva):
    """The function containing rva, from the .pdata RUNTIME_FUNCTION table (chained unwind followed to the
    parent). Returns {begin, end, size, bytes} or None for a leaf/missing entry."""
    try:
        rows = pe.pe.DIRECTORY_ENTRY_EXCEPTION
    except AttributeError:
        return None
    found = None
    for r in rows:
        if r.struct.BeginAddress <= rva < r.struct.EndAddress:
            found = (r.struct.BeginAddress, r.struct.EndAddress, r.struct.UnwindData)
            break
    if not found:
        return None
    b, e, u = found
    for _ in range(8):  # follow chained unwind info (flag 0x4) up to the parent function
        o = pe.rva2off(u)
        if o is None:
            break
        if not (pe.data[o] >> 3) & 0x4:
            break
        count = pe.data[o + 2]
        po = o + 4 + ((count + 1) & ~1) * 2
        b, e, u = struct.unpack_from("<III", pe.data, po)
    o = pe.rva2off(b)
    return {"begin": b, "end": e, "size": e - b, "bytes": pe.data[o:o + 32] if o is not None else b""}


# --- scanning: match a byte pattern first, confirm each hit with capstone (decoding all of .text is slow) ---

def _text_window(pe: PE):
    t = pe.text()
    raw = pe.data[t.PointerToRawData:t.PointerToRawData + t.SizeOfRawData]
    return raw, t.VirtualAddress


def callers(pe: PE, rva, max_hits=0):
    """Direct E8 (call) and E9 (jmp) sites whose rel32 targets rva."""
    raw, base = _text_window(pe)
    hits = []
    for m in re.finditer(rb"[\xE8\xE9]", raw):
        i = m.start()
        if i + 5 > len(raw):
            continue
        site = base + i
        o = pe.rva2off(site)
        if o is None:
            continue
        ins = next(_md.disasm(pe.data[o:o + 16], site), None)
        if ins is None or ins.mnemonic not in ("call", "jmp"):
            continue
        tgt = ins.address + ins.size + struct.unpack_from("<i", pe.data, o + 1)[0]
        if tgt == rva:
            fn = func_of(pe, site)
            hits.append({"rva": site, "mnemonic": ins.mnemonic,
                         "func": fn["begin"] if fn else None})
            if max_hits and len(hits) >= max_hits:
                break
    return hits


def callees(pe: PE, rva):
    """Direct calls and import-slot calls made inside the function containing rva."""
    fn = func_of(pe, rva)
    if not fn:
        raise ValueError("no function in .pdata contains %#x" % rva)
    o = pe.rva2off(fn["begin"])
    direct, imports = [], []
    imap = import_map(pe)
    for ins in _md.disasm(pe.data[o:o + fn["size"]], fn["begin"]):
        if ins.mnemonic in ("call", "jmp") and ins.op_str.replace("0x", "").lstrip("-").isalnum() \
                and not ins.op_str.startswith("["):
            try:
                tgt = int(ins.op_str, 16)
                if pe.is_exec(tgt):
                    direct.append({"rva": ins.address, "mnemonic": ins.mnemonic, "target": tgt})
            except ValueError:
                pass
        tgt = _rip_target(ins)
        if tgt is not None and tgt in imap:
            imports.append({"rva": ins.address, "mnemonic": ins.mnemonic,
                            "slot": tgt, "name": imap[tgt]})
    return {"direct": direct, "imports": imports}


def code_refs(pe: PE, rva, max_hits=0):
    """rip-relative references to rva from executable sections, plus 8-byte absolute pointers to it
    (vtable slots, function tables) from data sections."""
    out = {"rip": [], "pointers": []}
    for s in pe.sections:
        raw = pe.data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
        sbase = s.VirtualAddress
        if s.Characteristics & 0x20000000:
            for i in range(0, len(raw) - 5):
                site = sbase + i
                o = pe.rva2off(site)
                ins = None
                # cheap filter: only try to decode where a ModRM rip-relative form is plausible
                raw_at = pe.data[o:o + 16] if o is not None else b""
                ins = next(_md.disasm(raw_at, site), None) if raw_at else None
                if ins is None:
                    continue
                if _rip_target(ins) == rva:
                    out["rip"].append({"rva": site, "mnemonic": ins.mnemonic, "op_str": ins.op_str})
                    if max_hits and len(out["rip"]) >= max_hits:
                        break
        else:
            target_va = pe.base + rva
            for m in re.finditer(struct.pack("<Q", target_va), raw):
                out["pointers"].append({"rva": sbase + m.start(), "section": s.Name.rstrip(b"\0").decode("latin1")})
                if max_hits and len(out["pointers"]) >= max_hits:
                    break
    return out


def strings(pe: PE, pattern, max_hits=0, utf16=False):
    """ASCII (or UTF-16LE) strings in non-executable sections matching a regex, with their RVA."""
    rx = re.compile(pattern.encode("latin1"))
    out = []
    for s in pe.sections:
        if s.Characteristics & 0x20000000:
            continue
        raw = pe.data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
        if utf16:
            run = re.finditer(rb"(?:[\x20-\x7e]\x00){3,}", raw)
            for m in run:
                text = m.group().decode("utf-16le")
                if rx.search(text.encode("latin1")):
                    out.append({"rva": s.VirtualAddress + m.start(), "text": text})
                    if max_hits and len(out) >= max_hits:
                        return out
        else:
            for m in re.finditer(rb"[\x20-\x7e]{3,}", raw):
                if rx.search(m.group()):
                    out.append({"rva": s.VirtualAddress + m.start(), "text": m.group().decode("ascii")})
                    if max_hits and len(out) >= max_hits:
                        return out
    return out


def import_map(pe: PE) -> dict:
    """IAT slot RVA -> 'dll!name'."""
    out = {}
    try:
        entries = pe.pe.DIRECTORY_ENTRY_IMPORT
    except AttributeError:
        return out
    for dll in entries:
        name = dll.dll.decode("latin1")
        for imp in dll.imports:
            slot = imp.address - pe.base  # imp.address is a VA
            label = imp.name.decode("latin1") if imp.name else "ordinal_%d" % (imp.ordinal or 0)
            out[slot] = "%s!%s" % (name, label)
    return out


def parse_addr(text, pe: PE = None):
    """'0x1a2b' / '1a2b' is an RVA; 'va:0x...' subtracts the image base."""
    text = text.strip()
    if text.lower().startswith("va:"):
        if pe is None:
            raise ValueError("va: needs the binary")
        return int(text[3:], 16) - pe.base
    return int(text, 16)
