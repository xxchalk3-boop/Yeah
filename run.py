#!/usr/bin/env python3
"""
chalkobusf runner — obfuscate NewtonScript source from the command line.

Faithful Python port of src/chalkobusf.ns.  Reads source from a file or
stdin, applies the requested passes, and writes to stdout or a file.

Usage:
  python3 run.py [passes] [input] [-o output]

Pass flags (default: --all):
  --strip-comments   Pass 1 — remove // and /* */ comments
  --minify           Pass 2 — collapse whitespace runs to a single space
  --encode-strings   Pass 3 — replace string literals with Char() chains
  --obfuscate-nums   Pass 4 — replace integers with (a + b) split expressions
  --rename-vars      Pass 5 — rename locals to _0xN generated names
  --add-junk         Pass 6 — prepend rotating dead-code block
  --deep-nums        Pass 7 — 3 rounds of number obfuscation (nested trees)
  --obfuscate-nils   Pass 8 — replace nil with (0 > 1)
  --all              enable all eight passes (used when no pass flag given)

Examples:
  python3 run.py src/chalkobusf.ns
  python3 run.py --strip-comments --minify src/chalkobusf.ns
  python3 run.py src/chalkobusf.ns -o out.ns
  cat src/chalkobusf.ns | python3 run.py --all
"""

import argparse
import sys


