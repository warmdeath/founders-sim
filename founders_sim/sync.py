"""Sync your save and learner profile between computers with git.

How it works (only if ~/.founders_sim is a git repository - see the README,
"Playing on two computers"):

    game starts   ->  commit anything not yet synced, then `git pull --rebase`
    save / quit   ->  `git commit` + `git push`
    run ends      ->  `git commit` + `git push` (the profile keeps your progress)

The weekly autosave stays local; it is pushed at the next save or quit.
If both computers changed the save, you choose which one to keep; the
other copy is kept in conflict-backup/ (never synced).

This is the ONLY place the game runs a real program on your computer, and
only `git`, only inside the save folder.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

from .learn.profile import data_dir
from .ui.io import IO

GITIGNORE = "# Founder's Sim: local-only files (not synced)\nhistory\n*.tmp\nconflict-backup/\nbackup-*/\n"
TIMEOUT = 30          # seconds; a slow network must not freeze the game forever


def _git(args: list[str], directory: Path | None = None) -> subprocess.CompletedProcess:
    directory = directory or data_dir()
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")     # never hang asking for a password mid-game
    try:
        return subprocess.run(["git", "-C", str(directory), *args], capture_output=True, text=True,
                              timeout=TIMEOUT, env=env)
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, 127, "", "git is not installed (sudo apt install git)")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", f"git did not answer within {TIMEOUT} seconds")


def _why(result: subprocess.CompletedProcess) -> str:
    """The most useful line of git's error output."""
    lines = [l.strip() for l in (result.stderr or result.stdout).splitlines() if l.strip()]
    for line in lines:
        if line.startswith(("fatal:", "error:")):
            return line
    return lines[-1] if lines else f"git exited with code {result.returncode}"


def enabled() -> bool:
    if os.environ.get("FOUNDERS_SIM_SYNC", "").lower() in ("0", "off", "no"):
        return False
    return (data_dir() / ".git").is_dir()


def _has_upstream() -> bool:
    return _git(["rev-parse", "--abbrev-ref", "@{u}"]).returncode == 0


def _commit(message: str) -> bool:
    """Commit everything in the save folder. Returns True if there was something to commit."""
    _git(["add", "-A"])
    if _git(["diff", "--cached", "--quiet"]).returncode == 0:
        return False
    identity = []
    if not _git(["config", "user.email"]).stdout.strip():      # a fresh machine may have no git identity yet
        identity = ["-c", "user.name=Founder's Sim", "-c", "user.email=founders-sim@localhost"]
    _git([*identity, "commit", "-q", "-m", message])
    return True


def _label(what: str) -> str:
    return f"{what} on {socket.gethostname()} at {time.strftime('%Y-%m-%d %H:%M')}"


def pull(io: IO) -> None:
    """At start: bring in the save from the other computer."""
    if not enabled():
        return
    if not _has_upstream():
        io.print("[warn]Sync: the save folder is a git repo but has no remote branch to pull from. "
                 "Run `python3 -m founders_sim --sync-setup <repo url>`.[/warn]")
        return
    _commit(_label("unsynced changes"))
    result = _git(["pull", "--rebase", "-q"])
    if result.returncode == 0:
        io.print("[dim]Sync: save is up to date with your other computer.[/dim]")
        return
    if (data_dir() / ".git" / "rebase-merge").exists() or (data_dir() / ".git" / "rebase-apply").exists():
        _git(["rebase", "--abort"])
        _resolve_conflict(io)
        return
    io.print(f"[warn]Sync: could not pull ({_why(result)}). Playing with this computer's save; "
             "it will be pushed when you save or quit.[/warn]")


