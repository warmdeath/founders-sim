"""Save and load a run (JSON on the real disk, in ~/.founders_sim/)."""
from __future__ import annotations

import json

from .vfs import VFS
from .learn.profile import Profile, data_dir
from .game.state import save_game_dict, load_game_dict
from .game.session import Session
from .ui.io import IO


def save_path():
    return data_dir() / "save.json"


def save(s: Session) -> None:
    data = {"version": 1, "game": save_game_dict(s.game), "fs": s.fs.to_dict()}
    if s.shell is not None:
        data["shell"] = {"cwd": s.shell.cwd, "env": s.shell.env, "aliases": s.shell.aliases,
                         "exported": sorted(s.shell.exported)}
    tmp = save_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(save_path())          # atomic: never leaves a half-written save
    s.profile.save()


def has_save() -> bool:
    return save_path().exists()


def load(io: IO, profile: Profile) -> tuple[Session, dict] | None:
    """Returns (session, saved shell state) or None if the save is unreadable."""
    try:
        data = json.loads(save_path().read_text())
        session = Session(load_game_dict(data["game"]), VFS.from_dict(data["fs"]), io, profile)
        return session, data.get("shell", {})
    except (OSError, ValueError, KeyError, TypeError):
        return None


def delete_save() -> None:
    if save_path().exists():
        save_path().unlink()
