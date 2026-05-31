# chalkobusf — Codebase Guide

## What this project is

`chalkobusf` is a NewtonScript source-code obfuscator written entirely in NewtonScript. It takes a string of NewtonScript source and runs it through up to six transformation passes, returning obfuscated source that is semantically equivalent but hard to read.

The codebase has exactly two files:

```
src/chalkobusf.ns   — the obfuscator (single frame object)
tests/basic.ns      — smoke tests, one per pass + a full-pipeline test
```

---

## NewtonScript language primer

NewtonScript is a prototype-based language from the Apple Newton PDA. Key syntax:

| Construct | Syntax |
|---|---|
| Assignment | `x := value` |
| Frame (object/record) | `{ slot: value, method: func(a) begin … end }` |
| Method call | `self:Method(arg)` or `obj:Method(arg)` |
| Function | `func(a, b) begin … end` |
| Local variable | `local x := value;` |
| Integer division | `n div d` |
| Modulo | `n mod d` |
| String concat | `"a" & "b"` |
| Array | `[a, b, c]` |
| While | `while cond do begin … end` |
| Repeat-until | `repeat … until cond` |
| Nil / false | `nil` |
| Truthy | any non-nil value |

Built-in functions used here: `Ord(ch)`, `SubStr(s, start, len)`, `StrLen(s)`, `NumberStr(n)`, `Length(arr)`, `ArrayAddLast(arr, val)`, `Load(path)`, `Print(s)`.

---

## The six obfuscation passes

Passes are applied in this fixed order inside `chalkobusf:Obfuscate(code, opts)`:

| # | Slot key | Function | What it does |
|---|---|---|---|
| 1 | `stripComments` | `StripComments` | Removes `//` line comments and `/* */` block comments; skips string literals verbatim |
| 2 | `minifySpace` | `MinifyWhitespace` | Collapses every run of whitespace to a single space |
| 3 | `encodeStrings` | `EncodeStrings` | Replaces `"literal"` with a `Char(N) & Char(M) & …` chain; splits each string at its midpoint for extra noise |
| 4 | `obfuscateNums` | `ObfuscateNumbers` | Replaces integer `N` with `(a + b)` where `a = N div 2`, `b = N - a`; skips digit runs that follow an identifier character so generated names like `_0x1a` are never corrupted |
| 5 | `renameVars` | `RenameLocals` | Renames every `local` variable to a `_0xN` hex-style identifier; scans declarations first, then rewrites references via the same `mappings` array |
| 6 | `addJunk` | `InjectJunk` | Prepends one of three rotating dead-code snippets (unreachable `Print`, never-running `while`, always-skipped `if nil`) |

**Order matters.** Pass 4 must run after pass 5 OR after pass 3, not between them in a way that breaks generated names. As implemented, the pipeline is safe: passes 1–6 in sequence.

Each pass is also callable in isolation for testing (`chalkobusf:StripComments(src)`, etc.).

---

## Object structure

`chalkobusf` is a single NewtonScript frame with two mutable state slots and all methods as slots:

```
chalkobusf := {
  _counter:   0,       // incremented by GenName; reset to 0 on each Obfuscate call
  _junkPhase: 0,       // mod-3 phase for rotating junk patterns; reset on each call

  // Utilities
  IsIdentStart, IsIdentChar, IsDigit, IsWhitespace,
  ParseInt,            // decimal string → integer (no built-in parseInt in NS)
  GenName,             // returns _0x0, _0x1, _0x2, …
  FindMapping,         // linear search in [[oldName, newName], …]

  // Passes 1–6
  StripComments, MinifyWhitespace,
  EncodeStr, SplitAndEncode, EncodeStrings,
  ObfuscateNumber, ObfuscateNumbers,
  RenameLocals,
  MakeJunk, InjectJunk,

  // Entry point
  Obfuscate,           // resets state, applies selected passes in order
}
```

---

## Entry point API

```newtonscript
local opts := {
  stripComments: true,
  minifySpace:   true,
  encodeStrings: true,
  obfuscateNums: true,
  renameVars:    true,
  addJunk:       true,
};
local result := chalkobusf:Obfuscate(sourceCode, opts);
```

Any slot absent or set to `nil` skips that pass. Truthy value (including `true`) enables it.

`Obfuscate` resets `_counter` and `_junkPhase` to 0 at the start of each call, so repeated calls are deterministic.

---

## Running tests

```
Load("tests/basic.ns");
```

Run from the Newton environment or a compatible NS interpreter. The test file calls `Load("src/chalkobusf.ns")` itself. Each pass is exercised with a focused fixture, then the full pipeline runs on a multi-line snippet.

There is no test framework — assertions are implicit: if a pass throws or produces obviously wrong output, it fails.

---

## Conventions and constraints

- **No external dependencies.** Every character-level operation is built from `Ord`, `SubStr`, `StrLen`, `NumberStr`. Do not add imports.
- **No regex.** All scanning is a hand-written character-by-character loop. Match this style.
- **String safety in scanners.** Whenever a pass walks source characters, it must detect and skip over string literals verbatim (copy them as-is) to avoid mangling their contents. See how `StripComments` and `EncodeStrings` handle the `"` case.
- **No multi-pass mutation of state between passes.** Each pass is a pure string-in/string-out function; only `_counter` and `_junkPhase` are shared state, and both are reset by `Obfuscate`.
- **Identifier guard in number obfuscation.** The `prevWasIdent` flag in `ObfuscateNumbers` exists specifically to protect hex names like `_0x1f` generated by `RenameLocals`. Do not remove it.
- **Junk patterns must be syntactically valid NS.** Any new junk block added to `MakeJunk` must parse and execute cleanly (even if it does nothing). The rotation is `_junkPhase mod 3`; add a new pattern by changing the modulus.
- **NewtonScript frame comma discipline.** Every slot except the last must end with `,`. Missing or trailing commas are syntax errors.

---

## Adding a new pass

1. Add a new method slot to the `chalkobusf` frame with a comma after the previous last slot.
2. Add a corresponding `opts` key name (document it in the header comment block at the top of `chalkobusf.ns`).
3. Add an `if opts.yourKey then result := self:YourPass(result);` line in `Obfuscate`, in the intended pipeline position.
4. Add a focused test fixture in `tests/basic.ns`.

---

## Branch layout

| Branch | Purpose |
|---|---|
| `claude/game-project-6I7bF` | Separate experiment; unrelated to the obfuscator |
| `claude/claude-md-docs-1mm5i` | Documentation work (current) |
