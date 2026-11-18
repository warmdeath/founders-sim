"""Syncing the save between two computers through a git repo.

Uses a local bare repository as the 'GitHub' remote and two save folders
as the desktop and the laptop - no network needed."""
import json
import subprocess

import pytest

from founders_sim import sync
from founders_sim.ui.io import ScriptedIO

pytestmark = pytest.mark.skipif(subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
                                reason="git not installed")


@pytest.fixture
def two_computers(tmp_path, monkeypatch):
    remote = tmp_path / "saves.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    desktop, laptop = tmp_path / "desktop", tmp_path / "laptop"
    desktop.mkdir()
    laptop.mkdir()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))   # no identity: tests the fallback

    def on(computer):
        monkeypatch.setenv("FOUNDERS_SIM_HOME", str(computer))
        return computer
    return str(remote), desktop, laptop, on


def write_save(folder, week):
    (folder / "save.json").write_text(json.dumps({"week": week}))
    (folder / "profile.json").write_text(json.dumps({"runs": week // 10}))


def week_in(folder):
    return json.loads((folder / "save.json").read_text())["week"]


def test_sync_is_off_without_a_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDERS_SIM_HOME", str(tmp_path))
    io = ScriptedIO()
    sync.pull(io)
    sync.push(io)
    assert io.output() == "" and not sync.enabled()


def test_setup_then_save_on_one_computer_and_continue_on_the_other(two_computers):
    remote, desktop, laptop, on = two_computers
    on(desktop)
    write_save(desktop, 5)
    io = ScriptedIO()
    assert sync.setup(io, remote) == 0 and "Sync is set up" in io.output()

    on(laptop)
    write_save(laptop, 1)                          # an old local save gets backed up, not lost
    assert sync.setup(ScriptedIO(), remote) == 0
    assert week_in(laptop) == 5
    assert any(p.name.startswith("backup-") for p in laptop.iterdir())

    write_save(laptop, 9)                          # play on the laptop, quit
    sync.push(ScriptedIO(), "quit")
    (laptop / "history").write_text("ls\n")        # history stays local

    on(desktop)
    io = ScriptedIO()
    sync.pull(io)                                  # start the game on the desktop
    assert week_in(desktop) == 9 and "up to date" in io.output()
    assert not (desktop / "history").exists()


def test_conflict_lets_you_choose_and_keeps_a_backup(two_computers):
    remote, desktop, laptop, on = two_computers
    on(desktop)
    write_save(desktop, 5)
    sync.setup(ScriptedIO(), remote)
    on(laptop)
    sync.setup(ScriptedIO(), remote)

    write_save(laptop, 12)                         # played on the laptop and pushed
    sync.push(ScriptedIO())
    on(desktop)
    write_save(desktop, 7)                         # ...and on the desktop without pulling first

    sync.pull(ScriptedIO(answers=[0]))             # take the other computer's save
    assert week_in(desktop) == 12
    backups = list((desktop / "conflict-backup").glob("*/save.json"))
    assert backups and json.loads(backups[0].read_text())["week"] == 7

    write_save(desktop, 20)
    sync.push(ScriptedIO())
    on(laptop)
    write_save(laptop, 13)
    sync.pull(ScriptedIO(answers=[1]))             # keep THIS computer's save
    on(desktop)
    sync.pull(ScriptedIO())
    assert week_in(desktop) == 13


def test_unreachable_remote_is_reported_not_fatal(two_computers, tmp_path):
    remote, desktop, laptop, on = two_computers
    on(desktop)
    write_save(desktop, 3)
    sync.setup(ScriptedIO(), remote)
    subprocess.run(["git", "-C", str(desktop), "remote", "set-url", "origin", str(tmp_path / "gone.git")])
    io = ScriptedIO()
    sync.pull(io)
    write_save(desktop, 4)
    sync.push(io)
    out = io.output()
    assert "could not pull" in out and "could not push" in out and week_in(desktop) == 4
    assert sync.setup(ScriptedIO(), str(tmp_path / "nope.git")) == 1
