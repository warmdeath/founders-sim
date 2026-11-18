"""Turn a command line into a tree the shell can execute.

Two steps, like a real shell:
  1. tokenize():  "cat a.txt | grep -i 'big deal' > out"  ->  tokens
  2. parse():     tokens -> a small tree (ListNode > AndOr > Pipeline > Simple)

Supported bash syntax: quotes ('..', "..", \\x), variables, $(command
substitution), pipes |, redirection (> >> < 2> 2>> 2>&1 &>), ; && ||,
comments, `for ... do ... done` and `if ... then ... else ... fi`.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class ShellSyntaxError(Exception):
    pass


# A word is a list of parts; each part remembers how it was quoted so the
# shell knows whether to expand $VARS and * globs inside it.
#   kind: "raw" (unquoted) | "single" (literal) | "double" | "sub" / "dsub"
#         (command substitution, unquoted / inside double quotes)
@dataclass
class Word:
    parts: list[tuple[str, str]] = field(default_factory=list)

    def literal(self) -> str:
        return "".join(text for text, _ in self.parts)

    def is_plain(self) -> bool:
        return all(kind == "raw" for _, kind in self.parts)


@dataclass
class Op:
    text: str


OPERATORS = ["2>&1", "&>", ">>", "&&", "||", ">", "<", "|", ";", "\n", "&"]


def _read_substitution(line: str, i: int) -> tuple[str, int]:
    """`i` points just after "$(" ; return (inner text, index after ")")."""
    depth, start = 1, i
    while i < len(line):
        if line[i] == "(":
            depth += 1
        elif line[i] == ")":
            depth -= 1
            if depth == 0:
                return line[start:i], i + 1
        i += 1
    raise ShellSyntaxError("unexpected EOF while looking for matching `)'")


def tokenize(line: str) -> list[Word | Op]:
    tokens: list[Word | Op] = []
    word: Word | None = None
    i, n = 0, len(line)

    def add(text: str, kind: str):
        nonlocal word
        if word is None:
            word = Word()
        if word.parts and word.parts[-1][1] == kind and kind in ("raw", "single", "double"):
            word.parts[-1] = (word.parts[-1][0] + text, kind)
        else:
            word.parts.append((text, kind))

    def flush():
        nonlocal word
        if word is not None:
            tokens.append(word)
            word = None

    while i < n:
        ch = line[i]
        if ch in " \t":
            flush()
            i += 1
        elif ch == "#" and word is None:
            while i < n and line[i] != "\n":
                i += 1
        elif ch == "\\":
            if i + 1 < n:
                if line[i + 1] != "\n":       # backslash-newline = line continuation
                    add(line[i + 1], "single")
                i += 2
            else:
                i += 1
        elif ch == "'":
            end = line.find("'", i + 1)
            if end < 0:
                raise ShellSyntaxError("unexpected EOF while looking for matching `''")
            add(line[i + 1:end], "single")
            i = end + 1
        elif ch == '"':
            i += 1
            add("", "double")
            while True:
                if i >= n:
                    raise ShellSyntaxError("unexpected EOF while looking for matching `\"'")
                c = line[i]
                if c == '"':
                    i += 1
                    break
                if c == "\\" and i + 1 < n and line[i + 1] in '"\\$`':
                    add(line[i + 1], "single")
                    i += 2
                elif line.startswith("$(", i):
                    inner, i = _read_substitution(line, i + 2)
                    add(inner, "dsub")
                else:
                    add(c, "double")
                    i += 1
        elif line.startswith("$(", i):
            inner, i = _read_substitution(line, i + 2)
            add(inner, "sub")
        elif ch == "`":
            end = line.find("`", i + 1)
            if end < 0:
                raise ShellSyntaxError("unexpected EOF while looking for matching ``'")
            add(line[i + 1:end], "sub")
            i = end + 1
        else:
            if word is None and line.startswith("2>>", i):
                tokens.append(Op("2>>")); i += 3; continue
            if word is None and line.startswith("2>&1", i):
                tokens.append(Op("2>&1")); i += 4; continue
            if word is None and line.startswith("2>", i):
                tokens.append(Op("2>")); i += 2; continue
            for op in OPERATORS:
                if line.startswith(op, i):
                    flush()
                    tokens.append(Op(op))
                    i += len(op)
                    break
            else:
                add(ch, "raw")
                i += 1
    flush()
    return tokens


# ------------------------------------------------------------------ the tree
@dataclass
class Simple:
    assigns: list[tuple[str, Word]] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)
    redirs: list[tuple[str, Word | None]] = field(default_factory=list)


@dataclass
class For:
    var: str
    words: list[Word]
    body: "ListNode"


@dataclass
class If:
    cond: "ListNode"
    then: "ListNode"
    otherwise: "ListNode | None"


@dataclass
class Pipeline:
    cmds: list[Simple | For | If]


@dataclass
class AndOr:
    first: Pipeline
    rest: list[tuple[str, Pipeline]] = field(default_factory=list)


@dataclass
class ListNode:
    items: list[AndOr] = field(default_factory=list)


REDIR_OPS = {">", ">>", "<", "2>", "2>>", "&>", "2>&1"}
KEYWORDS_END = {"do", "done", "then", "else", "fi"}


class Parser:
    def __init__(self, tokens: list[Word | Op]):
        self.toks = tokens
        self.pos = 0

    def peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def next(self):
        tok = self.peek()
        self.pos += 1
        return tok

    def _keyword(self) -> str | None:
        tok = self.peek()
        if isinstance(tok, Word) and tok.is_plain():
            return tok.literal()
        return None

    def _unexpected(self, tok) -> ShellSyntaxError:
        text = "newline" if tok is None or (isinstance(tok, Op) and tok.text == "\n") else (
            tok.text if isinstance(tok, Op) else tok.literal())
        return ShellSyntaxError(f"syntax error near unexpected token `{text}'")

    def _skip_separators(self):
        while isinstance(self.peek(), Op) and self.peek().text in (";", "\n"):
            self.pos += 1

    def parse_list(self, stop: set[str] = frozenset()) -> ListNode:
        node = ListNode()
        while True:
            while isinstance(self.peek(), Op) and self.peek().text == "\n":
                self.pos += 1
            tok = self.peek()
            if tok is None or self._keyword() in stop:
                break
            if isinstance(tok, Op) and tok.text == ";":
                raise self._unexpected(tok)
            node.items.append(self.parse_and_or())
            tok = self.peek()
            if isinstance(tok, Op) and tok.text in (";", "\n", "&"):
                self.pos += 1
            elif tok is not None and self._keyword() not in stop:
                raise self._unexpected(tok)
        return node

    def parse_and_or(self) -> AndOr:
        node = AndOr(self.parse_pipeline())
        while isinstance(self.peek(), Op) and self.peek().text in ("&&", "||"):
            op = self.next().text
            while isinstance(self.peek(), Op) and self.peek().text == "\n":
                self.pos += 1
            node.rest.append((op, self.parse_pipeline()))
        return node

    def parse_pipeline(self) -> Pipeline:
        cmds = [self.parse_command()]
        while isinstance(self.peek(), Op) and self.peek().text == "|":
            self.pos += 1
            cmds.append(self.parse_command())
        return Pipeline(cmds)

    def _expect_keyword(self, word: str):
        self._skip_separators()
        if self._keyword() != word:
            raise self._unexpected(self.peek())
        self.pos += 1

    def parse_command(self):
        key = self._keyword()
        if key == "for":
            self.pos += 1
            var = self.next()
            if not isinstance(var, Word):
                raise self._unexpected(var)
            words: list[Word] = []
            if self._keyword() == "in":
                self.pos += 1
                while isinstance(self.peek(), Word):
                    words.append(self.next())
            self._expect_keyword("do")
            body = self.parse_list({"done"})
            self._expect_keyword("done")
            return For(var.literal(), words, body)
        if key == "if":
            self.pos += 1
            cond = self.parse_list({"then"})
            self._expect_keyword("then")
            then = self.parse_list({"else", "fi"})
            otherwise = None
            if self._keyword() == "else":
                self.pos += 1
                otherwise = self.parse_list({"fi"})
            self._expect_keyword("fi")
            return If(cond, then, otherwise)
        cmd = Simple()
        while True:
            tok = self.peek()
            if isinstance(tok, Word):
                self.pos += 1
                text = tok.literal()
                first = tok.parts[0]
                if (not cmd.words and first[1] == "raw" and "=" in first[0]
                        and first[0].split("=")[0].replace("_", "a").isalnum()
                        and not first[0][0].isdigit()):
                    name, _, rest = first[0].partition("=")
                    value = Word(([(rest, "raw")] if rest else []) + tok.parts[1:])
                    cmd.assigns.append((name, value))
                else:
                    cmd.words.append(tok)
                del text
            elif isinstance(tok, Op) and tok.text in REDIR_OPS:
                self.pos += 1
                if tok.text == "2>&1":
                    cmd.redirs.append((tok.text, None))
                    continue
                target = self.next()
                if not isinstance(target, Word):
                    raise self._unexpected(target)
                cmd.redirs.append((tok.text, target))
            else:
                break
        if not cmd.words and not cmd.assigns and not cmd.redirs:
            raise self._unexpected(self.peek())
        return cmd


def parse(line: str) -> ListNode:
    parser = Parser(tokenize(line))
    tree = parser.parse_list()
    if parser.peek() is not None:
        raise parser._unexpected(parser.peek())
    return tree
