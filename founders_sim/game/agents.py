"""PILLAR 1 - directing AI agents.

You never write code in this game. You write a SPEC, start agents on it,
REVIEW what they produced and MERGE it. The numbers below model real
experience with coding agents:

  * better spec  -> more work done, fewer bugs
  * no context   -> hallucinations
  * more agents  -> more throughput, but conflicts unless tasks are separable
  * tests        -> agents catch their own bugs
  * skip review  -> bugs ship to customers and become incidents
  * rushed work  -> technical debt, which makes every later run worse
"""
from __future__ import annotations

import re

from .state import AgentRun, Bug
from .session import Session, money
from . import engine

MODELS = {
    # name: (compute $ per work point, work points one agent can do in a run,
    #        bugs per 10 points, hallucination chance)
    "fast": (5, 22, 1.3, 0.38),
    "smart": (11, 34, 0.65, 0.16),
}
MIN_RUN_HOURS = 3      # briefing agents and reading what they did takes time, however small the job

UPGRADES = {
    # id: (title, hours, cash, requires, term, what it does)
    "planning": ("Plan mode", 3, 0, "", "plan_mode",
                 "Agents write a plan you approve before coding. Fewer misread specs: -20% bugs."),
    "memory": ("Project memory file (AGENTS.md)", 2, 0, "", "agents_md",
               "A file agents read every session. Better context for free: -25% bugs, fewer hallucinations."),
    "sandbox": ("Sandbox and permission rules", 3, 0, "", "guardrails",
                "Agents can't touch production or run destructive commands. Prevents the worst accidents."),
    "tests": ("Automated test suite", 8, 150, "", "tests",
              "Agents run tests on every run and fix what fails: about half of logic bugs never reach you."),
    "ci": ("Continuous integration", 4, 100, "tests", "ci",
           "`merge` is blocked while tests fail. You can no longer ship red by accident."),
    "reviewer": ("Review agent", 4, 150, "tests", "code_review",
                 "A second agent pre-reviews every run. Your reviews cost 1h less and catch more."),
    "subagents": ("Subagent orchestration", 5, 200, "planning", "subagents",
                  "A lead agent delegates to helpers and integrates. Parallel runs scale with far fewer conflicts."),
    "evals": ("Eval suite", 8, 250, "tests", "evals",
              "Measures AI output quality. Halves hallucinations; required to ship AI features safely."),
}

SECTIONS = ["Goal", "Context", "Tasks", "Acceptance tests", "Out of scope"]

BUG_TEXTS = {
    "logic": ["edge case: empty input crashes the importer", "off-by-one in pagination", "wrong rounding of totals",
              "state not saved when the user goes back", "time zones ignored in due dates",
              "duplicate records created on retry", "error message shown but action still executed"],
    "conflict": ["two agents edited the same module - one change overwrote the other",
                 "agents chose different data formats for the same field", "duplicate helper functions that disagree"],
    "hallucination": ["report claims 'all tests pass' but a suite was never run",
                      "calls an API method that does not exist in the library",
                      "invented a config option; the feature silently does nothing",
                      "says an edge case is 'handled' - no such code exists"],
    "security": ["user input reaches a database query unescaped", "secret key written into the code"],
}


def spec_template(feature) -> str:
    return (f"# Spec: {feature.title}\n"
            f"feature: {feature.key}\n\n"
            "## Goal\n"
            "TODO one or two sentences: what should exist when this is done, and for whom?\n\n"
            "## Context\n"
            "TODO point the agent at real files, e.g. customers/notes/<name>.md\n\n"
            "## Tasks\n"
            "- TODO 3-5 small steps that can each be checked on their own\n\n"
            "## Acceptance tests\n"
            "- TODO concrete, checkable statements of done\n\n"
            "## Out of scope\n"
            "TODO what must NOT be built\n")


