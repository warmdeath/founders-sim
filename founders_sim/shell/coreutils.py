"""Simulated versions of the real unix commands (ls, cat, grep ...).

Each function mimics the real tool's flags, output format and error
messages closely, so what you learn here works in a real terminal.
They only ever touch the virtual filesystem (`ctx.fs`).
"""
from __future__ import annotations

import datetime
import fnmatch
import re

from rich.text import Text

from ..vfs import VFSError, Dir, File, Node, HOME
from .interpreter import Ctx, Shell

GAME_START = datetime.date(2026, 1, 5)   # week 1 starts on this Monday


class UsageError(Exception):
    pass


def game_date(week: int) -> datetime.date:
    return GAME_START + datetime.timedelta(days=7 * max(0, week - 1))


def split_flags(ctx: Ctx, allowed: str, with_value: str = "") -> tuple[set, dict, list[str]]:
    """Separate '-la' style flags from operands. Flags listed in
    `with_value` take an argument (`-n 5` or `-n5`)."""
    flags: set[str] = set()
    values: dict[str, str] = {}
    operands: list[str] = []
    args = list(ctx.args)
    while args:
        arg = args.pop(0)
        if arg == "--":
            operands.extend(args)
            break
        if arg.startswith("-") and len(arg) > 1 and not arg.startswith("--"):
            i = 1
            while i < len(arg):
                ch = arg[i]
                if ch in with_value:
                    rest = arg[i + 1:]
                    if not rest:
                        if not args:
                            raise UsageError(f"option requires an argument -- '{ch}'")
                        rest = args.pop(0)
                    values[ch] = rest
                    break
                if ch not in allowed:
                    raise UsageError(f"invalid option -- '{ch}'")
                flags.add(ch)
                i += 1
        elif arg.startswith("--") and len(arg) > 2:
            raise UsageError(f"unrecognized option '{arg}'")
        else:
            operands.append(arg)
    return flags, values, operands


def read_inputs(ctx: Ctx, files: list[str], err_fmt: str = "{cmd}: {path}: {reason}"):
    """Yield (label, text) for each file operand, or stdin when there are
    none. Prints bash-style errors and remembers failure in ctx.failed."""
    ctx.failed = False  # type: ignore[attr-defined]
    if not files:
        if ctx.stdin is None:
            ctx.err(f"{ctx.name}: nothing to read. (A real terminal would now wait for you to type; "
                    f"in the sim, give a file or pipe something in: `cat file | {ctx.name}`)")
            ctx.failed = True  # type: ignore[attr-defined]
            return
        yield "", ctx.stdin
        return
    for path in files:
        if path == "-":
            yield "", ctx.stdin or ""
            continue
        try:
            yield path, ctx.fs.read(path, ctx.sh.cwd)
        except VFSError as exc:
            ctx.err(err_fmt.format(cmd=ctx.name, path=path, reason=exc.reason))
            ctx.failed = True  # type: ignore[attr-defined]


# ------------------------------------------------------------- navigation
def cmd_pwd(ctx: Ctx):
    ctx.line(ctx.sh.cwd)


def cmd_cd(ctx: Ctx):
    sh = ctx.sh
    if len(ctx.args) > 1:
        ctx.err("bash: cd: too many arguments")
        return 1
    target = ctx.args[0] if ctx.args else sh.env.get("HOME", HOME)
    show = False
    if target == "-":
        target, show = sh.env.get("OLDPWD", sh.cwd), True
    try:
        node = ctx.fs.lookup(target, sh.cwd)
    except VFSError as exc:
        ctx.err(f"bash: cd: {target}: {exc.reason}")
        return 1
    if not node.is_dir:
        ctx.err(f"bash: cd: {target}: Not a directory")
        return 1
    sh.env["OLDPWD"] = sh.cwd
    sh.cwd = node.path() or "/"
    if sh.cwd == "":
        sh.cwd = "/"
    sh.env["PWD"] = sh.cwd
    if show:
        ctx.line(sh.cwd)


def _human(size: int) -> str:
    for unit in ("", "K", "M"):
        if size < 1024:
            return f"{size}{unit}" if not unit else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}G"


def _ls_date(week: int) -> str:
    d = game_date(week)
    return f"{d.strftime('%b')} {d.day:>2} 09:00"


def _styled(node: Node, name: str) -> Text:
    if node.is_dir:
        return Text(name, style="bold blue")
    if node.mode & 0o111:
        return Text(name, style="bold green")
    return Text(name)


