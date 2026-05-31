# chalkobusf — Codebase Guide

## What this project is

`chalkobusf` is a NewtonScript source-code obfuscator. It takes a string of NewtonScript source and runs it through up to nine transformation passes, returning obfuscated source that is semantically equivalent but hard to read.

The obfuscator exists in **three implementations that produce byte-identical output**:

1. **NewtonScript** (`src/chalkobusf.ns`) — the original reference implementation.
2. **Io** (`src/chalkobusf.io`) — a native [Io language](https://iolanguage.org) port; the cleanest of the three because Io's `seq at(i)` returns a character code directly, so the NS idiom `Ord(SubStr(s, i, 1))` collapses to `src at(i)`.
3. **Python** (`run.py`) — the CLI runner and the basis of the standalone executable.

The codebase files:

```
src/chalkobusf.ns   — the obfuscator (single frame object, NewtonScript)
src/chalkobusf.io   — the obfuscator, native Io port (single Object clone)
tests/basic.ns      — NewtonScript smoke tests (one per pass + full pipeline)
tests/basic.io      — Io test suite, 28 explicit assertions (run: io tests/basic.io)
tests/basic.py      — Python test suite, 28 explicit assertions (run: python3 tests/basic.py)
run.py              — Python CLI runner (faithful port of the NS logic)
run.io              — Io CLI runner (same flags as run.py)
.gitignore          — excludes PyInstaller build artifacts (dist/, build/, *.spec)
```

**Equivalence is verified, not assumed.** The Io and Python runners are cross-checked to produce identical output byte-for-byte across every pass and the full pipeline, including on the obfuscator's own 14 KB source. If you change one implementation, change the others to match and re-run the cross-check (see *Running tests*).

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

## Io language primer

Io is a prototype-based, message-passing language. Everything is a message sent to a receiver. Key syntax as used in `src/chalkobusf.io`:

| Construct | Syntax | Notes |
|---|---|---|
| New slot / variable | `x := value` | `setSlot` |
| Reassign existing | `x = value` | `updateSlot` (searches proto chain) |
| Object / prototype | `Obj := Object clone do( … )` | slots defined inside `do(...)` |
| Method | `m := method(a, b, body…)` | last expression is the return value |
| Method call | `obj m(arg)` or `self m(arg)` | parens optional for zero args |
| Conditional | `if(cond, thenExpr, elseExpr)` | nest for `else if`; multi-statement branches wrapped in `( … )` |
| While | `while(cond, body…)` | |
| Infinite loop | `loop( … break )` | used for the repeat-until in `genName` |
| String concat | `a .. b` | |
| Char code at index | `s at(i)` | **returns a Number** — replaces NS `Ord(SubStr(s,i,1))` |
| Code → 1-char string | `code asCharacter` | |
| Substring | `s exSlice(start, end)` | end-exclusive; replaces NS `SubStr` |
| String length | `s size` | |
| Number → string | `n asString` | integers print without a decimal point |
| Integer division | `(a / b) floor` | `/` is float division |
| Modulo | `a % b` | |
| List | `list()`, `l append(x)`, `l at(i)`, `l size` | used for the rename `mappings` |
| Map (opts) | `Map clone atPut(k, v)`, `m at(k)`, `m hasKey(k)` | missing key → `nil` |
| Nil / false | `nil`, `false` | both falsy in `if`; everything else truthy |
| Boolean | `a and b`, `a or b`, `x not`, `x isNil` | |

The `chalkobusf` Io object is a single `Object clone do( … )` with the same two mutable state slots (`_counter`, `_junkPhase`) and the same method names (camelCased: `stripComments`, `obfuscateNumbers`, …) as the NS frame.

---

## The nine obfuscation passes

Passes are applied in this fixed order inside `chalkobusf:Obfuscate(code, opts)`:

| # | Slot key | Function | What it does |
|---|---|---|---|
| 1 | `stripComments` | `StripComments` | Removes `//` line comments and `/* */` block comments; skips string literals verbatim (escape-aware) |
| 2 | `minifySpace` | `MinifyWhitespace` | Collapses every run of whitespace to a single space |
| 3 | `encodeStrings` | `EncodeStrings` | Replaces `"literal"` with a `Char(N) & Char(M) & …` chain; splits each string at its midpoint for extra noise; handles `\"` and `\\` escape sequences |
| 4 | `obfuscateNums` | `ObfuscateNumbers` | Replaces integer `N` with `(a + b)` where `a = N div 2`, `b = N - a`; skips digit runs that follow an identifier character so generated names like `_0x1a` are never corrupted |
| 5 | `renameVars` | `RenameLocals` | Renames every `local` variable to a `_0xN` hex-style identifier; scans declarations first, then rewrites references via the same `mappings` array |
| 6 | `addJunk` | `InjectJunk` | Prepends one of three rotating dead-code snippets (unreachable `Print`, never-running `while`, always-skipped `if nil`) |
| 7 | `deepNums` | `DeepObfuscateNumbers` | Runs `ObfuscateNumbers` three times so numbers become nested arithmetic trees: `42 → (21+21) → ((10+11)+(10+11)) → …` |
| 8 | `obfuscateNils` | `ObfuscateNils` | Replaces every standalone `nil` token with `(0 > 1)` — semantically identical but unreadable; skips string literals and partial identifiers like `nilCount` |
| 9 | `obfuscateBools` | `ObfuscateBooleans` | Replaces standalone `true` with `(1 = 1)` and `false` with `(1 <> 1)`; skips string literals and partial identifiers like `trueValue` |

**Order matters.** Pass 7 (`deepNums`) runs after pass 4 so it can further nest the `(a + b)` expressions that pass 4 introduced. Passes 8 and 9 run after pass 5 so renamed `_0xN` variables are not affected. Pass 6 (`addJunk`) is always last since it prepends new code that should not be transformed. The full safe sequence is passes 1 → 9.

Each pass is also callable in isolation (`chalkobusf:StripComments(src)`, etc.).

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

  // Passes 1–9
  StripComments, MinifyWhitespace,
  EncodeStr, SplitAndEncode, EncodeStrings,
  ObfuscateNumber, ObfuscateNumbers,
  RenameLocals,
  MakeJunk, InjectJunk,
  DeepObfuscateNumbers,
  ObfuscateNils,
  ObfuscateBooleans,

  // Entry point
  Obfuscate,           // resets state, applies selected passes in order
}
```

---

## Entry point API

NewtonScript:
```newtonscript
local opts := {
  stripComments: true, minifySpace:    true,
  encodeStrings: true, obfuscateNums:  true,
  deepNums:      true, renameVars:     true,
  obfuscateNils: true, obfuscateBools: true,
  addJunk:       true,
};
local result := chalkobusf:Obfuscate(sourceCode, opts);
```

Io (opts is a `Map`):
```io
opts := Map clone do(
  atPut("stripComments",  true); atPut("minifySpace",    true)
  atPut("encodeStrings",  true); atPut("obfuscateNums",  true)
  atPut("deepNums",       true); atPut("renameVars",     true)
  atPut("obfuscateNils",  true); atPut("obfuscateBools", true)
  atPut("addJunk",        true)
)
result := chalkobusf obfuscate(sourceCode, opts)
```

Any key absent or set to `nil` skips that pass. Truthy value (including `true`) enables it.

`Obfuscate` resets `_counter` and `_junkPhase` to 0 at the start of each call, so repeated calls are deterministic.

---

## Running the obfuscator

There are two interchangeable command-line runners — `run.py` (Python) and `run.io` (Io). **They accept the same flags and produce identical output.** No Newton environment is required for either.

**With Python** (no extra install needed):
```
python3 run.py src/chalkobusf.ns                        # all passes (default)
python3 run.py --strip-comments --minify src/chalkobusf.ns
python3 run.py src/chalkobusf.ns -o obfuscated.ns       # write to a file
cat src/chalkobusf.ns | python3 run.py --all            # read from stdin
```

**With Io** (requires the `io` interpreter — see below):
```
io run.io src/chalkobusf.ns                             # all passes (default)
io run.io --strip-comments --minify src/chalkobusf.ns
io run.io src/chalkobusf.ns -o obfuscated.ns
cat src/chalkobusf.ns | io run.io --all
```

There is no Io package in apt/pip; build the interpreter from source (a few minutes):
```
git clone --depth 1 https://github.com/IoLanguage/io.git
cd io && mkdir build && cd build && cmake .. && make -j4
# binary lands at  build/_build/binaries/io
```

**Available flags** (omitting all flags enables `--all`):

| Flag | Pass |
|---|---|
| `--strip-comments` | 1 — remove `//` and `/* */` comments |
| `--minify` | 2 — collapse whitespace |
| `--encode-strings` | 3 — encode string literals as `Char()` chains |
| `--obfuscate-nums` | 4 — split integers into `(a + b)` |
| `--rename-vars` | 5 — rename locals to `_0xN` names |
| `--add-junk` | 6 — prepend dead-code block |
| `--deep-nums` | 7 — 3 rounds of number obfuscation (nested trees) |
| `--obfuscate-nils` | 8 — replace `nil` tokens with `(0 > 1)` |
| `--obfuscate-bools` | 9 — replace `true`/`(1=1)` and `false`/`(1<>1)` |
| `--all` | all nine passes |

