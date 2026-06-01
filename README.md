# chalkobusf

A **NewtonScript source-code obfuscator** with nine transformation passes.  
Available as a Python CLI, an Io-language CLI, and a zero-dependency browser UI.

---

## Quick start

**Web UI** — paste code, pick passes, click *Obfuscate*:
```sh
python3 app.py          # opens http://127.0.0.1:5000 automatically
python3 app.py --port 8080
```

**Python CLI** — no extra packages required:
```sh
python3 run.py src/chalkobusf.ns              # all nine passes (default)
python3 run.py --preset medium src/foo.ns     # medium strength
python3 run.py --strip-comments --minify src/foo.ns
python3 run.py --all --stats src/foo.ns       # print size/pass stats
python3 run.py src/foo.ns -o obfuscated.ns    # write to file
cat src/foo.ns | python3 run.py --all
```

**Io language** (requires the `io` interpreter):
```sh
io run.io src/chalkobusf.ns
io run.io --preset medium src/foo.ns
io run.io --all --stats src/foo.ns   # size stats to stderr
io bench.io src/foo.ns               # per-pass timing and size table
io inspect.io src/foo.ns             # preview code after each cumulative pass
```

---

## Passes

| Flag | # | What it does |
|---|---|---|
| `--strip-comments`  | 1 | Remove `//` line and `/* */` block comments |
| `--minify`          | 2 | Collapse whitespace runs to a single space |
| `--encode-strings`  | 3 | Encode string literals as `Char(N) & Char(M) & …` chains |
| `--obfuscate-nums`  | 4 | Replace integers with `(a + b)` split expressions |
| `--rename-vars`     | 5 | Rename `local` variables to `_0xN` hex identifiers |
| `--add-junk`        | 6 | Prepend a rotating dead-code block |
| `--deep-nums`       | 7 | 3× nested number obfuscation (creates deep arithmetic trees) |
| `--obfuscate-nils`  | 8 | Replace standalone `nil` with `(0 > 1)` |
| `--obfuscate-bools` | 9 | Replace `true` with `(1 = 1)`, `false` with `(1 <> 1)` |

**Presets:**

| `--preset` | Passes enabled |
|---|---|
| `light`  | 1, 2, 5 — strip, minify, rename |
| `medium` | 1, 2, 4, 5, 8, 9 — + number/nil/bool obfuscation |
| `heavy`  | all nine (same as `--all`) |

---

## Example

Input:
```newtonscript
// greet the user
local name := "Newton";
local count := 42;
if count > 0 then
  Print("Hello, " & name);
```

Output (`--preset heavy`):
```
local _j := (0 + 0); if _j > 16384 then Print(Char(100)&Char(101)&Char(97)&Char(100));
local _0x0 := Char(78)&Char(101)&Char(119)&Char(116)&Char(111)&Char(110);
local _0x1 := (((((((2+2)+(2+2))+((2+2)+(2+2)))+(((2+2)+(2+2))+((2+2)+(2+2))))+ ...)));
if _0x1 > (0+0) then Print(Char(72)&Char(101)&Char(108)&Char(108)&Char(111)&...&_0x0);
```

---

## Running tests

```sh
python3 tests/basic.py   # 30 assertions — no extra interpreter needed
io tests/basic.io        # 41 assertions — requires the Io interpreter
```

---

## Build a standalone executable

```sh
pip install pyinstaller
pyinstaller --onefile --name chalkobusf run.py
./dist/chalkobusf --all src/chalkobusf.ns
```

---

## Implementations

Three implementations that produce **byte-identical output**:

| File | Language | Notes |
|---|---|---|
| `src/chalkobusf.ns` | NewtonScript | Reference implementation |
| `src/chalkobusf.io` | Io language | Cleanest port — `s at(i)` returns char codes directly |
| `run.py` | Python 3 | CLI + web UI backend; no extra dependencies |

See [`CLAUDE.md`](CLAUDE.md) for full codebase documentation.
