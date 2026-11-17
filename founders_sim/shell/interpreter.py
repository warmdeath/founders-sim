"""The simulated bash shell: expands words, runs pipelines, handles
redirection, variables, aliases, history and scripts.

Commands are plain Python functions registered in `Shell.commands`.
Each receives a `Ctx` (arguments, stdin, where to write) and returns an
exit code (0 = success, like real programs).
"""
from __future__ import annotations

import difflib
import fnmatch
import re
from dataclasses import dataclass
from typing import Callable

from ..vfs import VFS, VFSError, HOME, COMPANY
from ..ui.io import IO, render_plain
from .parser import (parse, ShellSyntaxError, Word, Simple, For, If, Pipeline,
                     AndOr, ListNode)


@dataclass
class Command:
    name: str
    fn: Callable[["Ctx"], int | None]
    kind: str = "bash"            # "bash" = real unix command, "game" = game action
    summary: str = ""             # one line for `help`
    subcommands: tuple = ()       # for tab completion
    completes: str = "path"       # "path" | "none" | name of an entity list


class Ctx:
    """Everything one command invocation needs."""

    def __init__(self, sh: "Shell", name: str, args: list[str], stdin: str | None, piped: bool):
        self.sh = sh
        self.name = name
        self.args = args
        self.stdin = stdin        # None = nothing was piped in
        self.piped = piped        # True = our stdout goes to a pipe/file
        self.out_parts: list[str] = []
        self.err_parts: list[str] = []

    @property
    def fs(self) -> VFS:
        return self.sh.fs

    @property
    def game(self):
        return self.sh.game

    def out(self, text: str) -> None:
        if self.piped:
            self.out_parts.append(text)
        else:
            self.sh.io.write(text)

    def line(self, text: str = "") -> None:
        self.out(text + "\n")

    def err(self, text: str) -> None:
        self.err_parts.append(text + "\n")

    def show(self, renderable) -> None:
        """Rich output (tables/panels). Falls back to plain text in a pipe."""
        if self.piped:
            self.out_parts.append(render_plain(renderable))
        else:
            self.sh.io.print(renderable)

    def fail(self, message: str, code: int = 1) -> int:
        self.err(f"{self.name}: {message}")
        return code


GLOB_CHARS = set("*?[")
VAR_RE = re.compile(r"\$(\{[^}]*\}|[A-Za-z_][A-Za-z0-9_]*|[0-9?#@*$])")

# Real tools that are not simulated: answer with a useful pointer instead.
NOT_SIMULATED = {
    "vim": "no vim here - use `nano <file>` or `echo 'text' >> file`.",
    "vi": "no vi here - use `nano <file>` or `echo 'text' >> file`.",
    "code": "no VS Code in the sim - use `nano <file>`.",
    "git": "git is real-terminal only (see README). In the sim your work is saved with `save`.",
    "python": "there is no Python inside the sim; you direct agents instead: try `agent --help`.",
    "python3": "there is no Python inside the sim; you direct agents instead: try `agent --help`.",
    "sudo": "you are the founder: you already have all the power (and all the blame). No sudo needed.",
    "apt": "nothing to install in the sim. In real Ubuntu: `sudo apt install <package>`.",
    "pip": "nothing to install in the sim. In real life: `pip install <package>` inside a venv.",
    "curl": "the sim has no network. Your inbox is in ~/company/inbox.",
    "ssh": "the sim has no network.",
    "claude": "your agents are driven with the `agent` command here. Try `agent --help`.",
}


