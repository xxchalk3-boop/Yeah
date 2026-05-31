#!/usr/bin/env python3
"""
Basic smoke tests for chalkobusf — Python port.

Run with:   python3 tests/basic.py   (from the repo root)

Assertions are explicit: each `check` compares actual vs expected and
tracks failures. A non-zero exit code means at least one test failed.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import _Chalkobusf

failures = 0
checks = 0


def check(label, got, want):
    global failures, checks
    checks += 1
    if got == want:
        print("PASS  " + label)
    else:
        failures += 1
        print("FAIL  " + label)
        print("        got:  " + repr(got))
        print("        want: " + repr(want))


c = _Chalkobusf()

# ── Pass 1: strip_comments ────────────────────────────────────────────────────
check("P1 line+block comments removed",
      c.strip_comments('local x := 1; // comment\n/* block */ local y := 2;'),
      'local x := 1; \n local y := 2;')
check("P1 string with // preserved",
      c.strip_comments('Print("http://x");'),
      'Print("http://x");')
check("P1 escaped quote does not end string early",
      c.strip_comments('a := "x\\"y"; // c'),
      'a := "x\\"y"; ')

# ── Pass 2: minify_whitespace ─────────────────────────────────────────────────
check("P2 collapse spaces",
      c.minify_whitespace("local   x  :=   1 ;"),
      "local x := 1 ;")
check("P2 collapse tabs",
      c.minify_whitespace("a\t\t\tb"),
      "a b")

# ── Pass 3: encode_strings ────────────────────────────────────────────────────
check("P3 empty string",
      c._encode_str(""),
      '""')
check("P3 encode_str Hi",
      c._encode_str("Hi"),
      "Char(72) & Char(105)")
check("P3 split Hello",
      c._split_and_encode("Hello"),
      "Char(72) & Char(101) & Char(108) & Char(108) & Char(111)")

# ── Pass 4: obfuscate_numbers ─────────────────────────────────────────────────
check("P4 42",  c._obfuscate_number(42),  "(21 + 21)")
check("P4 100", c._obfuscate_number(100), "(50 + 50)")
check("P4 hex name guard",
      c.obfuscate_numbers("local _0x1a := 5;"),
      "local _0x1a := (2 + 3);")

# ── Pass 5: rename_locals ─────────────────────────────────────────────────────
c._counter = 0
check("P5 rename + reference",
      c.rename_locals("local count := 1; Print(count);"),
      "local _0x0 := 1; Print(_0x0);")

# ── _gen_name hex sequence ────────────────────────────────────────────────────
c._counter = 0
check("genName _0x0",   c._gen_name(), "_0x0")
c._counter = 255
check("genName _0xff",  c._gen_name(), "_0xff")
c._counter = 256
check("genName _0x100", c._gen_name(), "_0x100")

# ── Pass 6: inject_junk rotation ─────────────────────────────────────────────
c._junk_phase = 0
check("P6 phase0 has _j",  "_j"  in c.inject_junk("x;"), True)
c._junk_phase = 1
check("P6 phase1 has _k",  "_k"  in c.inject_junk("x;"), True)
c._junk_phase = 2
check("P6 phase2 has nil", "nil" in c.inject_junk("x;"), True)
c._junk_phase = 3
check("P6 phase3 wraps",   "_j"  in c.inject_junk("x;"), True)

# ── Pass 7: deep_obfuscate_numbers ───────────────────────────────────────────
check("P7 nested 8",
      c.deep_obfuscate_numbers("8", 3),
      "(((1 + 1) + (1 + 1)) + ((1 + 1) + (1 + 1)))")

# ── Pass 8: obfuscate_nils ────────────────────────────────────────────────────
check("P8 nil replaced, nilCount kept",
      c.obfuscate_nils("local d := nil; local nilCount := 3;"),
      "local d := (0 > 1); local nilCount := 3;")
check("P8 nil inside string untouched",
      c.obfuscate_nils('Print("nil");'),
      'Print("nil");')
check("P8 nil after string processed",
      c.obfuscate_nils('Print("x"); local d := nil;'),
      'Print("x"); local d := (0 > 1);')

# ── Pass 9: obfuscate_booleans ────────────────────────────────────────────────
check("P9 true replaced",
      c.obfuscate_booleans("local x := true;"),
      "local x := (1 = 1);")
check("P9 false replaced",
      c.obfuscate_booleans("local x := false;"),
      "local x := (1 <> 1);")
check("P9 trueValue preserved",
      c.obfuscate_booleans("local trueValue := 1;"),
      "local trueValue := 1;")
check("P9 true inside string untouched",
      c.obfuscate_booleans('Print("true");'),
      'Print("true");')

# ── Full pipeline determinism ─────────────────────────────────────────────────
opts = {
    'stripComments': True, 'minifySpace':   True,
    'encodeStrings': True, 'obfuscateNums': True,
    'deepNums':      True, 'renameVars':    True,
    'obfuscateNils': True, 'addJunk':       True,
    'obfuscateBools': True,
}
src = '// c\nlocal w := 10;\nlocal flag := true;\nPrint("Area" & NumberStr(w));'
check("Full pipeline deterministic",
      c.obfuscate(src, opts),
      c.obfuscate(src, opts))

# ── Summary ───────────────────────────────────────────────────────────────────
print()
if failures == 0:
    print("All " + str(checks) + " tests passed.")
else:
    print(str(failures) + " of " + str(checks) + " tests FAILED.")
    sys.exit(1)