def _resolve_conflict(io: IO) -> None:
    """Both computers changed the save since the last sync."""
    folder = data_dir()
    backup = folder / "conflict-backup" / time.strftime("%Y%m%d-%H%M%S")
    pick = io.choose("Sync conflict: you played on BOTH computers without syncing in between. Which save do you keep?",
                     ["The one from the other computer (this computer's copy goes to conflict-backup/)",
                      "The one on this computer (it replaces the other computer's save)"])
    backup.mkdir(parents=True, exist_ok=True)
    if pick == 0:
        for name in ("save.json", "profile.json"):
            if (folder / name).exists():
                shutil.copy2(folder / name, backup / name)
        _git(["reset", "-q", "--hard", "@{u}"])
        io.print(f"[good]Sync: using the other computer's save.[/good] [dim]This computer's copy: {backup}[/dim]")
    else:
        other = _git(["show", "@{u}:save.json"])
        if other.returncode == 0:
            (backup / "save.json").write_text(other.stdout)
        result = _git(["push", "-q", "--force-with-lease"])
        if result.returncode == 0:
            io.print(f"[good]Sync: kept this computer's save and uploaded it.[/good] [dim]The other copy: {backup}[/dim]")
        else:
            io.print(f"[warn]Sync: kept this computer's save, but uploading failed ({_why(result)}).[/warn]")


def push(io: IO, what: str = "save") -> None:
    """After save / quit / end of a run: send it to the other computer."""
    if not enabled():
        return
    _commit(_label(what))
    if not _has_upstream():
        return
    result = _git(["push", "-q"])
    if result.returncode != 0:                      # the other computer pushed first: rebase on top and retry
        if _git(["pull", "--rebase", "-q"]).returncode == 0:
            result = _git(["push", "-q"])
        else:
            _git(["rebase", "--abort"])
    if result.returncode == 0:
        io.print("[dim]Sync: pushed - your other computer will get this save when you start the game there.[/dim]")
    else:
        io.print(f"[warn]Sync: saved on this computer, but could not push ({_why(result)}). "
                 "It will be retried next time.[/warn]")


def setup(io: IO, url: str) -> int:
    """`--sync-setup URL`: turn the save folder into a clone of a (private) git repo.
    First computer: uploads the current save. Second computer: downloads it
    (an existing local save is moved to backup-<time>/ first)."""
    folder = data_dir()
    probe = _git(["ls-remote", url], folder)
    if probe.returncode != 0:
        io.print(f"[bad]Can't reach {url}: {_why(probe)}[/bad]\n"
                 "Check the address, that the repo exists, and that git can log in to GitHub (see the README).")
        return 1
    if not (folder / ".git").is_dir():
        _git(["init", "-q", "-b", "main"], folder)
    if _git(["remote", "get-url", "origin"], folder).returncode == 0:
        _git(["remote", "set-url", "origin", url], folder)
    else:
        _git(["remote", "add", "origin", url], folder)
    (folder / ".gitignore").write_text(GITIGNORE)
    if not probe.stdout.strip():                     # empty repo: this is the first computer
        _commit(_label("first sync"))
        result = _git(["push", "-q", "-u", "origin", "HEAD:main"], folder)
        _git(["branch", "-q", "--set-upstream-to=origin/main"], folder)
        if result.returncode != 0:
            io.print(f"[bad]Could not push: {_why(result)}[/bad]")
            return 1
        io.print("[good]Sync is set up.[/good] This computer's save and profile are now in the repo.\n"
                 f"On your other computer run:  python3 -m founders_sim --sync-setup {url}")
        return 0
    fetch = _git(["fetch", "-q", "origin"], folder)
    if fetch.returncode != 0:
        io.print(f"[bad]Could not download: {_why(fetch)}[/bad]")
        return 1
    local = [name for name in ("save.json", "profile.json") if (folder / name).exists()]
    if local:
        backup = folder / f"backup-{time.strftime('%Y%m%d-%H%M%S')}"
        backup.mkdir()
        for name in local:
            shutil.move(str(folder / name), backup / name)
        io.print(f"[dim]This computer's previous save was moved to {backup}[/dim]")
    branch = "main" if _git(["rev-parse", "--verify", "-q", "origin/main"], folder).returncode == 0 else "master"
    result = _git(["checkout", "-q", "-f", "-B", branch, f"origin/{branch}"], folder)
    if result.returncode != 0:
        io.print(f"[bad]Could not check out the synced save: {_why(result)}[/bad]")
        return 1
    _git(["branch", "-q", f"--set-upstream-to=origin/{branch}"], folder)
    if not (folder / ".gitignore").exists():
        (folder / ".gitignore").write_text(GITIGNORE)
    io.print("[good]Sync is set up.[/good] You now have the save from your other computer. "
             "From now on the game pulls when it starts and pushes when you save or quit.")
    return 0