class Shell:
    def __init__(self, fs: VFS, io: IO, game=None):
        self.fs = fs
        self.io = io
        self.game = game
        self.cwd = COMPANY
        self.env: dict[str, str] = {
            "HOME": HOME, "USER": "founder", "SHELL": "/bin/bash", "PWD": COMPANY,
            "OLDPWD": COMPANY, "PATH": "/usr/local/bin:/usr/bin:/bin", "HOSTNAME": "startup",
            "EDITOR": "nano", "AGENT_MODEL": "fast",
        }
        self.exported = set(self.env)
        self.aliases: dict[str, str] = {"ll": "ls -l", "la": "ls -la"}
        self.history: list[str] = []
        self.commands: dict[str, Command] = {}
        self.last_status = 0
        self.positional: list[str] = []
        self.exit_requested = False
        self.depth = 0
        # hook: called as on_use(feature_name, success) so the game can
        # track which bash skills the player practised
        self.on_use: Callable[[str, bool], None] = lambda feature, ok: None

    # ------------------------------------------------------------ registry
    def register(self, name: str, fn, kind="bash", summary="", subcommands=(), completes="path",
                 aliases: tuple = ()):
        cmd = Command(name, fn, kind, summary, tuple(subcommands), completes)
        self.commands[name] = cmd
        for alias in aliases:
            self.commands[alias] = cmd

    def prompt_path(self) -> str:
        if self.cwd == HOME or self.cwd.startswith(HOME + "/"):
            return "~" + self.cwd[len(HOME):]
        return self.cwd

    # ------------------------------------------------------------ expansion
    def _var(self, name: str) -> str:
        if name.startswith("{"):
            name = name[1:-1]
        if name == "?":
            return str(self.last_status)
        if name == "#":
            return str(max(0, len(self.positional) - 1))
        if name in ("@", "*"):
            return " ".join(self.positional[1:])
        if name == "$":
            return "4242"
        if name.isdigit():
            idx = int(name)
            return self.positional[idx] if idx < len(self.positional) else ""
        return self.env.get(name, "")

    def expand_vars(self, text: str) -> str:
        return VAR_RE.sub(lambda m: self._var(m.group(1)), text)

    def _substitute(self, command: str) -> str:
        out, _ = self.run_tree(parse(command), None, capture=True)
        return out.rstrip("\n")

    def expand_word(self, word: Word, split: bool = True) -> list[str]:
        """One parsed word -> zero or more final argument strings."""
        fields = [""]
        pattern_fields = [""]     # same text but with quoted glob chars escaped
        quoted_any = False
        has_glob = False
        for index, (text, kind) in enumerate(word.parts):
            if kind == "single":
                value, splittable = text, False
            elif kind == "double":
                value, splittable = self.expand_vars(text), False
            elif kind == "dsub":
                value, splittable = self._substitute(text), False
            elif kind == "sub":
                value, splittable = self._substitute(text), True
            else:  # raw
                if index == 0 and (text == "~" or text.startswith("~/")):
                    text = self.env.get("HOME", HOME) + text[1:]
                value = self.expand_vars(text)
                splittable = value != text
                if GLOB_CHARS & set(text):
                    has_glob = True
            if kind != "raw":
                quoted_any = quoted_any or kind in ("single", "double", "dsub")
                escaped = "".join(f"[{c}]" if c in GLOB_CHARS else c for c in value)
            else:
                escaped = value
            if splittable and split:
                pieces = value.split()
                if not pieces:
                    continue
                if value[:1].isspace() and fields[-1]:
                    fields.append(""); pattern_fields.append("")
                for n, piece in enumerate(pieces):
                    if n > 0:
                        fields.append(""); pattern_fields.append("")
                    fields[-1] += piece
                    pattern_fields[-1] += piece
                if value[-1:].isspace():
                    fields.append(""); pattern_fields.append("")
            else:
                fields[-1] += value
                pattern_fields[-1] += escaped
        if fields[-1] == "" and len(fields) > 1:
            fields.pop(); pattern_fields.pop()
        if fields == [""] and not quoted_any:
            return []
        if has_glob and split:
            result: list[str] = []
            for plain, pattern in zip(fields, pattern_fields):
                matches = self.glob(pattern)
                result.extend(matches if matches else [plain])
            return result
        return fields

    def glob(self, pattern: str) -> list[str]:
        """Expand * ? [..] against the virtual filesystem (like bash does
        BEFORE the command runs - the command never sees the star)."""
        absolute = pattern.startswith("/")
        segments = [s for s in pattern.split("/") if s]
        candidates = ["/" if absolute else ""]
        for seg in segments:
            new: list[str] = []
            magic = bool(GLOB_CHARS & set(seg))
            for base in candidates:
                here = base if base else "."
                if not magic or seg in (".", ".."):
                    path = base + seg
                    if self.fs.exists(path, self.cwd):
                        new.append(path + "/")
                    continue
                try:
                    names = [n.name for n in self.fs.listdir(here, self.cwd)]
                except VFSError:
                    continue
                for name in names:
                    if name.startswith(".") and not seg.startswith("."):
                        continue
                    if fnmatch.fnmatchcase(name, seg):
                        new.append(base + name + "/")
            candidates = new
            if not candidates:
                return []
        return sorted(c.rstrip("/") or "/" for c in candidates)

    # ------------------------------------------------------------ execution
    def run_line(self, line: str, record: bool = True) -> int:
        """Run one line typed at the prompt. Returns the exit status."""
        line = line.strip()
        if not line:
            return self.last_status
        if line.startswith("!") and len(line) > 1 and line[1] != " ":  # history expansion
            target = None
            if line.startswith("!!"):
                target = self.history[-1] + line[2:] if self.history else None
            elif line[1:].isdigit() and 0 < int(line[1:]) <= len(self.history):
                target = self.history[int(line[1:]) - 1]
            if target is None:
                self.io.write(f"bash: {line.split()[0]}: event not found\n")
                self.last_status = 1
                return 1
            self.io.write(target + "\n")
            line = target
        if record:
            self.history.append(line)
        try:
            tree = parse(line)
        except ShellSyntaxError as exc:
            self.io.write(f"bash: {exc}\n")
            self.last_status = 2
            return 2
        try:
            _, code = self.run_tree(tree, None, capture=False)
        except RecursionError:
            self.io.write("bash: maximum recursion depth reached\n")
            code = 1
        self.last_status = code
        return code

    def run_tree(self, node: ListNode, stdin: str | None, capture: bool) -> tuple[str, int]:
        out, code = [], 0
        for item in node.items:
            text, code = self._run_and_or(item, stdin, capture)
            out.append(text)
            if self.exit_requested:
                break
        return "".join(out), code

    def _run_and_or(self, node: AndOr, stdin, capture) -> tuple[str, int]:
        out, code = self._run_pipeline(node.first, stdin, capture)
        for op, pipeline in node.rest:
            if (op == "&&") == (code == 0):
                more, code = self._run_pipeline(pipeline, stdin, capture)
                out += more
        return out, code

    def _run_pipeline(self, node: Pipeline, stdin, capture) -> tuple[str, int]:
        data, code = stdin, 0
        last = len(node.cmds) - 1
        if last > 0:
            self.on_use("pipe", True)
        for i, cmd in enumerate(node.cmds):
            piped = capture or i < last
            if isinstance(cmd, Simple):
                data, code = self._run_simple(cmd, data, piped)
            elif isinstance(cmd, For):
                data, code = self._run_for(cmd, data, piped)
            else:
                data, code = self._run_if(cmd, data, piped)
        self.last_status = code
        return (data or "") if capture else "", code

    def _run_for(self, node: For, stdin, capture) -> tuple[str, int]:
        values: list[str] = []
        for word in node.words:
            values.extend(self.expand_word(word))
        out, code = [], 0
        for value in values:
            self.env[node.var] = value
            text, code = self.run_tree(node.body, stdin, capture)
            out.append(text)
        self.on_use("script", True)
        return "".join(out), code

    def _run_if(self, node: If, stdin, capture) -> tuple[str, int]:
        cond_out, code = self.run_tree(node.cond, stdin, capture)
        if code == 0:
            out, code = self.run_tree(node.then, stdin, capture)
        elif node.otherwise is not None:
            out, code = self.run_tree(node.otherwise, stdin, capture)
        else:
            out, code = "", 0
        return cond_out + out, code

    def _run_simple(self, cmd: Simple, stdin, piped) -> tuple[str | None, int]:
        # 1. expand words (variables, globs, substitutions)
        try:
            argv: list[str] = []
            for word in cmd.words:
                argv.extend(self.expand_word(word))
            # alias expansion (first word only, one level - like bash)
            if argv and argv[0] in self.aliases and cmd.words[0].is_plain():
                extra = parse(self.aliases[argv[0]]).items
                if extra and isinstance(extra[0].first.cmds[0], Simple) and len(extra) == 1 \
                        and len(extra[0].first.cmds) == 1 and not extra[0].rest:
                    head: list[str] = []
                    for word in extra[0].first.cmds[0].words:
                        head.extend(self.expand_word(word))
                    argv = head + argv[1:]
            assigns = [(name, "".join(self.expand_word(value, split=False)))
                       for name, value in cmd.assigns]
        except ShellSyntaxError as exc:
            self.io.write(f"bash: {exc}\n")
            return "", 2
        if not argv:
            for name, value in assigns:        # plain `X=1`
                self.env[name] = value
                self.on_use("variables", True)
            if not cmd.redirs:
                return "", 0
            argv = ["true"]

        # 2. redirections
        out_file = err_file = None
        out_append = err_append = False
        merge_err = False
        for op, target in cmd.redirs:
            if op == "2>&1":
                merge_err = True
                continue
            names = self.expand_word(target)
            if len(names) != 1:
                self.io.write(f"bash: {target.literal()}: ambiguous redirect\n")
                return "", 1
            name = names[0]
            if op == "<":
                try:
                    stdin = self.fs.read(name, self.cwd)
                except VFSError as exc:
                    self.io.write(f"bash: {name}: {exc.reason}\n")
                    return "", 1
            elif op in (">", ">>", "&>"):
                out_file, out_append = name, op == ">>"
                merge_err = merge_err or op == "&>"
            else:
                err_file, err_append = name, op == "2>>"
        for name, append in ((out_file, out_append), (err_file, err_append)):
            if name is not None:     # bash creates/truncates the file before running
                try:
                    self.fs.write(name, "", self.cwd, append=True if append else False)
                except VFSError as exc:
                    self.io.write(f"bash: {name}: {exc.reason}\n")
                    return "", 1

        # 3. run
        saved_env = None
        if assigns:                  # `VAR=x command` -> only for that command
            saved_env = dict(self.env)
            self.env.update(assigns)
        ctx = Ctx(self, argv[0], argv[1:], stdin, piped or out_file is not None)
        code = self._dispatch(ctx)
        if saved_env is not None:
            for name, _ in assigns:
                if name in saved_env:
                    self.env[name] = saved_env[name]
                else:
                    self.env.pop(name, None)

        # 4. deliver output
        out, err = "".join(ctx.out_parts), "".join(ctx.err_parts)
        if merge_err:
            out, err = out + err, ""
        if err:
            if err_file is not None:
                self.fs.write(err_file, err, self.cwd, append=True)
            else:
                self.io.write(err)
        if out_file is not None:
            self.fs.write(out_file, out, self.cwd, append=True)
            self.on_use("redirect_append" if out_append else "redirect", code == 0)
            self.on_file_written(self.fs.normalize(out_file, self.cwd))
            return ("" if piped else None), code
        return out, code

    def on_file_written(self, path: str) -> None:
        """Hook for the game (e.g. to notice an edited spec). Default: nothing."""

    def _dispatch(self, ctx: Ctx) -> int:
        name = ctx.name
        if "/" in name:              # ./script.sh or a path
            return self._run_path(ctx)
        cmd = self.commands.get(name)
        if cmd is None:
            ctx.err(f"bash: {name}: command not found")
            if name in NOT_SIMULATED:
                ctx.err(f"  hint: {NOT_SIMULATED[name]}")
            else:
                close = difflib.get_close_matches(name, list(self.commands), n=1, cutoff=0.6)
                ctx.err(f"  hint: did you mean `{close[0]}`? " if close else
                        "  hint: type `help` to list commands, or `tutor` for what to learn next.")
            self.on_use("unknown", False)
            return 127
        if (cmd.kind == "game" and ctx.args[:1] in (["--help"], ["-h"])) or \
                (cmd.kind == "bash" and "--help" in ctx.args and name not in ("echo", "man")):
            ctx.args = [cmd.name]
            cmd = self.commands["man"]
            self.on_use("--help", True)
        self.depth += 1
        try:
            if self.depth > 40:
                raise RecursionError
            code = cmd.fn(ctx) or 0
        except VFSError as exc:
            ctx.err(f"{name}: {exc.path}: {exc.reason}")
            code = 1
        finally:
            self.depth -= 1
        self.on_use(cmd.name, code == 0)
        return code

    def _run_path(self, ctx: Ctx) -> int:
        try:
            node = self.fs.lookup(ctx.name, self.cwd)
        except VFSError as exc:
            ctx.err(f"bash: {ctx.name}: {exc.reason}")
            return 127
        if node.is_dir:
            ctx.err(f"bash: {ctx.name}: Is a directory")
            return 126
        if not node.mode & 0o100:
            ctx.err(f"bash: {ctx.name}: Permission denied")
            ctx.err("  hint: a file needs the execute (x) permission to be run: `chmod +x <file>`")
            self.on_use("exec_denied", False)
            return 126
        code = self.run_script(node.content, [ctx.name] + ctx.args, ctx)  # type: ignore[union-attr]
        self.on_use("script", code == 0)
        return code

    def run_script(self, text: str, argv: list[str], ctx: Ctx) -> int:
        """Run a script file's text: same parser, with $1 $2 ... set."""
        saved = self.positional
        self.positional = argv
        try:
            tree = parse(text)
            out, code = self.run_tree(tree, ctx.stdin, capture=ctx.piped)
            if ctx.piped:
                ctx.out_parts.append(out)
        except ShellSyntaxError as exc:
            ctx.err(f"{argv[0]}: {exc}")
            code = 2
        finally:
            self.positional = saved
        return code
