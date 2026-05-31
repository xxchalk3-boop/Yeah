#!/usr/bin/env io
// chalkobusf — NewtonScript-source obfuscator, Io port
//
// This is a faithful port of src/chalkobusf.ns to the Io language
// (https://iolanguage.org). It takes a string of NewtonScript source and
// runs it through up to nine transformation passes, returning obfuscated
// source that is semantically equivalent but hard to read.
//
// Why Io reads cleaner than the NewtonScript original:
//   - `seq at(i)` returns the character code directly (a Number), so the
//     NS idiom `Ord(SubStr(s, i, 1))` collapses to `src at(i)`.
//   - `code asCharacter` turns a code back into a one-character string.
//   - `s exSlice(a, b)` is the substring primitive (start inclusive,
//     end exclusive), replacing `SubStr(s, start, len)`.
//
// Passes (in pipeline order):
//   1. stripComments        — remove // and /* */ comments
//   2. minifyWhitespace     — collapse whitespace runs to a single space
//   3. encodeStrings        — split string literals, encode halves as Char() chains
//   4. obfuscateNumbers     — replace integer literals with (a + b) split expressions
//   5. renameLocals         — rename local variables to _0xN generated names
//   6. injectJunk           — prepend rotating dead-code block
//   7. deepObfuscateNumbers — 3 rounds of pass 4 (nested arithmetic trees)
//   8. obfuscateNils        — replace standalone nil tokens with (0 > 1)
//   9. obfuscateBooleans    — replace true with (1 = 1), false with (1 <> 1)

