#!/usr/bin/env io
// bench.io — per-pass timing and size benchmark for chalkobusf
//
// Run with:   io bench.io [FILE]
// Default target: src/chalkobusf.ns
//
// Each pass is run in isolation on the original source, then all nine passes
// together.  Times are wall-clock milliseconds measured with Date.
//
// Example output:
//   chalkobusf bench — src/chalkobusf.ns
//   source: 16617 bytes
//
//   pass                        out(B)    pct     time
//   ─────────────────────────────────────────────────────
//   P1  stripComments           14201     85%     1ms
//   …

doRelativeFile("src/chalkobusf.io")

targetFile := if(System args size > 1, System args at(1), "src/chalkobusf.ns")
src        := File with(targetFile) contents
srcSize    := src size

writeln("chalkobusf bench — " .. targetFile)
writeln("source: " .. srcSize .. " bytes")
writeln("")
writeln("pass                        out(B)    pct     time")
writeln("─────────────────────────────────────────────────────")

passSpecs := list(
    list("P1  stripComments",        Map clone atPut("stripComments",  true)),
    list("P2  minifyWhitespace",     Map clone atPut("minifySpace",    true)),
    list("P3  encodeStrings",        Map clone atPut("encodeStrings",  true)),
    list("P4  obfuscateNumbers",     Map clone atPut("obfuscateNums",  true)),
    list("P5  renameLocals",         Map clone atPut("renameVars",     true)),
    list("P6  injectJunk",           Map clone atPut("addJunk",        true)),
    list("P7  deepObfuscateNumbers", Map clone atPut("deepNums",       true)),
    list("P8  obfuscateNils",        Map clone atPut("obfuscateNils",  true)),
    list("P9  obfuscateBooleans",    Map clone atPut("obfuscateBools", true)),
    list("ALL all passes",           Map clone do(
        atPut("stripComments",  true); atPut("minifySpace",    true)
        atPut("encodeStrings",  true); atPut("obfuscateNums",  true)
        atPut("deepNums",       true); atPut("renameVars",     true)
        atPut("obfuscateNils",  true); atPut("obfuscateBools", true)
        atPut("addJunk",        true)
    ))
)

passSpecs foreach(spec,
    name    := spec at(0)
    opts    := spec at(1)
    t0      := Date now asNumber
    out     := chalkobusf obfuscate(src, opts)
    ms      := ((Date now asNumber - t0) * 1000) truncated
    outSize := out size
    pct     := if(srcSize > 0, (outSize / srcSize * 100) truncated, 100)
    writeln(name .. "  " .. outSize .. "  " .. pct .. "%  " .. ms .. "ms")
)