---

## Building a standalone executable

`run.py` can be bundled into a single self-contained binary (no Python installation required) using [PyInstaller](https://pyinstaller.org):

```
pip install pyinstaller
pyinstaller --onefile --name chalkobusf run.py
```

The binary is written to `dist/chalkobusf` (Linux/macOS) or `dist\chalkobusf.exe` (Windows). It accepts the same flags as the Python script:

```
./dist/chalkobusf src/chalkobusf.ns
./dist/chalkobusf --all src/chalkobusf.ns -o out.ns
cat src/chalkobusf.ns | ./dist/chalkobusf --strip-comments --minify
```

`dist/`, `build/`, and `*.spec` are listed in `.gitignore` — do not commit them.

---

## Running tests

**Python test suite** (no extra interpreter needed — 28 explicit assertions):
```
python3 tests/basic.py
```
Loads `run.py`'s `_Chalkobusf` class directly, exercises every pass with focused fixtures, checks `_gen_name` hex rollover and junk rotation, and verifies full-pipeline determinism. Exits non-zero if any assertion fails.

**Io test suite** (requires the `io` interpreter — 28 explicit assertions):
```
io tests/basic.io
```
Loads `src/chalkobusf.io`, exercises each pass with the same fixtures as the Python suite, and verifies full-pipeline determinism. Exits non-zero if any assertion fails.

**NS tests** (require a Newton environment or compatible interpreter):
```
Load("tests/basic.ns");
```
Loads `src/chalkobusf.ns` itself and exercises each pass, then the full pipeline. No assertion framework — wrong output or an exception means failure.

**Cross-implementation check** (proves Io ≡ Python byte-for-byte). Run each flag through both runners and diff:
```
for p in --strip-comments --minify --encode-strings --obfuscate-nums \
         --rename-vars --add-junk --deep-nums --obfuscate-nils \
         --obfuscate-bools --all; do
  cmp -s <(python3 run.py $p src/chalkobusf.ns) \
         <(io run.io $p src/chalkobusf.ns) && echo "MATCH $p" || echo "DRIFT $p"
done
```
Any `DRIFT` means the implementations diverged — fix before committing.

---

## String escape handling

The string scanners in passes 1 and 3 handle `\"` (escaped quote) and `\\` (escaped backslash). When a `\` is seen inside a string literal, the following character is consumed as part of the string without being treated as a terminator. Other `\x` sequences pass through as-is.

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

A new pass must land in **all three implementations** so they stay byte-identical. For each of `src/chalkobusf.ns`, `src/chalkobusf.io`, and `run.py`:

1. Add the new pass method (NS frame slot with trailing comma / Io `method` inside `do(...)` / Python method).
2. Add a corresponding `opts` key and document it in the header comment block.
3. Add the `if opts.yourKey then result := self:YourPass(result);` (or the Io / Python equivalent) line in `Obfuscate`/`obfuscate`, in the intended pipeline position.
4. For `run.py`, also add the `--your-flag` argparse entry and wire it into the `opts` dict and the `explicit`/`use_all` logic.

Then add a fixture to both `tests/basic.py` and `tests/basic.io`, run both test suites, and run the cross-implementation check (see *Running tests*) to confirm Io and Python still agree. Also add `--your-flag` to `run.io`'s `flagKeys` map and the `useAll` block.

---

## Branch layout

| Branch | Purpose |
|---|---|
| `claude/game-project-6I7bF` | Separate experiment; unrelated to the obfuscator |
| `claude/claude-md-docs-1mm5i` | Documentation work (current) |
