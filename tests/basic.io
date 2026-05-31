#!/usr/bin/env io
// Basic smoke tests for chalkobusf — Io port
//
// Run with:   io tests/basic.io     (from the repo root)
//
// Assertions are explicit: each `check` compares actual vs expected and
// tracks failures. A non-zero exit code means at least one test failed.

doRelativeFile("../src/chalkobusf.io")

failures := 0
checks   := 0

check := method(label, got, want,
    checks = checks + 1
    if(got == want,
        writeln("PASS  " .. label),
        (
            failures = failures + 1
            writeln("FAIL  " .. label)
            writeln("        got:  " .. got)
            writeln("        want: " .. want)
        )
    )
)

// ── Pass 1: stripComments ────────────────────────────────────────────────────
check("P1 line+block comments removed",
    chalkobusf stripComments("local x := 1; // c\n/* b */ local y := 2;"),
    "local x := 1; \n local y := 2;")
check("P1 string with // preserved",
    chalkobusf stripComments("Print(\"http://x\");"),
    "Print(\"http://x\");")
check("P1 escaped quote does not end string early",
    chalkobusf stripComments("a := \"x\\\"y\"; // c"),
    "a := \"x\\\"y\"; ")

// ── Pass 2: minifyWhitespace ─────────────────────────────────────────────────
check("P2 collapse spaces", chalkobusf minifyWhitespace("local   x  :=   1 ;"), "local x := 1 ;")
check("P2 collapse tabs",   chalkobusf minifyWhitespace("a\t\t\tb"), "a b")

// ── Pass 3: encodeStrings ────────────────────────────────────────────────────
check("P3 empty string", chalkobusf encodeStr(""), "\"\"")
check("P3 encodeStr Hi",  chalkobusf encodeStr("Hi"), "Char(72) & Char(105)")
check("P3 split Hello",   chalkobusf splitAndEncode("Hello"),
    "Char(72) & Char(101) & Char(108) & Char(108) & Char(111)")

// ── Pass 4: obfuscateNumbers ─────────────────────────────────────────────────
check("P4 42",  chalkobusf obfuscateNumber(42),  "(21 + 21)")
check("P4 100", chalkobusf obfuscateNumber(100), "(50 + 50)")
check("P4 hex name guard", chalkobusf obfuscateNumbers("local _0x1a := 5;"),
    "local _0x1a := (2 + 3);")

// ── Pass 5: renameLocals ─────────────────────────────────────────────────────
chalkobusf _counter = 0
check("P5 rename + reference", chalkobusf renameLocals("local count := 1; Print(count);"),
    "local _0x0 := 1; Print(_0x0);")

// ── genName hex sequence ─────────────────────────────────────────────────────
chalkobusf _counter = 0
check("genName _0x0", chalkobusf genName, "_0x0")
chalkobusf _counter = 255
check("genName _0xff", chalkobusf genName, "_0xff")
chalkobusf _counter = 256
check("genName _0x100", chalkobusf genName, "_0x100")

// ── Pass 6: injectJunk rotation ──────────────────────────────────────────────
chalkobusf _junkPhase = 0
check("P6 phase0 has _j", chalkobusf injectJunk("x;") containsSeq("_j"), true)
check("P6 phase1 has _k", chalkobusf injectJunk("x;") containsSeq("_k"), true)
check("P6 phase2 has nil", chalkobusf injectJunk("x;") containsSeq("nil"), true)
check("P6 phase3 wraps", chalkobusf injectJunk("x;") containsSeq("_j"), true)

// ── Pass 7: deepObfuscateNumbers ─────────────────────────────────────────────
check("P7 nested 8", chalkobusf deepObfuscateNumbers("8", 3),
    "(((2 + 2) + (2 + 2)) + ((2 + 2) + (2 + 2)))")

// ── Pass 8: obfuscateNils ────────────────────────────────────────────────────
check("P8 nil replaced, nilCount kept",
    chalkobusf obfuscateNils("local d := nil; local nilCount := 3;"),
    "local d := (0 > 1); local nilCount := 3;")
check("P8 nil inside string untouched",
    chalkobusf obfuscateNils("Print(\"nil\");"),
    "Print(\"nil\");")

// ── Full pipeline determinism ────────────────────────────────────────────────
opts := Map clone do(
    atPut("stripComments", true); atPut("minifySpace", true)
    atPut("encodeStrings", true); atPut("obfuscateNums", true)
    atPut("deepNums", true);      atPut("renameVars", true)
    atPut("obfuscateNils", true); atPut("addJunk", true)
)
src := "// c\nlocal w := 10;\nPrint(\"Area\" & NumberStr(w));"
check("Full pipeline deterministic",
    chalkobusf obfuscate(src, opts), chalkobusf obfuscate(src, opts))

// ── Summary ──────────────────────────────────────────────────────────────────
writeln("")
if(failures == 0,
    writeln("All " .. checks .. " tests passed."),
    (
        writeln(failures .. " of " .. checks .. " tests FAILED.")
        System exit(1)
    )
)