chalkobusf := Object clone do(

    _counter   := 0
    _junkPhase := 0

    // ── Utilities ──────────────────────────────────────────────────────────
    // These take a character *code* (Number), since `seq at(i)` already
    // yields the code — no Ord() round-trip required.

    isIdentStart := method(c,
        (c >= 65 and c <= 90) or (c >= 97 and c <= 122) or (c == 95)
    )

    isIdentChar := method(c,
        (c >= 65 and c <= 90) or (c >= 97 and c <= 122) or
        (c >= 48 and c <= 57) or (c == 95)
    )

    isDigit := method(c, c >= 48 and c <= 57)

    isWhitespace := method(c, c == 32 or c == 9 or c == 10 or c == 13)

    // Parse a decimal digit string into a Number.
    parseInt := method(s,
        n := 0
        i := 0
        len := s size
        while(i < len,
            n = n * 10 + (s at(i) - 48)
            i = i + 1
        )
        n
    )

    // Generate the next obfuscated identifier: _0x0, _0x1, …, _0xff, _0x100, …
    genName := method(
        n := self _counter
        self _counter = self _counter + 1
        hex := ""
        tmp := n
        loop(
            digit := tmp % 16
            if(digit < 10,
                hex = (digit asString) .. hex,
                hex = ("abcdef" exSlice(digit - 10, digit - 9)) .. hex
            )
            tmp = (tmp / 16) floor
            if(tmp == 0, break)
        )
        "_0x" .. hex
    )

    // Search a list of [oldName, newName] pairs; return the mapped name or nil.
    findMapping := method(mappings, name,
        i := 0
        found := nil
        while((i < mappings size) and (found isNil),
            if((mappings at(i) at(0)) == name, found = mappings at(i) at(1))
            i = i + 1
        )
        found
    )

    // ── Pass 1: Strip comments ───────────────────────────────────────────────

    stripComments := method(src,
        result := ""
        i := 0
        len := src size
        while(i < len,
            ch := src at(i)
            if(ch == 34,
                (   // Copy string literal verbatim — do not strip inside it
                    result = result .. (ch asCharacter)
                    i = i + 1
                    done := false
                    while((i < len) and (done not),
                        c := src at(i)
                        result = result .. (c asCharacter)
                        i = i + 1
                        if(c == 92,
                            if(i < len,
                                (
                                    result = result .. (src at(i) asCharacter)
                                    i = i + 1
                                )
                            ),
                            if(c == 34, done = true)
                        )
                    )
                ),
                if((ch == 47) and (i + 1 < len),
                    (
                        nxt := src at(i + 1)
                        if(nxt == 47,
                            (   // line comment
                                i = i + 2
                                while((i < len) and (src at(i) != 10), i = i + 1)
                            ),
                            if(nxt == 42,
                                (   // block comment
                                    i = i + 2
                                    closed := false
                                    while((i + 1 < len) and (closed not),
                                        if((src at(i) == 42) and (src at(i + 1) == 47),
                                            (
                                                i = i + 2
                                                closed = true
                                            ),
                                            i = i + 1
                                        )
                                    )
                                ),
                                (   // lone slash
                                    result = result .. (ch asCharacter)
                                    i = i + 1
                                )
                            )
                        )
                    ),
                    (
                        result = result .. (ch asCharacter)
                        i = i + 1
                    )
                )
            )
        )
        result
    )

    // ── Pass 2: Collapse whitespace ──────────────────────────────────────────

    minifyWhitespace := method(src,
        result := ""
        i := 0
        len := src size
        wasSpace := false
        while(i < len,
            ch := src at(i)
            if(self isWhitespace(ch),
                if(wasSpace not,
                    (
                        result = result .. " "
                        wasSpace = true
                    )
                ),
                (
                    result = result .. (ch asCharacter)
                    wasSpace = false
                )
            )
            i = i + 1
        )
        result
    )

    // ── Pass 3: String encoding ──────────────────────────────────────────────

    // Encode one raw string as a Char() chain: Char(72) & Char(105) & …
    encodeStr := method(s,
        len := s size
        if(len == 0,
            "\"\"",
            (
                result := ""
                i := 0
                while(i < len,
                    code := s at(i)
                    if(i == 0,
                        result = "Char(" .. (code asString) .. ")",
                        result = result .. " & Char(" .. (code asString) .. ")"
                    )
                    i = i + 1
                )
                result
            )
        )
    )

    // Split s at its midpoint then encode each half separately for extra noise.
    splitAndEncode := method(s,
        len := s size
        if(len <= 1,
            self encodeStr(s),
            (
                mid := (len / 2) floor
                (self encodeStr(s exSlice(0, mid))) .. " & " .. (self encodeStr(s exSlice(mid, len)))
            )
        )
    )

    encodeStrings := method(src,
        result := ""
        i := 0
        len := src size
        while(i < len,
            ch := src at(i)
            if(ch == 34,
                (
                    strContent := ""
                    i = i + 1
                    done := false
                    while((i < len) and (done not),
                        c := src at(i)
                        if(c == 34,
                            (
                                done = true
                                i = i + 1
                            ),
                            if(c == 92,
                                (
                                    i = i + 1
                                    if(i < len,
                                        (
                                            esc := src at(i)
                                            if(esc == 34,
                                                strContent = strContent .. "\"",
                                                if(esc == 92,
                                                    strContent = strContent .. "\\",
                                                    strContent = strContent .. (esc asCharacter)
                                                )
                                            )
                                            i = i + 1
                                        )
                                    )
                                ),
                                (
                                    strContent = strContent .. (c asCharacter)
                                    i = i + 1
                                )
                            )
                        )
                    )
                    result = result .. (self splitAndEncode(strContent))
                ),
                (
                    result = result .. (ch asCharacter)
                    i = i + 1
                )
            )
        )
        result
    )

    // ── Pass 4: Number obfuscation ───────────────────────────────────────────

    // Replace integer N with (a + b) where a = N div 2, b = N - a.
    obfuscateNumber := method(n,
        a := (n / 2) floor
        b := n - a
        "(" .. (a asString) .. " + " .. (b asString) .. ")"
    )

    obfuscateNumbers := method(src,
        result := ""
        i := 0
        len := src size
        prevWasIdent := false
        while(i < len,
            ch := src at(i)
            // Only rewrite a digit run that does not follow an identifier char
            // (avoids breaking _0x1a-style generated names from earlier passes).
            if((self isDigit(ch)) and (prevWasIdent not),
                (
                    numStr := ""
                    while((i < len) and (self isDigit(src at(i))),
                        numStr = numStr .. (src at(i) asCharacter)
                        i = i + 1
                    )
                    result = result .. (self obfuscateNumber(self parseInt(numStr)))
                    prevWasIdent = false
                ),
                (
                    result = result .. (ch asCharacter)
                    prevWasIdent = self isIdentChar(ch)
                    i = i + 1
                )
            )
        )
        result
    )

    // ── Pass 5: Variable renaming ────────────────────────────────────────────

    renameLocals := method(src,
        mappings := list()
        output := ""
        i := 0
        len := src size
        while(i < len,
            if((i + 6 <= len) and (src exSlice(i, i + 6) == "local "),
                (
                    i = i + 6
                    varName := ""
                    while((i < len) and (self isIdentChar(src at(i))),
                        varName = varName .. (src at(i) asCharacter)
                        i = i + 1
                    )
                    mapped := self findMapping(mappings, varName)
                    if(mapped isNil,
                        (
                            mapped = self genName
                            mappings append(list(varName, mapped))
                        )
                    )
                    output = output .. "local " .. mapped
                ),
                if(self isIdentStart(src at(i)),
                    (
                        word := ""
                        while((i < len) and (self isIdentChar(src at(i))),
                            word = word .. (src at(i) asCharacter)
                            i = i + 1
                        )
                        wm := self findMapping(mappings, word)
                        if(wm isNil,
                            output = output .. word,
                            output = output .. wm
                        )
                    ),
                    (
                        output = output .. (src at(i) asCharacter)
                        i = i + 1
                    )
                )
            )
        )
        output
    )

    // ── Pass 6: Junk injection ───────────────────────────────────────────────

    // Three rotating dead-code patterns; cycles each time injectJunk is called.
    makeJunk := method(
        p := self _junkPhase % 3
        self _junkPhase = self _junkPhase + 1
        if(p == 0,
            "local _j := (0 + 0); if _j > 16384 then Print(" .. (self encodeStr("dead")) .. "); ",
            if(p == 1,
                "local _k := 1; while _k < 0 do _k := _k + 1; ",
                "if nil then begin local _z := (0 + 0); end; "
            )
        )
    )

    injectJunk := method(src, (self makeJunk) .. src)

    // ── Pass 7: Deep number obfuscation ──────────────────────────────────────

    // Run obfuscateNumbers multiple rounds so numbers become nested trees:
    //   42 → (21 + 21) → ((10 + 11) + (10 + 11))
    deepObfuscateNumbers := method(src, rounds,
        result := src
        i := 0
        while(i < rounds,
            result = self obfuscateNumbers(result)
            i = i + 1
        )
        result
    )

    // ── Pass 8: Nil obfuscation ──────────────────────────────────────────────

    // Replace every standalone nil token with (0 > 1) — always nil, unreadable.
    // Skips string literals and partial identifiers like nilCount.
    obfuscateNils := method(src,
        result := ""
        i := 0
        len := src size
        while(i < len,
            ch := src at(i)
            if(ch == 34,
                (
                    result = result .. (ch asCharacter)
                    i = i + 1
                    inStr := true
                    while((i < len) and inStr,
                        c := src at(i)
                        result = result .. (c asCharacter)
                        i = i + 1
                        if(c == 92,
                            if(i < len,
                                (
                                    result = result .. (src at(i) asCharacter)
                                    i = i + 1
                                )
                            ),
                            if(c == 34, inStr = false)
                        )
                    )
                ),
                if((i + 3 <= len) and (src exSlice(i, i + 3) == "nil"),
                    (
                        before := (i == 0) or (self isIdentChar(src at(i - 1)) not)
                        after  := (i + 3 >= len) or (self isIdentChar(src at(i + 3)) not)
                        if(before and after,
                            (
                                result = result .. "(0 > 1)"
                                i = i + 3
                            ),
                            (
                                result = result .. (ch asCharacter)
                                i = i + 1
                            )
                        )
                    ),
                    (
                        result = result .. (ch asCharacter)
                        i = i + 1
                    )
                )
            )
        )
        result
    )

    // ── Pass 9: Boolean obfuscation ──────────────────────────────────────────

    // Replace standalone true with (1 = 1) and false with (1 <> 1).
    // Skips string literals; guards against partial identifiers like trueValue.
    obfuscateBooleans := method(src,
        result := ""
        i := 0
        len := src size
        while(i < len,
            ch := src at(i)
            if(ch == 34,
                (
                    result = result .. (ch asCharacter)
                    i = i + 1
                    inStr := true
                    while((i < len) and inStr,
                        c := src at(i)
                        result = result .. (c asCharacter)
                        i = i + 1
                        if(c == 92,
                            if(i < len,
                                (
                                    result = result .. (src at(i) asCharacter)
                                    i = i + 1
                                )
                            ),
                            if(c == 34, inStr = false)
                        )
                    )
                ),
                if((i + 4 <= len) and (src exSlice(i, i + 4) == "true"),
                    (
                        before := (i == 0) or (self isIdentChar(src at(i - 1)) not)
                        after  := (i + 4 >= len) or (self isIdentChar(src at(i + 4)) not)
                        if(before and after,
                            (
                                result = result .. "(1 = 1)"
                                i = i + 4
                            ),
                            (
                                result = result .. (ch asCharacter)
                                i = i + 1
                            )
                        )
                    ),
                    if((i + 5 <= len) and (src exSlice(i, i + 5) == "false"),
                        (
                            before := (i == 0) or (self isIdentChar(src at(i - 1)) not)
                            after  := (i + 5 >= len) or (self isIdentChar(src at(i + 5)) not)
                            if(before and after,
                                (
                                    result = result .. "(1 <> 1)"
                                    i = i + 5
                                ),
                                (
                                    result = result .. (ch asCharacter)
                                    i = i + 1
                                )
                            )
                        ),
                        (
                            result = result .. (ch asCharacter)
                            i = i + 1
                        )
                    )
                )
            )
        )
        result
    )

    // ── Main pipeline ────────────────────────────────────────────────────────

    // opts is a Map; set any key to true to enable that pass (absent/nil skips):
    //   stripComments, minifySpace, encodeStrings, obfuscateNums,
    //   deepNums, renameVars, obfuscateNils, obfuscateBools, addJunk
    obfuscate := method(src, opts,
        self _counter   = 0
        self _junkPhase = 0
        result := src
        if(opts at("stripComments"),  result = self stripComments(result))
        if(opts at("minifySpace"),    result = self minifyWhitespace(result))
        if(opts at("encodeStrings"),  result = self encodeStrings(result))
        if(opts at("obfuscateNums"),  result = self obfuscateNumbers(result))
        if(opts at("deepNums"),       result = self deepObfuscateNumbers(result, 3))
        if(opts at("renameVars"),     result = self renameLocals(result))
        if(opts at("obfuscateNils"),  result = self obfuscateNils(result))
        if(opts at("obfuscateBools"), result = self obfuscateBooleans(result))
        if(opts at("addJunk"),        result = self injectJunk(result))
        result
    )
)
