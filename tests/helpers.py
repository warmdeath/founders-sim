"""Shared test helpers: build a headless session, and a bot that plays."""
from __future__ import annotations

import random

from founders_sim.vfs import VFS, COMPANY
from founders_sim.ui.io import ScriptedIO
from founders_sim.learn.profile import Profile
from founders_sim.game import files, engine, quiz, funding
from founders_sim.game.scenarios import new_game, scenario_of
from founders_sim.game.session import Session
from founders_sim.app import build_shell

GOOD_SPEC = """# Spec: {title}
feature: {key}

## Goal
Customers can use {title} end to end without help from support.

## Context
Read {note} for what the customer said in their own words.
Existing roadmap is in product/roadmap.md

## Tasks
- Build the data model and storage for {key}
- Build the user-facing screen for {key}
- Wire it into onboarding and settings
- Write the tests for every acceptance criterion

## Acceptance tests
- A new user completes the main flow in under two minutes
- Invalid input shows a clear error and nothing is saved
- Works with one thousand records without slowing down

## Out of scope
No redesign of other screens, no new pricing logic.
"""


MEDIUM_SPEC = """# Spec: {title}
feature: {key}

## Goal
Build {title} so customers can use it.

## Context
Customers asked for this in interviews.

## Tasks
- Build the backend for {key}
- Build the screen for {key}

## Acceptance tests
- The main flow works for a new user
"""


def make_session(scenario="focusly", run_number=1, seed=1, answers=None, profile=None, quiet=True) -> Session:
    io = ScriptedIO(answers)
    game = new_game(scenario, run_number, seed)
    s = Session(game, VFS(), io, profile or Profile())
    s.quiet_learning = quiet
    files.setup(s)
    build_shell(s)
    return s


def run(s: Session, *lines: str) -> str:
    """Run command lines like the main loop does; return what was printed."""
    s.io.clear()
    for line in lines:
        s.shell.run_line(line)
        s.after_line(line)
    return s.io.output()


class Bot:
    """Plays a whole run through the same shell commands a human types.
    skill: 0..1 = how carefully it plays (interviews, specs, reviews) and
    how often it answers questions correctly."""

    def __init__(self, s: Session, skill: float = 1.0, raise_money: bool = True):
        self.s, self.skill, self.raise_money = s, skill, raise_money
        self.rng = random.Random(7)
        s.game.guided = False
        quiz.ask = lambda sess, q, speaker="": (sess.credit(q.term, True) or True) if self.rng.random() < skill \
            else (sess.credit(q.term, False) or False)

    def do(self, line: str) -> int:
        code = self.s.shell.run_line(line)
        self.s.after_line(line)
        return code

    def week(self) -> None:
        s, g = self.s, self.s.game
        sc = scenario_of(g)
        m = engine.metrics(g)
        careful = self.skill >= 0.6
        if g.energy < 45:
            self.do("rest")
        for ts in funding.open_termsheets(g):
            self.do(f"ts accept {ts.id}")
        todo = [l for l in g.leads.values() if not l.interviewed]
        expert = self.skill >= 0.9
        wanted = (8 if expert else 5) if careful else 1
        while todo and sum(l.interviewed for l in g.leads.values()) < wanted and g.hours >= 3:
            self.do(f"interview {todo.pop(0).key}")
        done = sum(l.interviewed for l in g.leads.values())
        if g.idea < 0 and (done >= wanted or not todo):
            votes = [sum(l.interviewed and l.likes_idea == i for l in g.leads.values()) for i in range(3)]
            self.do(f"idea pick {votes.index(max(votes)) + 1 if careful else 2}")
        if g.idea < 0:
            self.do("next")
            return
        if careful:
            for up in ("memory", "planning", "tests", "sandbox", "ci"):
                if not g.has(up) and g.hours >= 10 and g.cash > 3000 and g.flag("merges") >= 1:
                    self.do(f"upgrade {up}")
                    break
        # build: best known feature first (careful bots follow customer evidence)
        for _ in range(3):
            pending = [r for r in g.runs if not r.merged and not r.discarded]
            if pending:
                run_ = pending[0]
                if careful and g.hours >= 5:
                    self.do(f"review {run_.id}" + (" --deep" if expert else ""))
                if g.hours >= 0:
                    self.do(f"merge {run_.id}")
                if not run_.merged:
                    break
                continue
            options = [f for f in g.features.values() if f.known and not f.shipped]
            if careful:
                options = [f for f in options if f.revealed] or options
                options.sort(key=lambda f: -f.weight)
            if not options or g.hours < 4 or g.cash < 1500:
                break
            f = options[0]
            path = f"product/specs/{f.key}.md"
            if not s.fs.exists(f"{COMPANY}/{path}"):
                self.do(f"spec new {f.key}")
                if careful:
                    note = next((f"customers/notes/{l.key}.md" for l in g.leads.values()
                                 if l.interviewed and f.key in l.reveals), "customers/market.md")
                    s.fs.write(f"{COMPANY}/{path}", (GOOD_SPEC if expert else MEDIUM_SPEC).format(title=f.title, key=f.key, note=note))
            if self.do(f"agent run {path} --model {'smart' if expert and g.cash > 6000 else 'fast'}") != 0:
                break
        if engine.live(g):
            if careful:
                target = round(engine.wtp_now(g) * 0.92, 1)
                if abs(target - g.price) / g.price > 0.12:
                    self.do(f"price {target}")
                if g.prod_bugs >= 3 and g.hours >= 4:
                    self.do("fix")
                if g.debt > 35 and g.hours >= 6:
                    self.do("refactor")
            if g.week - g.flag("launch_week", -99) >= 10 and g.hours >= 8 and (m["fit"] > 40 or not careful):
                self.do("launch")
            if careful:
                cac = engine.paid_cac(g, 300)
                budget = 300 if m["ltv"] > 2.5 * cac and g.cash > 4000 else 0
                if m["ltv"] > 4 * cac and g.cash > 15000:
                    budget = 900
            else:
                budget = 500 if g.cash > 3000 else 0
            if budget != g.ad_budget:
                self.do(f"ads {budget}")
            if g.hours >= 5 and (sc.model in ("b2b", "usage") or g.week % 3 == 0):
                open_deals = [d for d in g.deals.values() if d.status == "open"]
                if len(open_deals) < 2:
                    self.do("outbound")
                for d in open_deals:
                    if g.hours >= 7:
                        self.do(f"sales {d.key}")
            if g.hours >= 5 and careful:
                self.do("content")
        if self.raise_money and m["runway"] < 14 and g.hours >= 5:
            if g.week - g.flag("deck_week", -99) > 8 and g.hours >= 9:
                self.do("deck")
            if g.flag("deck"):
                for inv in g.investors.values():
                    if inv.known and inv.status in ("new", "watching") and g.week - inv.last_pitch >= 6 \
                            and g.hours >= 5 and funding.traction_score(g, inv) >= 0.7:
                        self.do(f"pitch {inv.key}")
                if g.hours >= 6 and g.week % 4 == 0:
                    self.do("network")
        self.do("next")

    def play(self, max_weeks: int = 200) -> str:
        g = self.s.game
        self.s.io.answers = [0] * 100000     # first option everywhere (e.g. "end the run here")
        while not g.ended and max_weeks > 0:
            self.week()
            self.s.io.clear()
            max_weeks -= 1
        return g.ended
