"""Build a tiny, valid PE32+ (x64) image in memory for the helper tests.

Nothing is compiled and nothing is downloaded: every byte is written here, so the expected answers are known.

Layout (ImageBase 0x140000000, SectionAlignment 0x1000, FileAlignment 0x200):

  .text  RVA 0x1000  func_a 0x1000-0x101D, func_b 0x1040-0x1047, func_c 0x1060-0x1067
  .rdata RVA 0x2000  "hello fixture" at 0x2000, vtable [a, b, c] at 0x2020, unwind info, import table
  .pdata RVA 0x3000  one RUNTIME_FUNCTION row per function
  .data  RVA 0x4000  a dword (0x2A) at 0x4000

func_a: push rbx; sub rsp,0x20; lea rcx,[rip->"hello fixture"]; call func_b; call [rip->IAT ExitProcess];
        add rsp,0x20; pop rbx; ret
func_b: mov eax,[rip->0x4000]; ret
func_c: xor eax,eax; jmp func_b          (a tail call: E9 rel32)
"""
import struct

IMAGE_BASE = 0x140000000
TEXT_RVA, RDATA_RVA, PDATA_RVA, DATA_RVA = 0x1000, 0x2000, 0x3000, 0x4000
FUNC_A, FUNC_A_END = 0x1000, 0x101D
FUNC_B, FUNC_B_END = 0x1040, 0x1047
FUNC_C, FUNC_C_END = 0x1060, 0x1067
STRING_RVA = 0x2000
STRING = b"hello fixture"
VTABLE_RVA = 0x2020
UNWIND_A, UNWIND_LEAF = 0x2040, 0x2050
IMPORT_DESC, ILT, IAT, HINTNAME, DLLNAME = 0x2060, 0x2090, 0x20A0, 0x20B0, 0x20C0
DATA_DWORD = 0x4000
TIMESTAMP = 0x5EED1234
# Expected sites (RVA of the instruction start).
SITE_LEA = 0x1005        # lea rcx, [rip + ...] -> STRING_RVA
SITE_CALL_B = 0x100C     # call func_b
SITE_CALL_IAT = 0x1011   # call qword ptr [rip + ...] -> IAT
SITE_MOV_DATA = 0x1040   # mov eax, dword ptr [rip + ...] -> DATA_DWORD
SITE_JMP_B = 0x1062      # jmp func_b


def _rel32(src_next, dst):
    return struct.pack("<i", dst - src_next)


def text_bytes():
    t = bytearray(b"\xCC" * 0x200)
    a = bytearray()
    a += b"\x53"                                            # 0x1000 push rbx
    a += b"\x48\x83\xEC\x20"                                # 0x1001 sub rsp, 0x20
    a += b"\x48\x8D\x0D" + _rel32(0x100C, STRING_RVA)       # 0x1005 lea rcx, [rip+..]
    a += b"\xE8" + _rel32(0x1011, FUNC_B)                   # 0x100C call func_b
    a += b"\xFF\x15" + _rel32(0x1017, IAT)                  # 0x1011 call [rip+..]
    a += b"\x48\x83\xC4\x20"                                # 0x1017 add rsp, 0x20
    a += b"\x5B"                                            # 0x101B pop rbx
    a += b"\xC3"                                            # 0x101C ret
    assert len(a) == FUNC_A_END - FUNC_A
    t[0:len(a)] = a
    b = b"\x8B\x05" + _rel32(0x1046, DATA_DWORD) + b"\xC3"  # 0x1040 mov eax, [rip+..]; ret
    t[0x40:0x40 + len(b)] = b
    c = b"\x31\xC0" + b"\xE9" + _rel32(0x1067, FUNC_B)      # 0x1060 xor eax,eax; jmp func_b
    t[0x60:0x60 + len(c)] = c
    return bytes(t)


def rdata_bytes():
    r = bytearray(0x200)

    def put(rva, blob):
        o = rva - RDATA_RVA
        r[o:o + len(blob)] = blob

    put(STRING_RVA, STRING + b"\0")
    put(VTABLE_RVA, struct.pack("<3Q", IMAGE_BASE + FUNC_A, IMAGE_BASE + FUNC_B, IMAGE_BASE + FUNC_C))
    # UNWIND_INFO for func_a: version 1, prolog 5 bytes, 2 codes: alloc small 0x20 at +5, push rbx at +1.
    put(UNWIND_A, bytes([0x01, 0x05, 0x02, 0x00, 0x05, 0x32, 0x01, 0x30]))
    put(UNWIND_LEAF, bytes([0x01, 0x00, 0x00, 0x00]))
    put(IMPORT_DESC, struct.pack("<5I", ILT, 0, 0, DLLNAME, IAT))   # then 20 zero bytes terminate the list
    put(ILT, struct.pack("<2Q", HINTNAME, 0))
    put(IAT, struct.pack("<2Q", HINTNAME, 0))
    put(HINTNAME, b"\0\0ExitProcess\0")
    put(DLLNAME, b"KERNEL32.dll\0")
    return bytes(r)


def pdata_bytes():
    p = bytearray(0x200)
    rows = [(FUNC_A, FUNC_A_END, UNWIND_A), (FUNC_B, FUNC_B_END, UNWIND_LEAF), (FUNC_C, FUNC_C_END, UNWIND_LEAF)]
    for i, row in enumerate(rows):
        p[i * 12:(i + 1) * 12] = struct.pack("<3I", *row)
    return bytes(p), len(rows) * 12


def build() -> bytes:
    text = text_bytes()
    rdata = rdata_bytes()
    pdata, pdata_size = pdata_bytes()
    data = struct.pack("<I", 0x2A) + b"\0" * (0x200 - 4)

    dos = bytearray(0x40)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, 0x40)

    coff = struct.pack("<HHIIIHH", 0x8664, 4, TIMESTAMP, 0, 0, 240, 0x0022)
    dirs = [(0, 0)] * 16
    dirs[1] = (IMPORT_DESC, 40)                 # import directory
    dirs[3] = (PDATA_RVA, pdata_size)           # exception directory
    dirs[12] = (IAT, 16)                        # IAT
    opt = struct.pack(
        "<HBBIIIII" "Q" "II" "HHHHHH" "IIII" "HH" "QQQQ" "II",
        0x20B, 14, 0, 0x200, 0x400, 0, FUNC_A, TEXT_RVA,
        IMAGE_BASE,
        0x1000, 0x200,
        6, 0, 0, 0, 6, 0,
        0, 0x5000, 0x400, 0,
        3, 0x8160,
        0x100000, 0x1000, 0x100000, 0x1000,
        0, 16)
    opt += b"".join(struct.pack("<II", *d) for d in dirs)
    assert len(opt) == 240

    def sec(name, rva, raw_off, chars):
        return struct.pack("<8sIIIIIIHHI", name, 0x200, rva, 0x200, raw_off, 0, 0, 0, 0, chars)

    sections = (sec(b".text", TEXT_RVA, 0x400, 0x60000020)
                + sec(b".rdata", RDATA_RVA, 0x600, 0x40000040)
                + sec(b".pdata", PDATA_RVA, 0x800, 0x40000040)
                + sec(b".data", DATA_RVA, 0xA00, 0xC0000040))
    head = bytes(dos) + b"PE\0\0" + coff + opt + sections
    head += b"\0" * (0x400 - len(head))
    return head + text + rdata + pdata + data


def write(path) -> str:
    with open(path, "wb") as f:
        f.write(build())
    return str(path)


if __name__ == "__main__":
    import sys
    print(write(sys.argv[1] if len(sys.argv) > 1 else "fixture.exe"))
