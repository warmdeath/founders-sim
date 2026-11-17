"""All input/output goes through one small `IO` object.

Why: the game logic never calls print() or input() directly. The real game
uses `TerminalIO` (rich + prompt_toolkit); tests use `ScriptedIO`, which
feeds pre-written answers and records everything printed. Same game code,
no terminal needed.
"""
from __future__ import annotations

import io as _io
import sys

from rich.console import Console
from rich.theme import Theme

THEME = Theme({
    "good": "bold green", "bad": "bold red", "warn": "yellow", "dim": "grey58",
    "term": "bold cyan", "cmd": "bold magenta", "money": "green", "title": "bold white",
})


def render_plain(renderable, width: int = 100) -> str:
    """Render any rich object (table, panel...) to plain text - used when a
    game command's output is piped into grep/wc/etc."""
    buf = _io.StringIO()
    Console(file=buf, width=width, color_system=None, theme=THEME, force_terminal=False).print(renderable)
    return buf.getvalue()


class IO:
    """Base class: prints with rich; subclasses decide how to ask questions."""

    interactive = False

    def __init__(self, console: Console | None = None):
        self.console = console or Console(theme=THEME, highlight=False)

    def print(self, *objects, **kwargs) -> None:
        self.console.print(*objects, **kwargs)

    def write(self, text: str) -> None:
        """Raw command output (no markup interpretation), like a real terminal."""
        self.console.out(text, end="", highlight=False)

    def choose(self, title: str, options: list[str], default: int = 0) -> int:
        raise NotImplementedError

    def ask(self, prompt: str) -> str:
        raise NotImplementedError

    def pause(self, message: str = "Press Enter to continue...") -> None:
        pass

    def edit(self, text: str, title: str = "") -> str | None:
        """Open a mini editor; return new text or None if cancelled."""
        return None

    def page(self, text: str) -> None:
        self.write(text if text.endswith("\n") or not text else text + "\n")


class ScriptedIO(IO):
    """For tests and non-interactive runs: answers come from a list."""

    def __init__(self, answers: list | None = None, width: int = 110):
        self.buffer = _io.StringIO()
        super().__init__(Console(file=self.buffer, width=width, color_system=None,
                                 theme=THEME, force_terminal=False, highlight=False))
        self.answers = list(answers or [])
        self.asked: list[str] = []

    def output(self) -> str:
        return self.buffer.getvalue()

    def clear(self) -> None:
        self.buffer.seek(0)
        self.buffer.truncate()

    def _next(self, default):
        return self.answers.pop(0) if self.answers else default

    def choose(self, title, options, default=0):
        self.asked.append(title)
        self.print(title)
        answer = self._next(default)
        if isinstance(answer, str):  # allow answering by option text
            for i, opt in enumerate(options):
                if answer.lower() in opt.lower():
                    return i
            return default
        return max(0, min(len(options) - 1, int(answer)))

    def ask(self, prompt):
        self.asked.append(prompt)
        self.print(prompt)
        return str(self._next(""))

    def edit(self, text, title=""):
        answer = self._next(None)
        return answer if isinstance(answer, str) else None


class TerminalIO(IO):
    """The real thing: arrow-key menus and line editing via prompt_toolkit."""

    interactive = True

    def choose(self, title, options, default=0):
        if not sys.stdin.isatty():
            return self._choose_plain(title, options, default)
        from .choices import arrow_select
        self.print(title)
        index = arrow_select(options, default)
        self.print(f"  [dim]→ {options[index]}[/dim]", highlight=False)
        return index

    def _choose_plain(self, title, options, default):
        self.print(title)
        for i, opt in enumerate(options, 1):
            self.print(f"  {i}) {opt}", markup=False)
        try:
            raw = input("> ").strip()
            return max(0, min(len(options) - 1, int(raw) - 1))
        except (ValueError, EOFError):
            return default

    def ask(self, prompt):
        self.print(prompt, end=" ")
        try:
            if sys.stdin.isatty():
                from prompt_toolkit import prompt as pt_prompt
                return pt_prompt("» ").strip()
            return input().strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    def pause(self, message="Press Enter to continue..."):
        if not sys.stdin.isatty():
            return
        try:
            input(f"\x1b[2m{message}\x1b[0m")
        except (EOFError, KeyboardInterrupt):
            pass

    def edit(self, text, title=""):
        if not sys.stdin.isatty():
            return None
        from prompt_toolkit import prompt as pt_prompt
        self.print(f"[dim]── editing {title} ── Esc then Enter = save · Ctrl+C = cancel ──[/dim]")
        try:
            return pt_prompt("", default=text, multiline=True)
        except (EOFError, KeyboardInterrupt):
            return None

    def page(self, text):
        """`less`: show one screen at a time."""
        lines = text.splitlines()
        height = max(5, self.console.size.height - 2)
        if not sys.stdin.isatty() or len(lines) <= height:
            return super().page(text)
        pos = 0
        while pos < len(lines):
            self.write("\n".join(lines[pos:pos + height]) + "\n")
            pos += height
            if pos >= len(lines):
                break
            try:
                key = input("\x1b[7m--More-- (Enter = next page, q = quit)\x1b[0m ")
            except (EOFError, KeyboardInterrupt):
                break
            if key.strip().lower().startswith("q"):
                break