def parse_spec(text: str) -> dict[str, list[str]]:
    """Split a spec into its '## Section' blocks -> meaningful lines."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        heading = re.match(r"#+\s*(.+)", line)
        if heading:
            name = heading.group(1).strip().lower()
            current = next((sec for sec in SECTIONS if name.startswith(sec.lower()[:6])), None)
            if current:
                sections.setdefault(current, [])
            continue
        stripped = line.strip().lstrip("-*").strip()
        if current and stripped and not stripped.upper().startswith("TODO") and len(stripped) >= 8:
            sections[current].append(stripped)
    return sections


def spec_feature(text: str, path: str) -> str:
    match = re.search(r"^feature:\s*(\S+)", text, re.MULTILINE)
    if match:
        return match.group(1)
    return path.rpartition("/")[2].rpartition(".")[0]


def score_spec(s: Session, text: str, feature_key: str = "") -> dict:
    """Score a spec 0..100 and explain why (like a senior reviewer would)."""
    g = s.game
    sec = parse_spec(text)
    score, notes = 0, []

    def judge(points: int, ok: bool, good: str, bad: str):
        nonlocal score
        if ok:
            score += points
            notes.append(("good", good))
        else:
            notes.append(("bad", bad))

    judge(15, bool(sec.get("Goal")), "Goal: stated.", "Goal: missing - the agent will guess what you want.")
    context = sec.get("Context", [])
    paths = re.findall(r"[\w./~-]+\.(?:md|txt|csv|deal)", " ".join(context))
    real = [p for p in paths if s.fs.exists(p, s.path("")) or s.fs.exists(p, "/")]
    judge(8, bool(context), "Context: present.", "Context: missing - agents know nothing about your project by default.")
    judge(12, bool(real), f"Context: points to real files ({', '.join(real[:2])}).",
          "Context: no path to a real file (e.g. customers/notes/<name>.md) - the agent can't read your customers' words.")
    tasks = sec.get("Tasks", [])
    if 2 <= len(tasks) <= 6:
        judge(20, True, f"Tasks: {len(tasks)} separate steps - good decomposition.", "")
    elif len(tasks) == 1:
        score += 8
        notes.append(("bad", "Tasks: only one - break the work into 3-5 checkable steps."))
    elif len(tasks) > 6:
        score += 12
        notes.append(("bad", f"Tasks: {len(tasks)} is a lot for one spec - split into two specs."))
    else:
        notes.append(("bad", "Tasks: missing - big fuzzy work produces big fuzzy bugs."))
    tests = sec.get("Acceptance tests", [])
    if len(tests) >= 2:
        judge(25, True, f"Acceptance tests: {len(tests)} checkable criteria - the agent can verify itself.", "")
    elif tests:
        score += 12
        notes.append(("bad", "Acceptance tests: only one - add another concrete, checkable criterion."))
    else:
        notes.append(("bad", "Acceptance tests: missing - neither the agent nor you can tell when it is done."))
    judge(10, bool(sec.get("Out of scope")), "Out of scope: stated - prevents over-building.",
          "Out of scope: missing - agents love to add things nobody asked for.")
    feature = g.features.get(feature_key)
    # evidence = an interview note in which a customer talks about THIS feature (or their quote)
    about = [f"customers/notes/{lead.key}.md" for lead in g.leads.values()
             if lead.interviewed and feature_key in lead.reveals]
    evidence = bool(feature and feature.revealed and
                    (any(p.endswith(a) for p in real for a in about) or feature.quote[:25].lower() in text.lower()))
    judge(10, evidence, "Evidence: built on a need customers actually voiced.",
          "Evidence: nothing links this to what customers said. Point Context at a note where someone asks for THIS "
          "(find it: grep -il '" + (feature.title.split()[0].lower() if feature else "keyword") + "' customers/notes/*).")
    # a spec copied from another feature and not adapted describes the WRONG feature
    mine = {line for lines in sec.values() for line in lines}
    try:
        others = s.fs.listdir(s.path("product/specs"))
    except Exception:
        others = []
    for other in others:
        other_text = getattr(other, "content", "")
        if spec_feature(other_text, other.name) == feature_key or len(mine) < 4:
            continue
        theirs = {line for lines in parse_spec(other_text).values() for line in lines}
        if len(mine & theirs) >= 0.7 * len(mine):
            score = min(score, 35)
            notes.append(("bad", f"Copy: most of this text is identical to {other.name}. It describes another feature - "
                                 "adapt the goal, tasks and tests or the agent will rebuild that one."))
            break
    return {"score": min(100, score), "notes": notes, "tasks": len(tasks), "tests": len(tests),
            "context": bool(real), "sections": sec}


def run_cost(model: str, agents: int, points: float) -> float:
    """Compute is billed by tokens, so it grows with the WORK done. Each
    extra parallel agent re-reads the project, adding ~15% overhead."""
    return max(20.0, round(MODELS[model][0] * points * (1 + 0.15 * (agents - 1))))


def run_hours(points: float, agents: int, planning: bool) -> float:
    """Your time: briefing, answering questions, reading the result."""
    return round(2 + points / 2.5 + 0.5 * (agents - 1) + (0.5 if planning else 0), 1)


def start_run(s: Session, spec_path: str, agents: int, model: str) -> AgentRun | None:
    """`agent run`: returns the run (also written to agents/runs/) or None."""
    from . import files
    g = s.game
    text = s.fs.read(spec_path, s.shell.cwd if s.shell else "/")
    key = spec_feature(text, spec_path)
    feature = g.features.get(key)
    if feature is None or not feature.known:
        s.bad(f"The spec names feature '{key}', which is not on your roadmap (see product/roadmap.md).")
        return None
    if feature.progress >= 0.999:
        s.bad(f"'{feature.title}' is already fully built and shipped.")
        return None
    pending = [r for r in g.runs if r.feature == key and not r.merged and not r.discarded]
    if pending:
        s.bad(f"{pending[0].id} for this feature is still waiting. `review`/`merge` it or `agent discard {pending[0].id}`.")
        return None
    info = score_spec(s, text, key)
    _, capacity, bug_rate, halluc = MODELS[model]
    spec = info["score"] / 100
    tasks = max(1, info["tasks"])
    useful = min(agents, tasks)                              # agents without a task of their own idle
    exponent = 0.93 if g.has("subagents") else 0.75
    throughput = capacity * (useful ** exponent) * (0.55 + 0.55 * spec) * (1 - g.debt / 250)
    remaining = 1 - feature.progress
    work = min(remaining, throughput / feature.complexity)
    if work >= 0.85 * remaining:                             # nearly there: the agent finishes the job
        work = remaining
    points = work * feature.complexity
    hours = run_hours(points, agents, g.has("planning"))
    if g.hours < MIN_RUN_HOURS:
        s.spend_hours(MIN_RUN_HOURS, "briefing and supervising the agents")
        return None
    if hours > g.hours:                                      # not enough of YOUR time to supervise it all
        points = max(1.0, (g.hours - 2 - 0.5 * (agents - 1) - (0.5 if g.has("planning") else 0)) * 2.5)
        work = points / feature.complexity
        hours = g.hours
        s.note(f"You only had {g.hours:g}h left to supervise, so the agents stopped early. "
               "They continue from here on the next run.")
    cost = run_cost(model, agents, points)
    if g.cash < cost:
        s.bad(f"This run would cost about {money(cost)} of compute and you have {money(g.cash)}.")
        return None
    g.hours -= hours
    s.pay(cost, "compute")
    g.compute_week += cost
    g.compute_total += cost
    g.flags["last_run_hours"] = hours

    expected = points / 10 * bug_rate * (1.7 - 1.1 * spec) * (1 + g.debt / 60)
    if g.has("planning"):
        expected *= 0.8
    if g.has("memory"):
        expected *= 0.75
    if engine.has_hire(g, "engineer"):
        expected *= 0.85
    count = int(expected) + (1 if g.rng.random() < expected - int(expected) else 0)
    bugs: list[Bug] = []
    visible_chance = (0.75 if g.has("tests") else 0.12) + (0.15 if info["tests"] >= 2 else 0)
    for _ in range(count):
        kind = "security" if g.rng.random() < 0.08 else "logic"
        if g.has("tests") and kind == "logic" and g.rng.random() < 0.55:
            continue                                         # the agent's own test run caught and fixed it
        bugs.append(Bug(kind, g.rng.choice(BUG_TEXTS[kind]), g.rng.random() < visible_chance))
    if agents > 1:
        conflict = (agents - 1) * (0.9 if tasks < agents else 0.35) * (0.3 if g.has("subagents") else 1.0)
        for _ in range(int(conflict) + (1 if g.rng.random() < conflict - int(conflict) else 0)):
            bugs.append(Bug("conflict", g.rng.choice(BUG_TEXTS["conflict"]), g.rng.random() < visible_chance))
        s.learn("parallel_agents")
        if any(b.kind == "conflict" for b in bugs):
            g.bump("conflicts")
    h_chance = halluc * (1.5 if not info["context"] else 0.8) * (0.7 if g.has("memory") else 1) \
        * (0.5 if g.has("evals") else 1)
    if feature.kind == "ai" and not g.has("evals"):
        h_chance = min(0.95, h_chance + 0.45)
    if g.rng.random() < h_chance:
        bugs.append(Bug("hallucination", g.rng.choice(BUG_TEXTS["hallucination"]), False))

    run = AgentRun(f"run_{len(g.runs) + 1:03d}", key, spec_path, agents, model, g.week, cost, info["score"],
                   work, bugs)
    g.runs.append(run)
    g.bump("runs")
    files.write_run(s, run, info)
    s.learn("agent", "spec", "token")
    if model == "smart" or g.flag("runs") == 3:
        s.learn("model_tier")
    if info["score"] < 50:
        g.bump("weak_specs")
    return run


def bug_count(run: AgentRun, found: bool | None = None) -> int:
    return sum(1 for b in run.bugs if found is None or b.found == found)


def review_run(s: Session, run: AgentRun, deep: bool) -> list[Bug] | None:
    """`review`: find (and fix) bugs before they ship."""
    from . import files
    g = s.game
    hours = 5.0 if deep else 2.0
    if g.has("reviewer"):
        hours -= 1
    if engine.has_hire(g, "engineer"):
        hours *= 0.5
    if not s.spend_hours(hours, "reviewing"):
        return None
    found: list[Bug] = []
    bonus = (0.1 if g.has("reviewer") else 0) + (0.05 if engine.has_hire(g, "engineer") else 0)
    for bug in run.bugs:
        if bug.found:
            continue
        if bug.kind == "hallucination":
            chance = (0.8 if deep else 0.35) + (0.15 if g.has("evals") else 0)
        elif bug.visible_in_tests:
            chance = 0.97 if deep else 0.9
        else:
            chance = 0.8 if deep else 0.4
        if g.rng.random() < min(0.99, chance + bonus):
            bug.found = True
            found.append(bug)
    fix_cost = 12 * len(found)
    if fix_cost:
        s.pay(fix_cost, "compute")
        g.compute_total += fix_cost
    run.review = "deep" if deep or run.review == "deep" else "quick"
    g.bump("reviews")
    files.write_run_review(s, run, found)
    s.learn("code_review")
    if any(b.kind == "hallucination" for b in found):
        s.learn("hallucination")
        s.credit("hallucination")
    return found


def merge_run(s: Session, run: AgentRun) -> bool:
    """`merge`: ship a run to customers - with whatever bugs are left."""
    g = s.game
    feature = g.features[run.feature]
    left = [b for b in run.bugs if not b.found]
    if g.has("ci") and any(b.visible_in_tests for b in left):
        failing = sum(b.visible_in_tests for b in left)
        s.bad(f"CI blocked the merge: {failing} test(s) failing in {run.id}/tests.log. Run `review` to fix them.")
        s.credit("ci")
        return False
    run.merged = True
    was_live = engine.live(g)
    feature.progress = min(1.0, feature.progress + run.work_done)
    weight = {"logic": 1.0, "conflict": 1.0, "hallucination": 1.5, "security": 2.0}
    shipped_bugs = sum(weight[b.kind] for b in left)
    g.prod_bugs += shipped_bugs
    points = run.work_done * feature.complexity
    g.debt = min(100, g.debt + points * (0.45 - 0.4 * run.spec_score / 100) + 1.5 * len(left)
                 + (2 if run.review == "none" else 0) + (0 if g.has("tests") else 1))
    g.bump("merges")
    if run.review == "none":
        g.bump("merged_unreviewed")
    if left:
        g.bump("bugs_shipped", len(left))
    runs = [r for r in g.runs if r.feature == run.feature and r.merged]
    if feature.progress >= 0.999:
        avg_spec = sum(r.spec_score for r in runs) / len(runs)
        all_left = sum(bug_count(r, found=False) for r in runs)
        feature.quality = engine.clamp(0.5 + 0.5 * avg_spec / 100 - 0.05 * all_left, 0.3, 1.0)
        if not feature.revealed and feature.weight < 0.06:
            g.bump("junk_built")
        s.good(f"Shipped: [bold]{feature.title}[/bold] is live (feature quality {feature.quality * 100:.0f}%).")
        if not was_live:
            s.learn("mvp")
            s.note("Your product is live: people can now sign up. Watch `metrics` after each `next`.")
    else:
        s.good(f"Merged. '{feature.title}' is {feature.progress * 100:.0f}% built - run agents on the spec again to finish it.")
    if run.review == "none":
        s.note("(Merged without review: whatever the agent got wrong is now in the product. "
               "You'll find out when customers do.)")
    if left:
        s.learn("bug")
    s.learn("merge", "tech_debt")
    return True


def fix_bugs(s: Session) -> bool:
    g = s.game
    if g.prod_bugs < 0.5:
        s.say("No known production bugs to fix right now.")
        return False
    if g.cash < 60 or not s.spend_hours(4, "a bug-fixing sweep"):
        return False
    s.pay(60, "compute")
    g.compute_total += 60
    before = g.prod_bugs
    g.prod_bugs *= 0.25 if g.has("tests") else 0.45
    s.good(f"Bug sweep done: production bugs {before:.0f} → {g.prod_bugs:.0f}."
           + ("" if g.has("tests") else " (With an automated test suite the sweep would find more.)"))
    s.learn("bug")
    return True


def refactor(s: Session) -> bool:
    g = s.game
    if g.debt < 5:
        s.say("Technical debt is low; nothing worth refactoring.")
        return False
    if g.cash < 140 or not s.spend_hours(6, "a refactoring session"):
        return False
    s.pay(140, "compute")
    g.compute_total += 140
    before = g.debt
    g.debt = max(0, g.debt - (35 if g.has("tests") else 22))
    s.good(f"Refactored: technical debt {before:.0f} → {g.debt:.0f}.")
    if not g.has("tests") and g.rng.random() < 0.45:
        g.prod_bugs += 1
        s.bad("Without tests, the refactor broke something that used to work (a regression).")
        s.learn("regression")
    s.learn("refactor")
    s.credit("tech_debt")
    return True


def buy_upgrade(s: Session, key: str) -> bool:
    from . import files
    g = s.game
    title, hours, cash, requires, term, what = UPGRADES[key]
    if g.has(key):
        s.say(f"You already have '{title}'.")
        return False
    if requires and not g.has(requires):
        s.bad(f"'{title}' builds on '{UPGRADES[requires][0]}' - set that up first (`upgrade {requires}`).")
        return False
    if g.cash < cash:
        s.bad(f"'{title}' costs {money(cash)}.")
        return False
    if not s.spend_hours(hours, f"setting up {title}"):
        return False
    if cash:
        s.pay(cash, "tools")
    g.upgrades.append(key)
    s.good(f"Workflow upgraded: [bold]{title}[/bold]. {what}")
    s.learn(term)
    s.credit(term)
    files.sync(s)
    return True