class _Chalkobusf:

    def __init__(self):
        self._counter = 0
        self._junk_phase = 0

    # ── Utilities ──────────────────────────────────────────────────────────────

    def _is_ident_start(self, ch):
        c = ord(ch)
        return (65 <= c <= 90) or (97 <= c <= 122) or c == 95

    def _is_ident_char(self, ch):
        c = ord(ch)
        return (65 <= c <= 90) or (97 <= c <= 122) or (48 <= c <= 57) or c == 95

    def _is_digit(self, ch):
        return 48 <= ord(ch) <= 57

    def _is_whitespace(self, ch):
        return ord(ch) in (32, 9, 10, 13)

    def _parse_int(self, s):
        n = 0
        for ch in s:
            n = n * 10 + (ord(ch) - 48)
        return n

    def _gen_name(self):
        n = self._counter
        self._counter += 1
        tmp = n
        h = ""
        while True:
            d = tmp % 16
            h = ("abcdef"[d - 10] if d >= 10 else str(d)) + h
            tmp //= 16
            if tmp == 0:
                break
        return "_0x" + h

    def _find_mapping(self, mappings, name):
        for pair in mappings:
            if pair[0] == name:
                return pair[1]
        return None

    # ── Pass 1: Strip comments ─────────────────────────────────────────────────

    def strip_comments(self, code):
        result = ""
        i = 0
        n = len(code)
        while i < n:
            ch = code[i]
            if ch == '"':
                result += ch
                i += 1
                while i < n:
                    c = code[i]
                    result += c
                    i += 1
                    if c == '\\' and i < n:
                        result += code[i]
                        i += 1
                    elif c == '"':
                        break
            elif ch == '/' and i + 1 < n:
                nx = code[i + 1]
                if nx == '/':
                    i += 2
                    while i < n and ord(code[i]) != 10:
                        i += 1
                elif nx == '*':
                    i += 2
                    while i + 1 < n:
                        if code[i] == '*' and code[i + 1] == '/':
                            i += 2
                            break
                        i += 1
                else:
                    result += ch
                    i += 1
            else:
                result += ch
                i += 1
        return result

    # ── Pass 2: Collapse whitespace ────────────────────────────────────────────

    def minify_whitespace(self, code):
        result = ""
        was_space = False
        for ch in code:
            if self._is_whitespace(ch):
                if not was_space:
                    result += " "
                    was_space = True
            else:
                result += ch
                was_space = False
        return result

    # ── Pass 3: String encoding ────────────────────────────────────────────────

    def _encode_str(self, s):
        if not s:
            return '""'
        return " & ".join("Char(" + str(ord(c)) + ")" for c in s)

    def _split_and_encode(self, s):
        n = len(s)
        if n <= 1:
            return self._encode_str(s)
        mid = n // 2
        return self._encode_str(s[:mid]) + " & " + self._encode_str(s[mid:])

    def encode_strings(self, code):
        result = ""
        i = 0
        n = len(code)
        while i < n:
            ch = code[i]
            if ch == '"':
                content = ""
                i += 1
                while i < n:
                    c = code[i]
                    if c == '"':
                        i += 1
                        break
                    elif c == '\\' and i + 1 < n:
                        i += 1
                        esc = code[i]
                        content += esc if esc in ('"', '\\') else esc
                        i += 1
                    else:
                        content += c
                        i += 1
                result += self._split_and_encode(content)
            else:
                result += ch
                i += 1
        return result

    # ── Pass 4: Number obfuscation ─────────────────────────────────────────────

    def _obfuscate_number(self, n):
        a = n // 2
        return "(" + str(a) + " + " + str(n - a) + ")"

    def obfuscate_numbers(self, code):
        result = ""
        i = 0
        n = len(code)
        prev_was_ident = False
        while i < n:
            ch = code[i]
            if self._is_digit(ch) and not prev_was_ident:
                num_str = ""
                while i < n and self._is_digit(code[i]):
                    num_str += code[i]
                    i += 1
                result += self._obfuscate_number(self._parse_int(num_str))
                prev_was_ident = False
            else:
                result += ch
                prev_was_ident = self._is_ident_char(ch)
                i += 1
        return result

    # ── Pass 5: Variable renaming ──────────────────────────────────────────────

    def rename_locals(self, code):
        mappings = []
        output = ""
        i = 0
        n = len(code)
        while i < n:
            if i + 6 <= n and code[i:i + 6] == "local ":
                i += 6
                var_name = ""
                while i < n and self._is_ident_char(code[i]):
                    var_name += code[i]
                    i += 1
                mapped = self._find_mapping(mappings, var_name)
                if mapped is None:
                    mapped = self._gen_name()
                    mappings.append([var_name, mapped])
                output += "local " + mapped
            elif self._is_ident_start(code[i]):
                word = ""
                while i < n and self._is_ident_char(code[i]):
                    word += code[i]
                    i += 1
                mapped = self._find_mapping(mappings, word)
                output += mapped if mapped else word
            else:
                output += code[i]
                i += 1
        return output

    # ── Pass 6: Junk injection ─────────────────────────────────────────────────

    def _make_junk(self):
        p = self._junk_phase % 3
        self._junk_phase += 1
        if p == 0:
            return ('local _j := (0 + 0); if _j > 16384 then Print(' +
                    self._encode_str("dead") + '); ')
        elif p == 1:
            return 'local _k := 1; while _k < 0 do _k := _k + 1; '
        else:
            return 'if nil then begin local _z := (0 + 0); end; '

    def inject_junk(self, code):
        return self._make_junk() + code

    # ── Pass 7: Deep number obfuscation ───────────────────────────────────────

    def deep_obfuscate_numbers(self, code, rounds=3):
        result = code
        for _ in range(rounds):
            result = self.obfuscate_numbers(result)
        return result

    # ── Pass 8: Nil obfuscation ────────────────────────────────────────────────

    def obfuscate_nils(self, code):
        result = ""
        i = 0
        n = len(code)
        while i < n:
            ch = code[i]
            if ch == '"':
                result += ch
                i += 1
                while i < n:
                    c = code[i]
                    result += c
                    i += 1
                    if c == '\\' and i < n:
                        result += code[i]
                        i += 1
                    elif c == '"':
                        break
            elif code[i:i+3] == 'nil':
                before = i == 0 or not self._is_ident_char(code[i - 1])
                after  = i + 3 >= n or not self._is_ident_char(code[i + 3])
                if before and after:
                    result += '(0 > 1)'
                    i += 3
                else:
                    result += ch
                    i += 1
            else:
                result += ch
                i += 1
        return result

    # ── Main pipeline ──────────────────────────────────────────────────────────

    def obfuscate(self, code, opts):
        self._counter = 0
        self._junk_phase = 0
        result = code
        if opts.get('stripComments'):  result = self.strip_comments(result)
        if opts.get('minifySpace'):    result = self.minify_whitespace(result)
        if opts.get('encodeStrings'):  result = self.encode_strings(result)
        if opts.get('obfuscateNums'):  result = self.obfuscate_numbers(result)
        if opts.get('deepNums'):       result = self.deep_obfuscate_numbers(result)
        if opts.get('renameVars'):     result = self.rename_locals(result)
        if opts.get('obfuscateNils'):  result = self.obfuscate_nils(result)
        if opts.get('addJunk'):        result = self.inject_junk(result)
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Obfuscate NewtonScript source via chalkobusf.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[1],
    )
    parser.add_argument("input", nargs="?", metavar="FILE",
                        help="input .ns file (omit to read from stdin)")
    parser.add_argument("-o", "--output", metavar="FILE",
                        help="write output to FILE (default: stdout)")

    g = parser.add_argument_group("passes (default: --all)")
    g.add_argument("--all",             action="store_true",
                   help="enable all six passes")
    g.add_argument("--strip-comments",  action="store_true",
                   help="pass 1: strip // and /* */ comments")
    g.add_argument("--minify",          action="store_true",
                   help="pass 2: collapse whitespace")
    g.add_argument("--encode-strings",  action="store_true",
                   help="pass 3: encode string literals as Char() chains")
    g.add_argument("--obfuscate-nums",  action="store_true",
                   help="pass 4: split integers into (a + b) expressions")
    g.add_argument("--rename-vars",     action="store_true",
                   help="pass 5: rename local variables to _0xN names")
    g.add_argument("--add-junk",        action="store_true",
                   help="pass 6: prepend rotating dead-code block")
    g.add_argument("--deep-nums",       action="store_true",
                   help="pass 7: 3 rounds of number obfuscation (nested trees)")
    g.add_argument("--obfuscate-nils",  action="store_true",
                   help="pass 8: replace nil tokens with (0 > 1)")

    args = parser.parse_args()

    explicit = any([
        args.strip_comments, args.minify, args.encode_strings,
        args.obfuscate_nums, args.rename_vars, args.add_junk,
        args.deep_nums, args.obfuscate_nils,
    ])
    use_all = args.all or not explicit

    opts = {
        'stripComments': use_all or args.strip_comments,
        'minifySpace':   use_all or args.minify,
        'encodeStrings': use_all or args.encode_strings,
        'obfuscateNums': use_all or args.obfuscate_nums,
        'deepNums':      use_all or args.deep_nums,
        'renameVars':    use_all or args.rename_vars,
        'obfuscateNils': use_all or args.obfuscate_nils,
        'addJunk':       use_all or args.add_junk,
    }

    if args.input:
        try:
            with open(args.input, encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            sys.exit(f"error: {e}")
    else:
        source = sys.stdin.read()

    result = _Chalkobusf().obfuscate(source, opts)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
        except OSError as e:
            sys.exit(f"error: {e}")
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
