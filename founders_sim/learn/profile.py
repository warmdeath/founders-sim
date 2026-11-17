"""The persistent learner profile: what YOU (the human) know, across runs.

Stored as JSON in ~/.founders_sim/profile.json on the REAL disk (the only
real files the game writes, together with saves and shell history).
Set the FOUNDERS_SIM_HOME environment variable to store them elsewhere.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .terms import TERMS, ORDER
from .bash_lessons import LESSONS


def data_dir() -> Path:
    path = Path(os.environ.get("FOUNDERS_SIM_HOME", Path.home() / ".founders_sim"))
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Profile:
    runs: int = 0                                        # completed runs
    terms: dict[str, dict] = field(default_factory=dict)  # id -> {seen, ok, bad}
    bash: dict[str, dict] = field(default_factory=dict)   # id -> {ok, bad}
    mechanics: dict[str, int] = field(default_factory=dict)  # e.g. "loan_taken": 2
    scenarios: dict[str, int] = field(default_factory=dict)  # scenario id -> times played
    endings: list[dict] = field(default_factory=list)
    next_focus: list[str] = field(default_factory=list)

    # ------------------------------------------------------------ terms
    def _term(self, term: str) -> dict:
        return self.terms.setdefault(term, {"seen": 0, "ok": 0, "bad": 0})

    def see(self, term: str) -> None:
        self._term(term)["seen"] += 1

    def credit(self, term: str, ok: bool = True) -> None:
        self._term(term)["ok" if ok else "bad"] += 1

    def term_status(self, term: str) -> str:
        """unseen -> seen -> practiced -> mastered"""
        rec = self.terms.get(term)
        if not rec or not (rec["seen"] or rec["ok"] or rec["bad"]):
            return "unseen"
        if rec["ok"] >= 2 and rec["ok"] > rec["bad"]:
            return "mastered"
        if rec["ok"] >= 1:
            return "practiced"
        return "seen"

    def struggling(self) -> list[str]:
        """Terms answered wrong at least as often as right."""
        return [t for t in ORDER if t in self.terms and self.terms[t]["bad"] > 0
                and self.terms[t]["bad"] >= self.terms[t]["ok"]]

    # ------------------------------------------------------------- bash
    def bash_use(self, lesson: str, ok: bool = True) -> None:
        rec = self.bash.setdefault(lesson, {"ok": 0, "bad": 0})
        rec["ok" if ok else "bad"] += 1

    def bash_status(self, lesson: str) -> str:
        rec = self.bash.get(lesson)
        if not rec or not (rec["ok"] or rec["bad"]):
            return "unseen"
        if rec["ok"] >= 3:
            return "mastered"
        return "practiced" if rec["ok"] else "seen"

    # --------------------------------------------------------- progress
    def counts(self) -> dict:
        statuses = [self.term_status(t) for t in TERMS]
        bash = [self.bash_status(b) for b in LESSONS]
        return {"terms": len(TERMS), "mastered": statuses.count("mastered"),
                "practiced": statuses.count("practiced"), "seen": statuses.count("seen"),
                "bash": len(LESSONS), "bash_mastered": bash.count("mastered"),
                "bash_practiced": bash.count("practiced")}

    def did(self, mechanic: str) -> None:
        self.mechanics[mechanic] = self.mechanics.get(mechanic, 0) + 1

    # ------------------------------------------------------------- disk
    def save(self) -> None:
        (data_dir() / "profile.json").write_text(json.dumps(asdict(self), indent=1))

    @classmethod
    def load(cls) -> "Profile":
        path = data_dir() / "profile.json"
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text())
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except (ValueError, TypeError):
            return cls()
