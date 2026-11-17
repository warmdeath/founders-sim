"""The virtual filesystem (VFS).

The whole company lives in a tree of Python objects, NOT on your real disk.
Every simulated bash command (ls, cat, rm ...) only ever touches this tree,
which is what makes the game a safe sandbox.

Beginner reading guide:
    Node  - anything that has a name (a file or a directory)
    File  - a Node with text `content`
    Dir   - a Node with `children` (a dict: name -> Node)
    VFS   - the tree plus helpers that turn a path string like
            "../finance/metrics.csv" into the Node it points to.
"""
from __future__ import annotations

HOME = "/home/founder"
COMPANY = HOME + "/company"


class VFSError(Exception):
    """Raised with the same wording real bash tools print, e.g.
    'No such file or directory'. Commands prefix it with their own name."""

    def __init__(self, reason: str, path: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.path = path


class Node:
    def __init__(self, name: str, mode: int):
        self.name = name
        self.mode = mode          # unix permission bits, e.g. 0o644
        self.mtime = 0            # game week of last modification
        self.parent: Dir | None = None

    @property
    def is_dir(self) -> bool:
        return isinstance(self, Dir)

    def path(self) -> str:
        parts = []
        node: Node | None = self
        while node is not None and node.parent is not None:
            parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    def mode_string(self) -> str:
        """0o644 -> '-rw-r--r--' (what `ls -l` shows)."""
        out = "d" if self.is_dir else "-"
        for shift in (6, 3, 0):
            bits = (self.mode >> shift) & 7
            out += ("r" if bits & 4 else "-") + ("w" if bits & 2 else "-") + ("x" if bits & 1 else "-")
        return out


class File(Node):
    def __init__(self, name: str, content: str = "", mode: int = 0o644):
        super().__init__(name, mode)
        self.content = content

    @property
    def size(self) -> int:
        return len(self.content.encode("utf-8"))


class Dir(Node):
    def __init__(self, name: str, mode: int = 0o755):
        super().__init__(name, mode)
        self.children: dict[str, Node] = {}

    @property
    def size(self) -> int:
        return 4096

    def add(self, node: Node) -> Node:
        node.parent = self
        self.children[node.name] = node
        return node


class VFS:
    def __init__(self):
        self.root = Dir("")
        self.clock = 0  # current game week, stamped on files when they change
        self.mkdir(COMPANY, parents=True)
        self.mkdir("/dev")
        self.write("/dev/null", "", mode=0o666)     # the bit bucket: anything written here disappears

    # ---------------------------------------------------------------- paths
    @staticmethod
    def normalize(path: str, cwd: str = "/") -> str:
        """Turn any path (relative, with . and ..) into a clean absolute one."""
        if not path.startswith("/"):
            path = cwd.rstrip("/") + "/" + path
        parts: list[str] = []
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)
        return "/" + "/".join(parts)

    def lookup(self, path: str, cwd: str = "/") -> Node:
        """Return the node at `path` or raise VFSError like bash would."""
        node: Node = self.root
        for part in self.normalize(path, cwd).split("/"):
            if not part:
                continue
            if not isinstance(node, Dir):
                raise VFSError("Not a directory", path)
            if part not in node.children:
                raise VFSError("No such file or directory", path)
            node = node.children[part]
        if path.endswith("/") and not node.is_dir:
            raise VFSError("Not a directory", path)
        return node

    def exists(self, path: str, cwd: str = "/") -> bool:
        try:
            self.lookup(path, cwd)
            return True
        except VFSError:
            return False

    def is_dir(self, path: str, cwd: str = "/") -> bool:
        try:
            return self.lookup(path, cwd).is_dir
        except VFSError:
            return False

    def is_file(self, path: str, cwd: str = "/") -> bool:
        try:
            return not self.lookup(path, cwd).is_dir
        except VFSError:
            return False

    def _parent_and_name(self, path: str, cwd: str) -> tuple[Dir, str]:
        full = self.normalize(path, cwd)
        if full == "/":
            raise VFSError("File exists", path)
        parent_path, _, name = full.rpartition("/")
        parent = self.lookup(parent_path or "/")
        if not isinstance(parent, Dir):
            raise VFSError("Not a directory", path)
        return parent, name

    # ------------------------------------------------------------ file ops
    def read(self, path: str, cwd: str = "/") -> str:
        node = self.lookup(path, cwd)
        if isinstance(node, Dir):
            raise VFSError("Is a directory", path)
        if not node.mode & 0o400:
            raise VFSError("Permission denied", path)
        return node.content  # type: ignore[union-attr]

    def write(self, path: str, content: str, cwd: str = "/", append: bool = False,
              mode: int | None = None, force: bool = False) -> File:
        """Create or overwrite a file. `force` lets the GAME write files the
        player made read-only; player commands never pass it."""
        parent, name = self._parent_and_name(path, cwd)
        node = parent.children.get(name)
        if isinstance(node, File) and node.path() == "/dev/null":
            return node
        if isinstance(node, Dir):
            raise VFSError("Is a directory", path)
        if node is None:
            node = parent.add(File(name, "", mode if mode is not None else 0o644))
        elif not force and not node.mode & 0o200:
            raise VFSError("Permission denied", path)
        assert isinstance(node, File)
        node.content = node.content + content if append else content
        if mode is not None:
            node.mode = mode
        node.mtime = self.clock
        return node

    def mkdir(self, path: str, cwd: str = "/", parents: bool = False) -> Dir:
        full = self.normalize(path, cwd)
        if parents:
            node: Node = self.root
            for part in full.split("/"):
                if not part:
                    continue
                assert isinstance(node, Dir)
                child = node.children.get(part)
                if child is None:
                    child = node.add(Dir(part))
                    child.mtime = self.clock
                elif not child.is_dir:
                    raise VFSError("File exists", path)
                node = child
            return node  # type: ignore[return-value]
        parent, name = self._parent_and_name(path, cwd)
        if name in parent.children:
            raise VFSError("File exists", path)
        new = parent.add(Dir(name))
        new.mtime = self.clock
        return new  # type: ignore[return-value]

    def remove(self, path: str, cwd: str = "/") -> None:
        node = self.lookup(path, cwd)
        if node.parent is None:
            raise VFSError("Permission denied", path)
        del node.parent.children[node.name]

    def copy_node(self, node: Node, new_name: str) -> Node:
        if isinstance(node, File):
            clone: Node = File(new_name, node.content, node.mode)
        else:
            clone = Dir(new_name, node.mode)
            for child in node.children.values():  # type: ignore[union-attr]
                clone.add(self.copy_node(child, child.name))  # type: ignore[union-attr]
        clone.mtime = self.clock
        return clone

    def walk(self, path: str = "/", cwd: str = "/"):
        """Yield every node under `path` (depth-first, sorted), like `find`."""
        start = self.lookup(path, cwd)
        stack = [start]
        while stack:
            node = stack.pop()
            yield node
            if isinstance(node, Dir):
                stack.extend(sorted(node.children.values(), key=lambda n: n.name, reverse=True))

    def listdir(self, path: str, cwd: str = "/") -> list[Node]:
        node = self.lookup(path, cwd)
        if not isinstance(node, Dir):
            raise VFSError("Not a directory", path)
        return sorted(node.children.values(), key=lambda n: n.name)

    # ------------------------------------------------------- save / restore
    def to_dict(self) -> dict:
        def dump(node: Node) -> dict:
            if isinstance(node, File):
                return {"t": "f", "m": node.mode, "w": node.mtime, "c": node.content}
            return {"t": "d", "m": node.mode, "w": node.mtime,
                    "k": {n: dump(c) for n, c in node.children.items()}}  # type: ignore[union-attr]
        return {"clock": self.clock, "root": dump(self.root)}

    @classmethod
    def from_dict(cls, data: dict) -> "VFS":
        def load(name: str, d: dict) -> Node:
            if d["t"] == "f":
                node: Node = File(name, d["c"], d["m"])
            else:
                node = Dir(name, d["m"])
                for child_name, child in d["k"].items():
                    node.add(load(child_name, child))  # type: ignore[union-attr]
            node.mtime = d["w"]
            return node
        fs = cls()
        fs.root = load("", data["root"])  # type: ignore[assignment]
        fs.clock = data["clock"]
        return fs
