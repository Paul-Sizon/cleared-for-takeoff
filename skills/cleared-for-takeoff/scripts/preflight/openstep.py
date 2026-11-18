"""Minimal parser for OpenStep-style property lists (Xcode's project.pbxproj)."""
from __future__ import annotations

import re

_BARE = re.compile(r"[A-Za-z0-9_$/:.\-+]+")


class ParseError(ValueError):
    pass


class _Parser:
    def __init__(self, text: str):
        self.s = text
        self.i = 0
        self.n = len(text)

    def _skip(self) -> None:
        s, n = self.s, self.n
        while self.i < n:
            c = s[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif s.startswith("//", self.i):
                j = s.find("\n", self.i)
                self.i = n if j < 0 else j + 1
            elif s.startswith("/*", self.i):
                j = s.find("*/", self.i + 2)
                if j < 0:
                    raise ParseError("unterminated comment")
                self.i = j + 2
            else:
                break

    def _peek(self) -> str:
        self._skip()
        return self.s[self.i] if self.i < self.n else ""

    def _expect(self, ch: str) -> None:
        if self._peek() != ch:
            raise ParseError(f"expected {ch!r} at {self.i}")
        self.i += 1

    def value(self):
        c = self._peek()
        if c == "{":
            return self._dict()
        if c == "(":
            return self._array()
        if c == '"':
            return self._quoted()
        if c == "<":
            j = self.s.find(">", self.i)
            raw = self.s[self.i + 1 : j]
            self.i = j + 1
            return raw
        m = _BARE.match(self.s, self.i)
        if not m:
            raise ParseError(f"unexpected {c!r} at {self.i}")
        self.i = m.end()
        return m.group(0)

    def _quoted(self) -> str:
        self.i += 1
        out = []
        s = self.s
        while self.i < self.n:
            c = s[self.i]
            if c == "\\":
                nxt = s[self.i + 1]
                out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, nxt))
                self.i += 2
            elif c == '"':
                self.i += 1
                return "".join(out)
            else:
                out.append(c)
                self.i += 1
        raise ParseError("unterminated string")

    def _dict(self) -> dict:
        self._expect("{")
        d = {}
        while self._peek() != "}":
            k = self.value()
            self._expect("=")
            d[k] = self.value()
            self._expect(";")
        self.i += 1
        return d

    def _array(self) -> list:
        self._expect("(")
        arr = []
        while self._peek() != ")":
            arr.append(self.value())
            if self._peek() == ",":
                self.i += 1
        self.i += 1
        return arr


def loads(text: str):
    return _Parser(text).value()