def cmd_ls(ctx: Ctx):
    try:
        flags, _, paths = split_flags(ctx, "laA1htrRdS")
    except UsageError as exc:
        ctx.err(f"ls: {exc}\nTry 'ls --help' for more information.")
        return 2
    sh, fs = ctx.sh, ctx.fs
    paths = paths or ["."]
    code = 0
    files: list[tuple[str, Node]] = []
    dirs: list[tuple[str, Dir]] = []
    for path in paths:
        try:
            node = fs.lookup(path, sh.cwd)
        except VFSError as exc:
            ctx.err(f"ls: cannot access '{path}': {exc.reason}")
            code = 2
            continue
        if node.is_dir and "d" not in flags:
            dirs.append((path, node))  # type: ignore[arg-type]
        else:
            files.append((path, node))

    def order(entries: list[tuple[str, Node]]) -> list[tuple[str, Node]]:
        if "t" in flags:
            entries = sorted(entries, key=lambda e: (-e[1].mtime, e[0]))
        elif "S" in flags:
            entries = sorted(entries, key=lambda e: (-e[1].size, e[0]))
        else:
            entries = sorted(entries, key=lambda e: e[0].lstrip(".").lower())
        return entries[::-1] if "r" in flags else entries

    def emit(entries: list[tuple[str, Node]], total: bool):
        if "l" in flags:
            if total:
                ctx.line(f"total {sum((n.size + 1023) // 1024 * 4 // 4 for _, n in entries)}")
            width = max((len(_human(n.size) if "h" in flags else str(n.size)) for _, n in entries), default=1)
            for name, node in entries:
                size = _human(node.size) if "h" in flags else str(node.size)
                links = 2 + sum(c.is_dir for c in node.children.values()) if isinstance(node, Dir) else 1
                prefix = f"{node.mode_string()} {links} founder founder {size:>{width}} {_ls_date(node.mtime)} "
                if ctx.piped:
                    ctx.line(prefix + name)
                else:
                    sh.io.print(Text(prefix) + _styled(node, name))
        elif ctx.piped or "1" in flags:
            for name, _ in entries:
                ctx.line(name)
        elif entries:
            # column layout, filled top-to-bottom like real ls
            width = sh.io.console.size.width
            col = max(len(name) for name, _ in entries) + 2
            cols = max(1, width // col)
            rows = -(-len(entries) // cols)
            for r in range(rows):
                line = Text()
                for c in range(cols):
                    i = c * rows + r
                    if i < len(entries):
                        name, node = entries[i]
                        line.append_text(_styled(node, name))
                        line.append(" " * (col - len(name)))
                sh.io.print(line)

    if files:
        emit(order(files), total=False)
    multiple = len(paths) > 1 or "R" in flags
    queue = [(p, d) for p, d in order(dirs)]  # type: ignore[misc]
    first = not files
    while queue:
        path, node = queue.pop(0)
        if multiple:
            if not first:
                ctx.line()
            ctx.line(f"{path}:")
        first = False
        entries: list[tuple[str, Node]] = [(n.name, n) for n in node.children.values()
                                           if "a" in flags or "A" in flags or not n.name.startswith(".")]
        if "a" in flags:
            entries += [(".", node), ("..", node.parent or node)]
        entries = order(entries)
        emit(entries, total=True)
        if "R" in flags:
            subs = [(f"{path.rstrip('/')}/{name}", n) for name, n in entries
                    if n.is_dir and name not in (".", "..")]
            queue = subs + queue  # type: ignore[assignment]
    return code


def cmd_tree(ctx: Ctx):
    try:
        flags, values, paths = split_flags(ctx, "ad", "L")
    except UsageError as exc:
        return ctx.fail(str(exc), 2)
    depth_limit = int(values.get("L", "99"))
    counts = [0, 0]
    for path in paths or ["."]:
        try:
            root = ctx.fs.lookup(path, ctx.sh.cwd)
        except VFSError as exc:
            ctx.line(f"{path}  [error opening dir: {exc.reason}]")
            continue
        ctx.line(path)

        def walk(node: Node, prefix: str, depth: int):
            if not isinstance(node, Dir) or depth > depth_limit:
                return
            kids = [c for c in sorted(node.children.values(), key=lambda n: n.name)
                    if ("a" in flags or not c.name.startswith(".")) and ("d" not in flags or c.is_dir)]
            for i, child in enumerate(kids):
                last = i == len(kids) - 1
                ctx.line(f"{prefix}{'└── ' if last else '├── '}{child.name}")
                counts[0 if child.is_dir else 1] += 1
                walk(child, prefix + ("    " if last else "│   "), depth + 1)
        walk(root, "", 1)
    ctx.line(f"\n{counts[0]} directories, {counts[1]} files")


# ---------------------------------------------------------------- reading
def cmd_cat(ctx: Ctx):
    try:
        flags, _, files = split_flags(ctx, "n")
    except UsageError as exc:
        ctx.err(f"cat: {exc}")
        return 1
    number = 0
    for _, text in read_inputs(ctx, files):
        if "n" in flags:
            for line in text.splitlines():
                number += 1
                ctx.line(f"{number:>6}\t{line}")
        else:
            ctx.out(text)
    return 1 if ctx.failed else 0  # type: ignore[attr-defined]


def cmd_less(ctx: Ctx):
    files = [a for a in ctx.args if not a.startswith("-")]
    chunks = [text for _, text in read_inputs(ctx, files)]
    if ctx.failed:  # type: ignore[attr-defined]
        return 1
    text = "".join(chunks)
    if ctx.piped:
        ctx.out(text)
    else:
        ctx.sh.io.page(text)


def _head_tail(ctx: Ctx, tail: bool):
    args = list(ctx.args)
    count, from_line = 10, False
    files: list[str] = []
    while args:
        arg = args.pop(0)
        if arg == "-n":
            if not args:
                ctx.err(f"{ctx.name}: option requires an argument -- 'n'")
                return 1
            arg = "-n" + args.pop(0)
        if arg.startswith("-n"):
            arg = "-" + arg[2:]
        if arg.startswith("-") and len(arg) > 1:
            value = arg[1:]
            if tail and value.startswith("+"):
                from_line, value = True, value[1:]
            if not value.isdigit():
                ctx.err(f"{ctx.name}: invalid number of lines: ‘{arg[1:]}’")
                return 1
            count = int(value)
        else:
            files.append(arg)
    code = 0
    shown = 0
    for label, text in read_inputs(ctx, files, "{cmd}: cannot open '{path}' for reading: {reason}"):
        lines = text.splitlines(keepends=True)
        if len(files) > 1:
            ctx.line(("\n" if shown else "") + f"==> {label} <==")
        shown += 1
        if tail:
            part = lines[count - 1:] if from_line else (lines[-count:] if count else [])
        else:
            part = lines[:count]
        ctx.out("".join(part))
    return 1 if ctx.failed else code  # type: ignore[attr-defined]


def cmd_head(ctx: Ctx):
    return _head_tail(ctx, tail=False)


def cmd_tail(ctx: Ctx):
    return _head_tail(ctx, tail=True)


# ------------------------------------------------------- creating / moving
def cmd_mkdir(ctx: Ctx):
    try:
        flags, _, paths = split_flags(ctx, "pv")
    except UsageError as exc:
        return ctx.fail(str(exc))
    if not paths:
        ctx.err("mkdir: missing operand\nTry 'mkdir --help' for more information.")
        return 1
    code = 0
    for path in paths:
        try:
            ctx.fs.mkdir(path, ctx.sh.cwd, parents="p" in flags)
        except VFSError as exc:
            ctx.err(f"mkdir: cannot create directory ‘{path}’: {exc.reason}")
            code = 1
    return code


def cmd_touch(ctx: Ctx):
    if not ctx.args:
        ctx.err("touch: missing file operand\nTry 'touch --help' for more information.")
        return 1
    code = 0
    for path in ctx.args:
        try:
            if ctx.fs.exists(path, ctx.sh.cwd):
                ctx.fs.lookup(path, ctx.sh.cwd).mtime = ctx.fs.clock
            else:
                ctx.fs.write(path, "", ctx.sh.cwd)
        except VFSError as exc:
            ctx.err(f"touch: cannot touch '{path}': {exc.reason}")
            code = 1
    return code


def _dest(ctx: Ctx, src: Node, dest: str):
    """Work out the (parent dir, new name) a cp/mv should write to."""
    fs, cwd = ctx.fs, ctx.sh.cwd
    if fs.is_dir(dest, cwd):
        return fs.lookup(dest, cwd), src.name
    parent, name = fs._parent_and_name(dest, cwd)
    return parent, name


def cmd_cp(ctx: Ctx):
    try:
        flags, _, paths = split_flags(ctx, "rRvfa")
    except UsageError as exc:
        return ctx.fail(str(exc))
    if not paths:
        ctx.err("cp: missing file operand\nTry 'cp --help' for more information.")
        return 1
    if len(paths) == 1:
        ctx.err(f"cp: missing destination file operand after '{paths[0]}'")
        return 1
    *sources, dest = paths
    fs, cwd = ctx.fs, ctx.sh.cwd
    if len(sources) > 1 and not fs.is_dir(dest, cwd):
        ctx.err(f"cp: target '{dest}' is not a directory")
        return 1
    code = 0
    for src in sources:
        try:
            node = fs.lookup(src, cwd)
        except VFSError as exc:
            ctx.err(f"cp: cannot stat '{src}': {exc.reason}")
            code = 1
            continue
        if node.is_dir and not flags & {"r", "R", "a"}:
            ctx.err(f"cp: -r not specified; omitting directory '{src}'")
            code = 1
            continue
        try:
            parent, name = _dest(ctx, node, dest)
        except VFSError as exc:
            ctx.err(f"cp: cannot create regular file '{dest}': {exc.reason}")
            code = 1
            continue
        if parent.children.get(name) is node:
            ctx.err(f"cp: '{src}' and '{dest}' are the same file")
            code = 1
            continue
        parent.add(fs.copy_node(node, name))
        ctx.sh.on_file_written(parent.path() + "/" + name)
    return code


def cmd_mv(ctx: Ctx):
    try:
        _, _, paths = split_flags(ctx, "fvn")
    except UsageError as exc:
        return ctx.fail(str(exc))
    if not paths:
        ctx.err("mv: missing file operand\nTry 'mv --help' for more information.")
        return 1
    if len(paths) == 1:
        ctx.err(f"mv: missing destination file operand after '{paths[0]}'")
        return 1
    *sources, dest = paths
    fs, cwd = ctx.fs, ctx.sh.cwd
    if len(sources) > 1 and not fs.is_dir(dest, cwd):
        ctx.err(f"mv: target '{dest}' is not a directory")
        return 1
    code = 0
    for src in sources:
        try:
            node = fs.lookup(src, cwd)
            parent, name = _dest(ctx, node, dest)
        except VFSError as exc:
            what = "cannot stat" if not fs.exists(src, cwd) else "cannot move"
            ctx.err(f"mv: {what} '{src}': {exc.reason}" if what == "cannot stat"
                    else f"mv: cannot move '{src}' to '{dest}': {exc.reason}")
            code = 1
            continue
        if parent.children.get(name) is node:
            ctx.err(f"mv: '{src}' and '{dest}' are the same file")
            code = 1
            continue
        probe: Node | None = parent
        while probe is not None:          # can't move a dir inside itself
            if probe is node:
                ctx.err(f"mv: cannot move '{src}' to a subdirectory of itself, '{dest}'")
                code = 1
                break
            probe = probe.parent
        else:
            assert node.parent is not None
            del node.parent.children[node.name]
            node.name = name
            parent.add(node)
            node.mtime = fs.clock
            ctx.sh.on_file_written(node.path())
    return code


def cmd_rm(ctx: Ctx):
    try:
        flags, _, paths = split_flags(ctx, "rRfvi")
    except UsageError as exc:
        return ctx.fail(str(exc))
    if not paths:
        if "f" in flags:
            return 0
        ctx.err("rm: missing operand\nTry 'rm --help' for more information.")
        return 1
    code = 0
    for path in paths:
        try:
            node = ctx.fs.lookup(path, ctx.sh.cwd)
        except VFSError as exc:
            if "f" not in flags:
                ctx.err(f"rm: cannot remove '{path}': {exc.reason}")
                code = 1
            continue
        if node.is_dir and not flags & {"r", "R"}:
            ctx.err(f"rm: cannot remove '{path}': Is a directory")
            code = 1
            continue
        if node.parent is None or node.path() in ("/home", HOME):
            ctx.err(f"rm: it is dangerous to operate recursively on '{path}'")
            code = 1
            continue
        ctx.fs.remove(path, ctx.sh.cwd)
    return code


def cmd_rmdir(ctx: Ctx):
    if not ctx.args:
        ctx.err("rmdir: missing operand")
        return 1
    code = 0
    for path in ctx.args:
        try:
            node = ctx.fs.lookup(path, ctx.sh.cwd)
            if not isinstance(node, Dir):
                raise VFSError("Not a directory", path)
            if node.children:
                raise VFSError("Directory not empty", path)
            ctx.fs.remove(path, ctx.sh.cwd)
        except VFSError as exc:
            ctx.err(f"rmdir: failed to remove '{path}': {exc.reason}")
            code = 1
    return code


# ------------------------------------------------------------------ text
def _unescape(text: str) -> str:
    return (text.replace("\\\\", "\0").replace("\\n", "\n").replace("\\t", "\t")
            .replace("\0", "\\"))


def cmd_echo(ctx: Ctx):
    args = list(ctx.args)
    newline, escapes = True, False
    while args and args[0] in ("-n", "-e", "-ne", "-en"):
        flag = args.pop(0)
        newline = newline and "n" not in flag
        escapes = escapes or "e" in flag
    text = " ".join(args)
    if escapes:
        text = _unescape(text)
    ctx.out(text + ("\n" if newline else ""))


def cmd_printf(ctx: Ctx):
    if not ctx.args:
        ctx.err("printf: usage: printf format [arguments]")
        return 2
    fmt = _unescape(ctx.args[0])
    values = ctx.args[1:]
    try:
        if "%" in fmt:
            n = len(re.findall(r"%[-0-9.]*[sdf]", fmt)) or 1
            rows = [values[i:i + n] for i in range(0, max(len(values), 1), n)]
            for row in rows:
                row = row + [""] * (n - len(row))
                conv = []
                for spec, value in zip(re.findall(r"%[-0-9.]*([sdf])", fmt), row):
                    conv.append(value if spec == "s" else (int(value or 0) if spec == "d" else float(value or 0)))
                ctx.out(fmt % tuple(conv))
        else:
            ctx.out(fmt)
    except (ValueError, TypeError):
        ctx.err("printf: invalid format or number")
        return 1


def _bre_to_python(pattern: str) -> str:
    """Basic regex (plain grep): + ? | ( ) { } are literal unless escaped.
    Python's `re` is 'extended' style, so swap the escaping."""
    out, i = [], 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\" and i + 1 < len(pattern):
            nxt = pattern[i + 1]
            out.append(nxt if nxt in "+?|(){}" else "\\" + nxt)
            i += 2
        elif ch in "+?|(){}":
            out.append("\\" + ch)
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def cmd_grep(ctx: Ctx):
    try:
        flags, values, operands = split_flags(ctx, "invcrRlwEFoqHh", "e")
    except UsageError as exc:
        ctx.err(f"grep: {exc}\nUsage: grep [OPTION]... PATTERNS [FILE]...")
        return 2
    pattern = values.get("e")
    if pattern is None:
        if not operands:
            ctx.err("Usage: grep [OPTION]... PATTERNS [FILE]...\nTry 'grep --help' for more information.")
            return 2
        pattern = operands.pop(0)
    if "F" in flags:
        source = re.escape(pattern)
    else:
        source = pattern if "E" in flags else _bre_to_python(pattern)
    if "w" in flags:
        source = rf"\b(?:{source})\b"
    try:
        regex = re.compile(source, re.IGNORECASE if "i" in flags else 0)
    except re.error:
        ctx.err("grep: Invalid regular expression")
        return 2
    recursive = bool(flags & {"r", "R"})
    targets: list[tuple[str, str]] = []
    failed = False
    fs, cwd = ctx.fs, ctx.sh.cwd
    if not operands and recursive:
        operands = ["."]
    if not operands:
        if ctx.stdin is None:
            ctx.err("grep: nothing to search. Give a file, or pipe text in: `cat file | grep word`")
            return 2
        targets.append(("", ctx.stdin))
    for path in operands:
        try:
            node = fs.lookup(path, cwd)
        except VFSError as exc:
            ctx.err(f"grep: {path}: {exc.reason}")
            failed = True
            continue
        if isinstance(node, Dir):
            if not recursive:
                ctx.err(f"grep: {path}: Is a directory")
                failed = True
                continue
            base = node.path()
            for sub in fs.walk(path, cwd):
                if isinstance(sub, File) and sub.mode & 0o400:
                    rel = sub.path()[len(base):].lstrip("/")
                    label = rel if path == "." else f"{path.rstrip('/')}/{rel}"
                    targets.append((label, sub.content))
        elif not node.mode & 0o400:
            ctx.err(f"grep: {path}: Permission denied")
            failed = True
        else:
            targets.append((path, node.content))  # type: ignore[union-attr]
    with_name = ("H" in flags or len(targets) > 1 or recursive) and "h" not in flags
    found = False
    for label, text in targets:
        count = 0
        for number, line in enumerate(text.splitlines(), 1):
            hit = regex.search(line)
            if bool(hit) == ("v" in flags):
                continue
            count += 1
            found = True
            if flags & {"c", "l", "q"}:
                continue
            body = [m.group(0) for m in regex.finditer(line)] if "o" in flags and "v" not in flags else [line]
            for piece in body:
                prefix = (f"{label}:" if with_name and label else "") + (f"{number}:" if "n" in flags else "")
                ctx.line(prefix + piece)
        if "c" in flags:
            ctx.line((f"{label}:" if with_name and label else "") + str(count))
        elif "l" in flags and count:
            ctx.line(label or "(standard input)")
    if failed:
        return 2
    return 0 if found else 1


def cmd_wc(ctx: Ctx):
    try:
        flags, _, files = split_flags(ctx, "lwcm")
    except UsageError as exc:
        ctx.err(f"wc: {exc}")
        return 1
    cols = [c for c in "lwc" if c in flags or (c == "c" and "m" in flags)] or ["l", "w", "c"]
    rows = []
    for label, text in read_inputs(ctx, files):
        rows.append(({"l": text.count("\n"), "w": len(text.split()), "c": len(text.encode())}, label))
    if not rows:
        return 1
    if len(rows) > 1:
        rows.append(({c: sum(r[0][c] for r in rows) for c in "lwc"}, "total"))
    if len(cols) == 1 and len(rows) == 1:
        width = 1
    elif not files:
        width = 7
    else:
        width = max(len(str(rows[-1][0]["c"])), 1)
    for counts, label in rows:
        ctx.line(" ".join(f"{counts[c]:>{width}}" for c in cols) + (f" {label}" if label else ""))
    return 1 if ctx.failed else 0  # type: ignore[attr-defined]


def _leading_number(text: str) -> float:
    match = re.match(r"\s*-?[0-9]*\.?[0-9]+", text)
    return float(match.group(0)) if match else 0.0


def cmd_sort(ctx: Ctx):
    try:
        flags, values, files = split_flags(ctx, "rnufbh", "kt")
    except UsageError as exc:
        ctx.err(f"sort: {exc}")
        return 2
    lines: list[str] = []
    for _, text in read_inputs(ctx, files, "{cmd}: cannot read: {path}: {reason}"):
        lines.extend(text.splitlines())
    if ctx.failed:  # type: ignore[attr-defined]
        return 2
    sep = values.get("t")
    field = None
    if "k" in values:
        try:
            field = int(values["k"].split(",")[0].split(".")[0])
        except ValueError:
            ctx.err(f"sort: invalid number at field start: invalid count at start of ‘{values['k']}’")
            return 2

    def key(line: str):
        text = line
        if field:
            parts = line.split(sep) if sep else line.split()
            text = (sep or " ").join(parts[field - 1:]) if field <= len(parts) else ""
        if "n" in flags or "h" in flags:
            return (_leading_number(text), line)
        return (text.lower(), text) if "f" in flags else (text, line)

    lines.sort(key=key, reverse="r" in flags)
    if "u" in flags:
        seen, unique = set(), []
        for line in lines:
            k = key(line)[0]
            if k not in seen:
                seen.add(k)
                unique.append(line)
        lines = unique
    for line in lines:
        ctx.line(line)


def cmd_uniq(ctx: Ctx):
    try:
        flags, _, files = split_flags(ctx, "cdui")
    except UsageError as exc:
        ctx.err(f"uniq: {exc}")
        return 1
    lines: list[str] = []
    for _, text in read_inputs(ctx, files[:1]):
        lines = text.splitlines()
    if ctx.failed:  # type: ignore[attr-defined]
        return 1
    groups: list[list] = []
    for line in lines:   # uniq only merges ADJACENT duplicates - that's why you `sort` first
        probe = line.lower() if "i" in flags else line
        if groups and groups[-1][2] == probe:
            groups[-1][1] += 1
        else:
            groups.append([line, 1, probe])
    for line, count, _ in groups:
        if "d" in flags and count < 2 or "u" in flags and count > 1:
            continue
        ctx.line(f"{count:>7} {line}" if "c" in flags else line)


def cmd_cut(ctx: Ctx):
    try:
        _, values, files = split_flags(ctx, "s", "dfc")
    except UsageError as exc:
        ctx.err(f"cut: {exc}")
        return 1
    spec = values.get("f") or values.get("c")
    if not spec:
        ctx.err("cut: you must specify a list of bytes, characters, or fields\n"
                "Try 'cut --help' for more information.")
        return 1
    delim = values.get("d", "\t")
    picks: list[tuple[int, int]] = []
    try:
        for part in spec.split(","):
            lo, dash, hi = part.partition("-")
            start = int(lo) if lo else 1
            end = (int(hi) if hi else 10 ** 6) if dash else start
            picks.append((start, end))
    except ValueError:
        ctx.err(f"cut: invalid field value ‘{spec}’")
        return 1
    for _, text in read_inputs(ctx, files):
        for line in text.splitlines():
            items = list(line) if "c" in values else line.split(delim)
            if "f" in values and delim not in line:
                ctx.line(line)
                continue
            chosen = [item for i, item in enumerate(items, 1) if any(a <= i <= b for a, b in picks)]
            ctx.line(("" if "c" in values else delim).join(chosen))
    return 1 if ctx.failed else 0  # type: ignore[attr-defined]


def cmd_tr(ctx: Ctx):
    args = list(ctx.args)
    delete = bool(args and args[0] == "-d")
    if delete:
        args.pop(0)

    def charset(spec: str) -> str:
        spec = _unescape(spec).replace("[:upper:]", "A-Z").replace("[:lower:]", "a-z").replace("[:digit:]", "0-9")
        return re.sub(r"(.)-(.)", lambda m: "".join(chr(c) for c in range(ord(m.group(1)), ord(m.group(2)) + 1)), spec)

    if not args or (not delete and len(args) < 2):
        ctx.err("tr: missing operand\nTry 'tr --help' for more information.")
        return 1
    text = ctx.stdin or ""
    a = charset(args[0])
    if delete:
        ctx.out("".join(ch for ch in text if ch not in a))
    else:
        b = charset(args[1])
        b = b + b[-1] * (len(a) - len(b))
        ctx.out(text.translate(str.maketrans(a, b[:len(a)])))


def _sed_address(text: str):
    """Parse the optional line selector in front of a sed command:
    '3' (line 3), '2,5' (lines 2-5), '$' (last line), '/regex/'."""
    import re as _re
    match = _re.match(r"(\d+|\$)(?:,(\d+|\$))?", text)
    if match:
        return ("lines", match.group(1), match.group(2) or match.group(1)), text[match.end():]
    if text.startswith("/"):
        end = text.find("/", 1)
        while end > 0 and text[end - 1] == "\\":
            end = text.find("/", end + 1)
        if end < 0:
            raise UsageError("unterminated address regex")
        return ("regex", text[1:end], None), text[end + 1:]
    return None, text


def _sed_compile(script: str, extended: bool):
    """One sed command -> (address, action, data). Supports s/old/new/[gi], d, p."""
    address, rest = _sed_address(script.strip())
    rest = rest.strip()
    if rest[:1] == "s" and len(rest) > 1:
        delim = rest[1]
        parts, current, i = [], "", 2
        while i < len(rest) and len(parts) < 2:
            if rest[i] == "\\" and i + 1 < len(rest):
                current += rest[i + 1] if rest[i + 1] == delim else rest[i:i + 2]
                i += 2
            elif rest[i] == delim:
                parts.append(current)
                current = ""
                i += 1
            else:
                current += rest[i]
                i += 1
        if len(parts) < 2:
            raise UsageError("unterminated `s' command")
        flags = rest[i:]
        if flags.strip("gi"):
            raise UsageError("unknown option to `s'")
        pattern = parts[0] if extended else _bre_to_python(parts[0])
        try:
            regex = re.compile(pattern, re.IGNORECASE if "i" in flags else 0)
        except re.error:
            raise UsageError("Invalid regular expression")
        # sed uses & for "the whole match" and \1 for groups
        repl = re.sub(r"(?<!\\)&", r"\\g<0>", parts[1]).replace("\\&", "&")
        return address, "s", (regex, repl, 0 if "g" in flags else 1)
    if rest in ("d", "p"):
        return address, rest, None
    raise UsageError(f"unknown command: `{rest[:1]}'" if rest else "missing command")


def cmd_sed(ctx: Ctx):
    """Stream editor: the classic find-and-replace tool."""
    args = list(ctx.args)
    in_place = quiet = extended = False
    scripts: list[str] = []
    files: list[str] = []
    while args:
        arg = args.pop(0)
        if arg in ("-i", "--in-place"):
            in_place = True
        elif arg == "-n":
            quiet = True
        elif arg in ("-E", "-r"):
            extended = True
        elif arg == "-e" and args:
            scripts.append(args.pop(0))
        elif arg.startswith("-") and len(arg) > 1:
            ctx.err(f"sed: invalid option -- '{arg[1:]}'")
            return 1
        elif not scripts:
            scripts.append(arg)
        else:
            files.append(arg)
    if not scripts:
        ctx.err("Usage: sed [OPTION]... {script-only-if-no-other-script} [input-file]...")
        return 1
    try:
        commands = [_sed_compile(part, extended) for script in scripts for part in script.split(";") if part.strip()]
    except UsageError as exc:
        ctx.err(f"sed: -e expression #1, char {len(scripts[0])}: {exc}")
        return 1
    if in_place and not files:
        ctx.err("sed: no input files")
        return 4

    def process(text: str) -> str:
        lines = text.splitlines()
        out: list[str] = []
        for number, line in enumerate(lines, 1):
            deleted = False
            for address, action, data in commands:
                if address is not None:
                    kind, a, b = address
                    if kind == "regex":
                        hit = re.search(a if extended else _bre_to_python(a), line) is not None
                    else:
                        lo = len(lines) if a == "$" else int(a)
                        hi = len(lines) if b == "$" else int(b)
                        hit = lo <= number <= hi
                    if not hit:
                        continue
                if action == "d":
                    deleted = True
                    break
                if action == "p":
                    out.append(line)
                else:
                    regex, repl, count = data
                    line = regex.sub(repl, line, count=count)
            if not deleted and not quiet:
                out.append(line)
        return "\n".join(out) + ("\n" if out else "")

    code = 0
    if not files:
        if ctx.stdin is None:
            ctx.err("sed: nothing to read. Give a file, or pipe text in: `cat file | sed 's/a/b/'`")
            return 1
        ctx.out(process(ctx.stdin))
        return 0
    for path in files:
        try:
            text = ctx.fs.read(path, ctx.sh.cwd)
        except VFSError as exc:
            ctx.err(f"sed: can't read {path}: {exc.reason}")
            code = 2
            continue
        if in_place:
            try:
                ctx.fs.write(path, process(text), ctx.sh.cwd)
            except VFSError as exc:
                ctx.err(f"sed: couldn't open temporary file for {path}: {exc.reason}")
                code = 4
                continue
            ctx.sh.on_file_written(ctx.fs.normalize(path, ctx.sh.cwd))
        else:
            ctx.out(process(text))
    return code


def cmd_tee(ctx: Ctx):
    try:
        flags, _, files = split_flags(ctx, "a")
    except UsageError as exc:
        ctx.err(f"tee: {exc}")
        return 1
    text = ctx.stdin or ""
    code = 0
    for path in files:
        try:
            ctx.fs.write(path, text, ctx.sh.cwd, append="a" in flags)
            ctx.sh.on_file_written(ctx.fs.normalize(path, ctx.sh.cwd))
        except VFSError as exc:
            ctx.err(f"tee: {path}: {exc.reason}")
            code = 1
    ctx.out(text)
    return code


def cmd_find(ctx: Ctx):
    args = list(ctx.args)
    paths: list[str] = []
    while args and not args[0].startswith("-"):
        paths.append(args.pop(0))
    tests: list = []
    maxdepth = None
    while args:
        opt = args.pop(0)
        if opt in ("-name", "-iname", "-type", "-maxdepth", "-path"):
            if not args:
                ctx.err(f"find: missing argument to `{opt}'")
                return 1
            value = args.pop(0)
            if opt == "-name":
                tests.append(lambda n, p, v=value: fnmatch.fnmatchcase(n.name or "/", v))
            elif opt == "-iname":
                tests.append(lambda n, p, v=value.lower(): fnmatch.fnmatchcase(n.name.lower(), v))
            elif opt == "-path":
                tests.append(lambda n, p, v=value: fnmatch.fnmatchcase(p, v))
            elif opt == "-type":
                if value not in ("f", "d"):
                    ctx.err(f"find: Unknown argument to -type: {value}")
                    return 1
                tests.append(lambda n, p, v=value: n.is_dir == (v == "d"))
            else:
                if not value.isdigit():
                    ctx.err(f"find: Expected a positive decimal integer argument to -maxdepth, but got ‘{value}’")
                    return 1
                maxdepth = int(value)
        elif opt == "-print":
            continue
        else:
            ctx.err(f"find: unknown predicate `{opt}'")
            return 1
    code = 0
    for start in paths or ["."]:
        try:
            root = ctx.fs.lookup(start, ctx.sh.cwd)
        except VFSError as exc:
            ctx.err(f"find: ‘{start}’: {exc.reason}")
            code = 1
            continue
        base = root.path()
        for node in ctx.fs.walk(start, ctx.sh.cwd):
            rel = node.path()[len(base):].lstrip("/")
            depth = rel.count("/") + 1 if rel else 0
            if maxdepth is not None and depth > maxdepth:
                continue
            shown = start.rstrip("/") + "/" + rel if rel else start
            if start == "/" and rel:
                shown = "/" + rel
            if all(test(node, shown) for test in tests):
                ctx.line(shown)
    return code


def cmd_xargs(ctx: Ctx):
    """Turn stdin into ARGUMENTS for another command: `find . -name '*.md' | xargs grep -l pricing`."""
    argv = list(ctx.args) or ["echo"]
    items = (ctx.stdin or "").split()
    if not items:
        return 0
    sub = Ctx(ctx.sh, argv[0], argv[1:] + items, None, ctx.piped)
    code = ctx.sh._dispatch(sub)
    ctx.out_parts.extend(sub.out_parts)
    ctx.err_parts.extend(sub.err_parts)
    return code


def cmd_seq(ctx: Ctx):
    try:
        nums = [int(a) for a in ctx.args]
    except ValueError:
        return ctx.fail("invalid argument")
    if not nums:
        return ctx.fail("missing operand")
    lo, hi = (1, nums[0]) if len(nums) == 1 else (nums[0], nums[-1])
    for i in range(lo, hi + 1):
        ctx.line(str(i))


def cmd_basename(ctx: Ctx):
    if not ctx.args:
        return ctx.fail("missing operand")
    name = ctx.args[0].rstrip("/").rpartition("/")[2]
    if len(ctx.args) > 1 and name.endswith(ctx.args[1]):
        name = name[:-len(ctx.args[1])]
    ctx.line(name)


def cmd_dirname(ctx: Ctx):
    if not ctx.args:
        return ctx.fail("missing operand")
    head = ctx.args[0].rstrip("/").rpartition("/")[0]
    ctx.line(head or ("/" if ctx.args[0].startswith("/") else "."))


# ------------------------------------------------------- shell built-ins
def cmd_history(ctx: Ctx):
    sh = ctx.sh
    if ctx.args[:1] == ["-c"]:
        sh.history.clear()
        return 0
    items = list(enumerate(sh.history, 1))
    if ctx.args and ctx.args[0].isdigit():
        items = items[-int(ctx.args[0]):]
    for number, line in items:
        ctx.line(f"{number:>5}  {line}")


def cmd_env(ctx: Ctx):
    sh = ctx.sh
    if ctx.name == "printenv" and ctx.args:
        code = 0
        for name in ctx.args:
            if name in sh.env:
                ctx.line(sh.env[name])
            else:
                code = 1
        return code
    for name in sorted(sh.exported):
        if name in sh.env:
            ctx.line(f"{name}={sh.env[name]}")


def cmd_export(ctx: Ctx):
    sh = ctx.sh
    if not ctx.args:
        for name in sorted(sh.exported):
            if name in sh.env:
                ctx.line(f'declare -x {name}="{sh.env[name]}"')
        return 0
    for arg in ctx.args:
        name, eq, value = arg.partition("=")
        if not name.replace("_", "a").isalnum() or name[0].isdigit():
            ctx.err(f"bash: export: `{arg}': not a valid identifier")
            return 1
        if eq:
            sh.env[name] = value
        sh.exported.add(name)
    sh.on_use("variables", True)


def cmd_unset(ctx: Ctx):
    for name in ctx.args:
        ctx.sh.env.pop(name, None)
        ctx.sh.exported.discard(name)


def cmd_alias(ctx: Ctx):
    sh = ctx.sh
    if not ctx.args:
        for name, value in sorted(sh.aliases.items()):
            ctx.line(f"alias {name}='{value}'")
        return 0
    code = 0
    for arg in ctx.args:
        name, eq, value = arg.partition("=")
        if eq:
            sh.aliases[name] = value
        elif name in sh.aliases:
            ctx.line(f"alias {name}='{sh.aliases[name]}'")
        else:
            ctx.err(f"bash: alias: {name}: not found")
            code = 1
    return code


def cmd_unalias(ctx: Ctx):
    code = 0
    for name in ctx.args:
        if ctx.sh.aliases.pop(name, None) is None:
            ctx.err(f"bash: unalias: {name}: not found")
            code = 1
    return code


BUILTINS = {"cd", "pwd", "echo", "export", "unset", "alias", "unalias", "history", "exit",
            "source", ".", "type", "test", "[", "true", "false", "help", "printf"}


def cmd_which(ctx: Ctx):
    code = 0
    for name in ctx.args:
        cmd = ctx.sh.commands.get(name)
        if ctx.name == "type":
            if name in ctx.sh.aliases:
                ctx.line(f"{name} is aliased to `{ctx.sh.aliases[name]}'")
            elif cmd is None:
                ctx.err(f"bash: type: {name}: not found")
                code = 1
            elif name in BUILTINS:
                ctx.line(f"{name} is a shell builtin")
            else:
                ctx.line(f"{name} is {'/usr/bin' if cmd.kind == 'bash' else '/usr/local/bin'}/{name}")
        elif cmd is None or name in BUILTINS - {"echo", "pwd", "test", "[", "true", "false", "printf"}:
            code = 1
        else:
            ctx.line(f"{'/usr/bin' if cmd.kind == 'bash' else '/usr/local/bin'}/{name}")
    return code


def cmd_chmod(ctx: Ctx):
    args = [a for a in ctx.args if a not in ("-R", "-v")]
    recursive = "-R" in ctx.args
    if len(args) < 2:
        ctx.err("chmod: missing operand" + (f" after ‘{args[0]}’" if args else "")
                + "\nTry 'chmod --help' for more information.")
        return 1
    spec, paths = args[0], args[1:]

    def apply(mode: int) -> int:
        if re.fullmatch(r"[0-7]{3,4}", spec):
            return int(spec, 8)
        for clause in spec.split(","):
            match = re.fullmatch(r"([ugoa]*)([+\-=])([rwxX]*)", clause)
            if not match:
                raise ValueError
            who, op, perms = match.groups()
            who = "ugo" if who in ("", "a") else who
            bits = sum({"r": 4, "w": 2, "x": 1, "X": 1}[p] for p in set(perms))
            for w in who:
                shift = {"u": 6, "g": 3, "o": 0}.get(w)
                if shift is None:
                    continue
                if op == "+":
                    mode |= bits << shift
                elif op == "-":
                    mode &= ~(bits << shift)
                else:
                    mode = (mode & ~(7 << shift)) | (bits << shift)
        return mode

    code = 0
    for path in paths:
        try:
            node = ctx.fs.lookup(path, ctx.sh.cwd)
        except VFSError as exc:
            ctx.err(f"chmod: cannot access '{path}': {exc.reason}")
            code = 1
            continue
        targets = list(ctx.fs.walk(path, ctx.sh.cwd)) if recursive else [node]
        for target in targets:
            try:
                target.mode = apply(target.mode)
            except ValueError:
                ctx.err(f"chmod: invalid mode: ‘{spec}’\nTry 'chmod --help' for more information.")
                return 1
    return code


def cmd_whoami(ctx: Ctx):
    ctx.line(ctx.sh.env.get("USER", "founder"))


def cmd_hostname(ctx: Ctx):
    ctx.line(ctx.sh.env.get("HOSTNAME", "startup"))


def cmd_date(ctx: Ctx):
    d = game_date(ctx.fs.clock)
    ctx.line(f"{d.strftime('%a %b')} {d.day:>2} 09:00:00 CET {d.year}")


def cmd_clear(ctx: Ctx):
    if not ctx.piped:
        ctx.sh.io.console.clear()


def cmd_true(ctx: Ctx):
    return 0


def cmd_false(ctx: Ctx):
    return 1


def cmd_sleep(ctx: Ctx):
    return 0   # time only moves with the game's `next` command


def cmd_exit(ctx: Ctx):
    ctx.sh.exit_requested = True
    return 0


def cmd_test(ctx: Ctx):
    """`test` / `[ ... ]`: the condition checker used by `if`."""
    args = list(ctx.args)
    if ctx.name == "[":
        if not args or args[-1] != "]":
            ctx.err("bash: [: missing `]'")
            return 2
        args.pop()
    negate = False
    if args and args[0] == "!":
        negate, args = True, args[1:]
    fs, cwd = ctx.fs, ctx.sh.cwd
    try:
        if len(args) == 0:
            result = False
        elif len(args) == 1:
            result = args[0] != ""
        elif len(args) == 2:
            op, value = args
            result = {"-f": lambda: fs.is_file(value, cwd), "-d": lambda: fs.is_dir(value, cwd),
                      "-e": lambda: fs.exists(value, cwd), "-z": lambda: value == "",
                      "-n": lambda: value != "",
                      "-s": lambda: fs.is_file(value, cwd) and bool(fs.read(value, cwd)),
                      "-x": lambda: fs.exists(value, cwd) and bool(fs.lookup(value, cwd).mode & 0o100),
                      }[op]()
        else:
            left, op, right = args[:3]
            if op in ("=", "=="):
                result = left == right
            elif op == "!=":
                result = left != right
            else:
                a, b = int(left), int(right)
                result = {"-eq": a == b, "-ne": a != b, "-gt": a > b, "-ge": a >= b,
                          "-lt": a < b, "-le": a <= b}[op]
    except (KeyError, ValueError):
        ctx.err(f"bash: {ctx.name}: {' '.join(args)}: unknown or malformed condition")
        return 2
    return 0 if result != negate else 1


def cmd_bash(ctx: Ctx):
    """bash FILE / sh FILE / source FILE: run a script's commands."""
    args = [a for a in ctx.args if not a.startswith("-")]
    if not args:
        if ctx.stdin is not None:
            return ctx.sh.run_script(ctx.stdin, [ctx.name], ctx)
        ctx.err(f"{ctx.name}: you are already in a shell. Give it a script: `{ctx.name} myscript.sh`")
        return 1
    try:
        text = ctx.fs.read(args[0], ctx.sh.cwd)
    except VFSError as exc:
        ctx.err(f"{ctx.name}: {args[0]}: {exc.reason}")
        return 127
    code = ctx.sh.run_script(text, args, ctx)
    ctx.sh.on_use("script", code == 0)
    return code


def cmd_nano(ctx: Ctx):
    """A tiny stand-in for a text editor."""
    if not ctx.args:
        ctx.err("nano: give a file name, e.g. `nano product/specs/login.md`")
        return 1
    path = ctx.args[0]
    fs, cwd = ctx.fs, ctx.sh.cwd
    try:
        text = fs.read(path, cwd) if fs.exists(path, cwd) else ""
        fs._parent_and_name(path, cwd)
    except VFSError as exc:
        ctx.err(f"nano: {path}: {exc.reason}")
        return 1
    new = ctx.sh.io.edit(text, path)
    if new is None:
        ctx.err("nano: nothing saved. (Needs an interactive terminal. "
                "Alternative: `echo 'a line' >> file` appends a line.)")
        return 1
    if not new.endswith("\n"):
        new += "\n"
    try:
        fs.write(path, new, cwd)
    except VFSError as exc:
        ctx.err(f"nano: {path}: {exc.reason}")
        return 1
    ctx.sh.on_file_written(fs.normalize(path, cwd))


def cmd_man(ctx: Ctx):
    pages = getattr(ctx.sh, "manpages", {})
    if not ctx.args:
        ctx.err("What manual page do you want?\nFor example, try 'man ls'.")
        return 1
    name = ctx.args[0]
    cmd = ctx.sh.commands.get(name)
    key = cmd.name if cmd else name
    if key not in pages:
        ctx.err(f"No manual entry for {name}")
        return 16
    text = pages[key].strip("\n") + "\n"
    if ctx.piped:
        ctx.out(text)
    else:
        ctx.sh.io.page(text)


def register_coreutils(sh: Shell) -> None:
    table = [
        ("pwd", cmd_pwd, "print the current directory"), ("cd", cmd_cd, "change directory"),
        ("ls", cmd_ls, "list directory contents"), ("tree", cmd_tree, "show a directory as a tree"),
        ("cat", cmd_cat, "print file contents"), ("less", cmd_less, "read a long file page by page"),
        ("more", cmd_less, "like less"), ("head", cmd_head, "first lines of a file"),
        ("tail", cmd_tail, "last lines of a file"), ("mkdir", cmd_mkdir, "make directories"),
        ("touch", cmd_touch, "create an empty file"), ("cp", cmd_cp, "copy files"),
        ("mv", cmd_mv, "move or rename files"), ("rm", cmd_rm, "remove files"),
        ("rmdir", cmd_rmdir, "remove empty directories"), ("echo", cmd_echo, "print text"),
        ("printf", cmd_printf, "formatted print"), ("grep", cmd_grep, "search text for a pattern"),
        ("wc", cmd_wc, "count lines, words, bytes"), ("sort", cmd_sort, "sort lines"),
        ("uniq", cmd_uniq, "collapse adjacent duplicate lines"), ("cut", cmd_cut, "pick columns"),
        ("tr", cmd_tr, "translate characters"), ("sed", cmd_sed, "find and replace text (stream editor)"), ("tee", cmd_tee, "write stdin to a file AND stdout"),
        ("find", cmd_find, "search for files by name/type"), ("xargs", cmd_xargs, "stdin -> arguments"),
        ("seq", cmd_seq, "print a sequence of numbers"), ("basename", cmd_basename, "strip directory"),
        ("dirname", cmd_dirname, "strip last path part"), ("history", cmd_history, "show past commands"),
        ("env", cmd_env, "show environment variables"), ("printenv", cmd_env, "show environment variables"),
        ("export", cmd_export, "set an environment variable"), ("unset", cmd_unset, "remove a variable"),
        ("alias", cmd_alias, "define a shortcut"), ("unalias", cmd_unalias, "remove a shortcut"),
        ("which", cmd_which, "where a command lives"), ("type", cmd_which, "what kind of command"),
        ("chmod", cmd_chmod, "change file permissions"), ("whoami", cmd_whoami, "current user"),
        ("hostname", cmd_hostname, "machine name"), ("date", cmd_date, "current (game) date"),
        ("clear", cmd_clear, "clear the screen"), ("true", cmd_true, "succeed"),
        ("false", cmd_false, "fail"), ("sleep", cmd_sleep, "wait"), ("exit", cmd_exit, "leave the game"),
        ("logout", cmd_exit, "leave the game"), ("test", cmd_test, "check a condition"),
        ("[", cmd_test, "check a condition"), ("bash", cmd_bash, "run a script"),
        ("sh", cmd_bash, "run a script"), ("source", cmd_bash, "run a script in this shell"),
        (".", cmd_bash, "run a script in this shell"), ("nano", cmd_nano, "edit a file"),
        ("man", cmd_man, "show the manual for a command"),
    ]
    for name, fn, summary in table:
        sh.register(name, fn, "bash", summary)
