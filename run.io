#!/usr/bin/env io
// run.io — Io CLI runner for chalkobusf
//
// Obfuscate NewtonScript source from the command line using the native Io
// implementation in src/chalkobusf.io.
//
// Usage:
//   io run.io [passes] [FILE] [-o OUTPUT]
//
// Pass flags (default: --all):
//   --strip-comments    Pass 1 — remove // and /* */ comments
//   --minify            Pass 2 — collapse whitespace runs to a single space
//   --encode-strings    Pass 3 — replace string literals with Char() chains
//   --obfuscate-nums    Pass 4 — replace integers with (a + b) split expressions
//   --rename-vars       Pass 5 — rename locals to _0xN generated names
//   --add-junk          Pass 6 — prepend rotating dead-code block
//   --deep-nums         Pass 7 — 3 rounds of number obfuscation (nested trees)
//   --obfuscate-nils    Pass 8 — replace nil with (0 > 1)
//   --obfuscate-bools   Pass 9 — replace true/(1=1) and false/(1<>1)
//   --all               enable all nine passes (used when no pass flag given)
//
// Examples:
//   io run.io src/chalkobusf.ns
//   io run.io --strip-comments --minify src/chalkobusf.ns
//   io run.io src/chalkobusf.ns -o out.ns
//   cat src/chalkobusf.ns | io run.io --all

doRelativeFile("src/chalkobusf.io")

flagKeys := Map clone do(
    atPut("--strip-comments", "stripComments")
    atPut("--minify",         "minifySpace")
    atPut("--encode-strings", "encodeStrings")
    atPut("--obfuscate-nums", "obfuscateNums")
    atPut("--rename-vars",    "renameVars")
    atPut("--add-junk",       "addJunk")
    atPut("--deep-nums",      "deepNums")
    atPut("--obfuscate-nils",  "obfuscateNils")
    atPut("--obfuscate-bools", "obfuscateBools")
)

args := System args  // first element is the script path; skip it
opts := Map clone
inputPath  := nil
outputPath := nil
useAll     := false
explicit   := false

i := 1
while(i < args size,
    a := args at(i)
    if(a == "--all",
        useAll = true,
        if((a == "-o") or (a == "--output"),
            (
                i = i + 1
                if(i < args size, outputPath = args at(i))
            ),
            if(flagKeys hasKey(a),
                (
                    opts atPut(flagKeys at(a), true)
                    explicit = true
                ),
                if((a == "-h") or (a == "--help"),
                    (
                        writeln("usage: io run.io [passes] [FILE] [-o OUTPUT]")
                        writeln("passes: --strip-comments --minify --encode-strings --obfuscate-nums")
                        writeln("        --rename-vars --add-junk --deep-nums --obfuscate-nils")
                        writeln("        --obfuscate-bools --all")
                        System exit(0)
                    ),
                    inputPath = a
                )
            )
        )
    )
    i = i + 1
)

if(useAll or (explicit not),
    opts = Map clone do(
        atPut("stripComments",  true)
        atPut("minifySpace",    true)
        atPut("encodeStrings",  true)
        atPut("obfuscateNums",  true)
        atPut("deepNums",       true)
        atPut("renameVars",     true)
        atPut("obfuscateNils",  true)
        atPut("obfuscateBools", true)
        atPut("addJunk",        true)
    )
)

source := if(inputPath isNil,
    File standardInput readLines join("\n"),
    File with(inputPath) contents
)

out := chalkobusf obfuscate(source, opts)

if(outputPath isNil,
    write(out),
    File with(outputPath) open write(out) close
)
