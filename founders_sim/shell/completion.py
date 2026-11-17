"""Tab completion for the prompt (prompt_toolkit).

First word  -> command names.
Later words -> game entities for that command (investors, runs, ...)
               and paths in the virtual filesystem.
"""
from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion

from ..vfs import VFSError


class ShellCompleter(Completer):
    def __init__(self, shell):
        self.shell = shell

    def candidates(self, text: str) -> tuple[str, list[str]]:
        """(the fragment being completed, possible full replacements)"""
        sh = self.shell
        segment = text
        for sep in ("|", ";", "&&", "||"):       # complete the command after a pipe, too
            segment = segment.rpartition(sep)[2]
        words = segment.split()
        fresh = segment.endswith(" ") or not segment.strip()
        fragment = "" if fresh else words[-1]
        if not words or (len(words) == 1 and not fresh):
            names = sorted(set(sh.commands) | set(sh.aliases))
            return fragment, [n + " " for n in names if n.startswith(fragment) and len(n) > 1]
        cmd = sh.commands.get(words[0])
        out: list[str] = []
        table = getattr(sh, "entity_completers", {})
        if cmd and cmd.name in table:
            out += [c for c in table[cmd.name]() if c.startswith(fragment)]
        out += [p for p in self.paths(fragment) if p not in out]
        return fragment, out

    def paths(self, fragment: str) -> list[str]:
        sh = self.shell
        head, slash, tail = fragment.rpartition("/")
        base = head + slash
        lookup = base or "."
        if base.startswith("~"):
            lookup = sh.env.get("HOME", "/") + base[1:]
        try:
            nodes = sh.fs.listdir(lookup, sh.cwd)
        except VFSError:
            return []
        out = []
        for node in nodes:
            if node.name.startswith(tail) and (tail.startswith(".") or not node.name.startswith(".")):
                out.append(base + node.name + ("/" if node.is_dir else ""))
        return out

    def get_completions(self, document, complete_event):
        self.shell.on_use("tab", True)
        fragment, options = self.candidates(document.text_before_cursor)
        for option in options:
            yield Completion(option, start_position=-len(fragment))
