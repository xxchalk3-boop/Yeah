#!/usr/bin/env io
// inspect.io — show code after each cumulative obfuscation pass
//
// Run with:   io inspect.io [FILE]
//             cat src.ns | io inspect.io
//
// Applies each pass to the running result in pipeline order and prints a
// 100-character preview plus the byte-delta after every step.  Useful for
// understanding what each pass contributes and for debugging pass ordering.
//
// Example:
//   io inspect.io src/chalkobusf.ns
//   io inspect.io --from P3 src/chalkobusf.ns   (start from a specific pass)

doRelativeFile("src/chalkobusf.io")

// Collect args: optional --from PASS_NUMBER, then optional FILE
args      := System args
fromPass  := 1
inputPath := nil

i := 1
while(i < args size,
    a := args at(i)
    if(a == "--from",
        (
            i = i + 1
            if(i < args size, fromPass = args at(i) asNumber)
        ),
        inputPath = a
    )
    i = i + 1
)

src := if(inputPath isNil,
    File standardInput readLines join("\n"),
    File with(inputPath) contents
)

passOrder := list(
    list("stripComments",  "P1  Strip comments"),
    list("minifySpace",    "P2  Minify whitespace"),
    list("encodeStrings",  "P3  Encode strings"),
    list("obfuscateNums",  "P4  Obfuscate numbers"),
    list("renameVars",     "P5  Rename locals"),
    list("addJunk",        "P6  Inject junk"),
    list("deepNums",       "P7  Deep number obfuscation"),
    list("obfuscateNils",  "P8  Obfuscate nils"),
    list("obfuscateBools", "P9  Obfuscate booleans")
)

writeln("═══════════════════════════════════════════════════════")
writeln("  chalkobusf inspect" .. if(inputPath isNil, "", "  —  " .. inputPath))
writeln("═══════════════════════════════════════════════════════")
writeln("  input: " .. src size .. " bytes")
writeln("")

current  := src
passNum  := 1
passOrder foreach(p,
    key  := p at(0)
    name := p at(1)

    if(passNum >= fromPass,
        (
            opts    := Map clone atPut(key, true)
            next    := chalkobusf obfuscate(current, opts)
            delta   := next size - current size
            sign    := if(delta >= 0, "+", "")
            preview := if(next size > 100, next exSlice(0, 100) .. " …", next)

            writeln("─── " .. name .. "  (" .. sign .. delta .. " bytes → " .. next size .. " total) ───")
            writeln(preview)
            writeln("")
            current = next
        ),
        writeln("(skipping " .. name .. ")")
    )
    passNum = passNum + 1
)

writeln("═══════════════════════════════════════════════════════")
writeln("  final: " .. current size .. " bytes")
writeln("═══════════════════════════════════════════════════════")
