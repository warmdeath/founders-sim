import pytest

from founders_sim.game import quiz


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Every test gets its own profile/save directory, and the Bot's
    patched quiz.ask is undone afterwards."""
    monkeypatch.setenv("FOUNDERS_SIM_HOME", str(tmp_path / "home"))
    original = quiz.ask
    yield
    quiz.ask = original
