"""Unit tests for the pecore helpers against the hand-built PE fixture (tests/make_pe.py).

Run: python -I -m pytest tests/  (or: python -I -m unittest discover -s tests)
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "skills", "re-tooling", "scripts"))

import make_pe  # noqa: E402
import pecore  # noqa: E402


class PEFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.path = tempfile.mkstemp(suffix=".exe")
        os.close(fd)
        make_pe.write(cls.path)
        cls.pe = pecore.PE(cls.path)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.path)

    def test_fixture_parses(self):
        import pefile
        pe = pefile.PE(data=make_pe.build())
        self.assertEqual([s.Name.rstrip(b"\0") for s in pe.sections],
                         [b".text", b".rdata", b".pdata", b".data"])

    def test_fingerprint(self):
        fp = pecore.fingerprint(self.path)
        self.assertEqual(fp["format"], "pe")
        self.assertEqual(fp["machine"], "0x8664")
        self.assertEqual(fp["image_base"], hex(make_pe.IMAGE_BASE))
        self.assertEqual(len(fp["sha256"]), 64)
        self.assertTrue(pecore.fingerprint_line(self.path).startswith("# bin"))

    def test_disasm_string_ref(self):
        ins = {d["rva"]: d for d in pecore.disasm(self.pe, make_pe.FUNC_A, 10)}
        lea = ins[make_pe.SITE_LEA]
        self.assertEqual(lea["mnemonic"], "lea")
        self.assertEqual(lea["target"], make_pe.STRING_RVA)
        self.assertEqual(lea["string"], "hello fixture")

    def test_func_bounds(self):
        fn = pecore.func_of(self.pe, make_pe.SITE_CALL_B)
        self.assertEqual(fn["begin"], make_pe.FUNC_A)
        self.assertEqual(fn["end"], make_pe.FUNC_A_END)
        # func_b is a separate .pdata row
        self.assertEqual(pecore.func_of(self.pe, make_pe.FUNC_B)["begin"], make_pe.FUNC_B)

    def test_callers_of_func_b(self):
        hits = pecore.callers(self.pe, make_pe.FUNC_B)
        sites = {h["rva"] for h in hits}
        self.assertIn(make_pe.SITE_CALL_B, sites)   # E8 call from func_a
        self.assertIn(make_pe.SITE_JMP_B, sites)    # E9 tail jmp from func_c
        call = next(h for h in hits if h["rva"] == make_pe.SITE_CALL_B)
        self.assertEqual(call["mnemonic"], "call")
        self.assertEqual(call["func"], make_pe.FUNC_A)

    def test_callees_of_func_a(self):
        c = pecore.callees(self.pe, make_pe.FUNC_A)
        self.assertIn(make_pe.FUNC_B, [d["target"] for d in c["direct"]])
        names = {d["name"] for d in c["imports"]}
        self.assertTrue(any(n.endswith("!ExitProcess") for n in names))

    def test_refs_vtable_pointers(self):
        r = pecore.code_refs(self.pe, make_pe.FUNC_A)
        ptr_rvas = {p["rva"] for p in r["pointers"]}
        self.assertIn(make_pe.VTABLE_RVA, ptr_rvas)   # slot 0 of the vtable holds &func_a

    def test_refs_rip_to_data(self):
        r = pecore.code_refs(self.pe, make_pe.DATA_DWORD)
        self.assertIn(make_pe.SITE_MOV_DATA, {h["rva"] for h in r["rip"]})

    def test_refs_vtable_holds_func_b(self):
        # "which vtable holds this function": func_b sits in slot 1 of the vtable at VTABLE_RVA
        r = pecore.code_refs(self.pe, make_pe.FUNC_B)
        self.assertIn(make_pe.VTABLE_RVA + 8, {p["rva"] for p in r["pointers"]})

    def test_refs_iat_callers(self):
        # "IAT refs": the call [rip->IAT] site references the ExitProcess slot
        r = pecore.code_refs(self.pe, make_pe.IAT)
        self.assertIn(make_pe.SITE_CALL_IAT, {h["rva"] for h in r["rip"]})

    def test_strings(self):
        out = pecore.strings(self.pe, "fixture")
        self.assertEqual(out[0]["rva"], make_pe.STRING_RVA)
        self.assertEqual(out[0]["text"], "hello fixture")

    def test_imports(self):
        imap = pecore.import_map(self.pe)
        self.assertIn(make_pe.IAT, imap)
        self.assertEqual(imap[make_pe.IAT], "KERNEL32.dll!ExitProcess")

    def test_parse_addr(self):
        self.assertEqual(pecore.parse_addr("0x1000"), 0x1000)
        self.assertEqual(pecore.parse_addr("1000"), 0x1000)
        self.assertEqual(pecore.parse_addr("va:0x140001000", self.pe), 0x1000)


if __name__ == "__main__":
    unittest.main()
