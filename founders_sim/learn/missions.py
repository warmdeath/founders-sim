"""Guidance: the run-1 tutorial missions, the `tutor` command, and the
bash challenges that require combining commands.

Missions are a simple ordered list. After every command the game checks
whether the current mission's condition is now true and moves on.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from rich.panel import Panel
from rich.text import Text

from ..vfs import COMPANY, File
from .bash_lessons import LESSONS, ORDER as BASH_ORDER
from .terms import TERMS
from . import notebook


# =================================================================== missions
@dataclass
class Mission:
    title: str
    why: str
    how: str                       # what to type
    done: Callable                 # (session) -> bool


def _used(s, name: str, n: int = 1) -> bool:
    return s.game.used.get(name, 0) >= n


def _interviews(s) -> int:
    return sum(l.interviewed for l in s.game.leads.values())


MISSIONS = [
    Mission("Where am I?", "A shell always 'stands' in one directory. Everything starts with knowing where you are.",
            "pwd", lambda s: _used(s, "pwd")),
    Mission("Look around", "Your company is a folder full of folders. See what's in it.",
            "ls", lambda s: _used(s, "ls")),
    Mission("Read your mail", "Your mentor wrote to you. `cat` prints a file. Type `cat inb` and press Tab to complete.",
            "cat inbox/001_welcome_read_me_first.txt", lambda s: _used(s, "cat")),
    Mission("Walk into a folder", "`cd` changes directory. Go into product, read the ideas, come back up with `cd ..`",
            "cd product   →   cat ideas.md   →   cd ..", lambda s: _used(s, "cd", 2) and s.game.flag("paths_used") > 0),
    Mission("See the details", "Flags change what a command does. -l is the long listing.",
            "ls -l customers/leads", lambda s: s.game.flag("ls_flags_used") > 0),
    Mission("Talk to three customers", "Before building anything, find out which problem is real. Each interview costs 3 hours.",
            "interview customers/leads/<name>.txt     (three different people)", lambda s: _interviews(s) >= 3),
    Mission("Read what they said", "The notes are files. Read one, then search ALL of them at once with grep.",
            "cat customers/notes/<name>.md   →   grep -i pricing customers/notes/*", lambda s: _used(s, "grep")),
    Mission("Commit to an idea", "Pick the idea whose problem your interviewees actually have.",
            "cat product/ideas.md   →   idea pick <number>", lambda s: s.game.idea >= 0),
    Mission("Write a spec", "Agents build what the words say. Create a spec for a feature customers asked for, fill in every "
            "section (replace the TODO lines), and get it to 60+ points.",
            "cat product/roadmap.md   →   spec new <key>   →   nano product/specs/<key>.md   →   spec check product/specs/<key>.md",
            lambda s: s.game.flag("best_spec") >= 60),
    Mission("Put your agents to work", "Start an agent on your spec. It costs compute dollars and a couple of hours.",
            "agent run product/specs/<key>.md", lambda s: s.game.flag("runs") >= 1),
    Mission("Don't trust - verify", "The agent says it's done. Check the evidence yourself, then review.",
            "cat agents/runs/run_001/report.md   →   grep -c FAIL agents/runs/run_001/tests.log   →   review run_001",
            lambda s: s.game.flag("reviews") >= 1),
    Mission("Ship it", "Merging puts the work in front of customers. If the feature isn't 100% built, run the agent again.",
            "merge run_001     (repeat agent run / review / merge until the feature is LIVE)",
            lambda s: any(f.shipped for f in s.game.features.values())),
    Mission("Let a week pass", "Time only moves when you say so. `next` ends the week: revenue comes in, bills go out.",
            "next", lambda s: s.game.week >= 2),
    Mission("Know your numbers", "The founder's dashboard. Every number has a notebook entry explaining it.",
            "metrics", lambda s: _used(s, "metrics")),
    Mission("Count with a pipe", "The | sends one command's output into another. Count your emails.",
            "ls inbox | wc -l", lambda s: _used(s, "pipe")),
    Mission("Set your price", "Check what interviewees said about money, then set a price.",
            "grep -i pricing customers/notes/*   →   price <amount>", lambda s: s.game.flag("price_changes") >= 1),
    Mission("Open your notebook", "Everything you've learned is saved. The glossary shows the whole curriculum.",
            "notebook   →   glossary", lambda s: _used(s, "notebook") and _used(s, "glossary")),
    Mission("Tidy your inbox", "Move a read email into the archive. Moving and renaming are the same command.",
            "mv inbox/001_welcome_read_me_first.txt inbox/archive/", lambda s: _used(s, "mv")),
    Mission("Find customers", "A product nobody hears about earns nothing. `growth` shows where customers come from "
            "and why they leave. Start small; save the big `launch` for when several asked-for features are live.",
            "growth   →   content     or     ads 100",
            lambda s: s.game.flag("launches") >= 1 or s.game.ad_budget > 0 or s.game.audience > 0),
    Mission("Build your deck", "A pitch deck is assembled from evidence you really have.",
            "deck   →   cat investors/deck.md", lambda s: s.game.flag("deck") > 0),
    Mission("Pitch an investor", "Read who they are first. Study `metrics` - they will ask and you can't look it up.",
            "cat investors/angel_rossi.txt   →   metrics   →   pitch investors/angel_rossi.txt",
            lambda s: s.game.flag("pitches") >= 1),
]


def mission_panel(s) -> Panel:
    g = s.game
    mission = MISSIONS[g.mission]
    body = Text()
    body.append(mission.why + "\n\n")
    body.append("Try:  ", style="bold")
    body.append(mission.how, style="bold magenta")
    return Panel(body, title=f"🎯 Mission {g.mission + 1}/{len(MISSIONS)}: {mission.title}",
                 border_style="yellow", title_align="left", subtitle="type `tutor` to see this again",
                 subtitle_align="right")


def check_missions(s) -> None:
    """Called after every command in the guided first run."""
    g = s.game
    if not g.guided or g.mission >= len(MISSIONS):
        return
    advanced = False
    while g.mission < len(MISSIONS) and MISSIONS[g.mission].done(s):
        s.io.print(f"[good]✔ Mission complete:[/good] {MISSIONS[g.mission].title}")
        g.mission += 1
        advanced = True
    if advanced:
        if g.mission < len(MISSIONS):
            s.io.print(mission_panel(s))
        else:
            s.io.print(Panel("You know the core loop: talk to customers → spec → agents → review → ship → measure → "
                             "sell → fund.\nFrom here you're on your own. `tutor` always suggests what to learn next, "
                             "`challenges` lists shell puzzles, `help` lists every command.\n"
                             "Win by becoming profitable, closing a priced funding round, or being acquired.",
                             title="🎓 Tutorial complete", border_style="green", title_align="left"))


# ====================================================================== tutor
def next_bash_lesson(s) -> str | None:
    for lesson in BASH_ORDER:
        if "sh_" + lesson not in s.game.notebook:
            return lesson
    return None


def strategy_tips(s) -> list[str]:
    """What an experienced founder would worry about right now."""
    from ..game import engine
    g = s.game
    m = engine.metrics(g)
    interviews = _interviews(s)
    pending = [r for r in g.runs if not r.merged and not r.discarded]
    tips = []
    if interviews < 3:
        tips.append("Talk to customers before building: `ls customers/leads`, then `interview customers/leads/<name>.txt`.")
    elif g.idea < 0:
        tips.append("You have interview evidence. Commit: `cat product/ideas.md`, then `idea pick <n>`.")
    elif not g.runs:
        tips.append("Write a spec for a feature customers asked for: `spec new <key>` (keys are in product/roadmap.md).")
    if pending:
        tips.append(f"{pending[0].id} is waiting: read its tests.log, `review {pending[0].id}`, then `merge {pending[0].id}`.")
    if m["runway"] < 6:
        tips.append(f"Runway is {engine.fmt_runway(m)}. Cut burn (`ads 0`), raise the price, pitch investors, or look at `loan`.")
    if engine.live(g) and m["churn"] > 0.12:
        tips.append(f"Churn is {m['churn'] * 100:.0f}% a month. `growth` lists why they leave; ship what customers asked for "
                    "before spending on growth.")
    if engine.live(g) and g.ad_budget == 0 and g.audience < 30 and g.flag("launches") == 0:
        tips.append("Your product is live but nobody knows. `growth` shows the funnel; try `content` or a small `ads <weekly budget>`.")
    if g.debt > 35:
        tips.append(f"Technical debt is {g.debt:.0f}/100: `refactor`, and consider `upgrade tests`.")
    if g.prod_bugs >= 3:
        tips.append(f"{g.prod_bugs:.0f} bugs are live in production: `fix`.")
    if interviews >= 3 and interviews < len(g.leads) and engine.fit(g) < 50 and g.runs:
        tips.append("Fit is low and you still have people to interview. More interviews reveal hidden needs.")
    if not g.upgrades and g.flag("runs") >= 2:
        tips.append("You run agents with no workflow upgrades. `upgrade` lists them; `memory` and `planning` are cheap.")
    if g.energy < 40:
        tips.append(f"Energy is {g.energy:.0f}/100. `rest` before you burn out.")
    open_ts = [t for t in g.termsheets if t.status == "open"]
    if open_ts:
        tips.append(f"A term sheet is waiting: `cat investors/termsheets/{open_ts[0].id}.txt`, then `ts negotiate|accept|decline`.")
    if m["mrr"] > 0 and not g.flag("deck") and m["runway"] < 14:
        tips.append("You have revenue - investors will take meetings. `deck`, then `pitch investors/<file>`.")
    if any(d.status == "open" for d in g.deals.values()):
        tips.append("Open B2B deals go cold if ignored: `sales` lists them, `sales <deal>` works one.")
    return tips


def tutor(s):
    """`tutor`: the next thing worth learning, in three parts."""
    g = s.game
    if g.guided and g.mission < len(MISSIONS):
        return mission_panel(s)
    body = Text()
    lesson = next_bash_lesson(s)
    if lesson:
        L = LESSONS[lesson]
        body.append("Shell  ", style="bold magenta")
        body.append(f"Next skill: {L.title}\n       {L.what}\n       Try:  ")
        body.append(L.try_it + "\n\n", style="bold magenta")
    else:
        body.append("Shell  ", style="bold magenta")
        body.append("You've touched every shell lesson. `challenges` has puzzles that combine them.\n\n")
    tips = strategy_tips(s)
    body.append("Company  ", style="bold green")
    body.append(("\n         ".join(tips[:3]) if tips else "Nothing urgent. Keep the loop turning: build, measure, learn.") + "\n\n")
    weak = notebook.weakest_terms(s, 3)
    body.append("Vocabulary  ", style="bold cyan")
    if weak:
        body.append("Not yet mastered: " + ", ".join(TERMS[t].name for t in weak)
                    + f".\n            Practise with `quiz`, reread with `nb {weak[0]}`.")
    else:
        body.append("Everything in your notebook is mastered. New terms unlock as new situations arise.")
    return Panel(body, title="🧭 Tutor", border_style="yellow", title_align="left")


# ================================================================= challenges
@dataclass
class Challenge:
    id: str
    title: str
    text: str
    hint: str
    ready: Callable                # (session) -> bool : can it be asked yet?
    check: Callable                # (session, answer text) -> bool
    skills: tuple                  # bash lessons this practises


def _files(s, rel: str):
    return [n for n in s.fs.walk(f"{COMPANY}/{rel}") if isinstance(n, File)]


def _num(text: str):
    try:
        return int(text.strip())
    except ValueError:
        return None


def _notes_with_pricing(s) -> int:
    return sum("pricing" in f.content.lower() for f in s.fs.listdir(f"{COMPANY}/customers/notes"))


def _fail_lines(s) -> int:
    return sum(line.count("FAIL") > 0 for f in _files(s, "agents/runs") if f.name == "tests.log"
               for line in f.content.splitlines())


def _best_cash_week(s) -> int:
    return max(s.game.history, key=lambda wk: wk.cash).week


def _script_ok(s) -> bool:
    path = f"{COMPANY}/reports/weekly.sh"
    if not s.fs.is_file(path) or not s.fs.lookup(path).mode & 0o100:
        return False
    from ..shell.parser import parse
    cwd, s.shell.cwd = s.shell.cwd, COMPANY
    try:
        out, _ = s.shell.run_tree(parse("./reports/weekly.sh"), None, capture=True)
    finally:
        s.shell.cwd = cwd
    last = s.fs.read(f"{COMPANY}/finance/metrics.csv").strip().splitlines()[-1]
    return last in out


CHALLENGES = [
    Challenge("c1", "Count the inbox", "How many entries are in your inbox folder right now (files and folders)?",
              "ls inbox | wc -l", lambda s: s.game.week >= 3,
              lambda s, a: _num(a) == len(s.fs.listdir(f"{COMPANY}/inbox")), ("pipe", "wc", "ls")),
    Challenge("c2", "Archive old mail", "Move at least three emails from inbox/ into inbox/archive/. Then: answer c2",
              "mv inbox/001* inbox/archive/      (a * matches any characters; you can list several files)",
              lambda s: len(s.game.emails) >= 5,
              lambda s, a: sum(isinstance(n, File) for n in s.fs.listdir(f"{COMPANY}/inbox/archive")) >= 3, ("mv",)),
    Challenge("c3", "Who talked about pricing?", "How many of your interview notes mention the word 'pricing'?",
              "grep -il pricing customers/notes/* | wc -l", lambda s: _interviews(s) >= 3,
              lambda s, a: _num(a) == _notes_with_pricing(s), ("grep", "pipe", "wc")),
    Challenge("c4", "Count the failures", "How many FAIL lines are there in ALL your agents' tests.log files together?",
              "cat agents/runs/*/tests.log | grep -c FAIL", lambda s: len(s.game.runs) >= 2,
              lambda s, a: _num(a) == _fail_lines(s), ("grep", "cat", "pipe")),
    Challenge("c5", "Find the markdown", "How many .md files exist anywhere under ~/company?",
              "find ~/company -name '*.md' | wc -l", lambda s: s.game.week >= 8,
              lambda s, a: _num(a) == sum(f.name.endswith(".md") for f in _files(s, "")), ("find", "pipe", "wc")),
    Challenge("c6", "Best week", "In which week was your cash balance the highest? (finance/metrics.csv, column 2)",
              "sort -t, -k2 -n finance/metrics.csv | tail -n 1", lambda s: len(s.game.history) >= 8,
              lambda s, a: _num(a) == _best_cash_week(s), ("sort", "tail", "pipe")),
    Challenge("c7", "Investor census", "How many of the investors you know have 'Type: vc' in their file?",
              "grep -l 'Type: vc' investors/*.txt | wc -l     or     grep -h '^Type:' investors/*.txt | sort | uniq -c",
              lambda s: sum(i.known for i in s.game.investors.values()) >= 4,
              lambda s, a: _num(a) == sum(i.known and i.kind == "vc" for i in s.game.investors.values()),
              ("grep", "uniq", "sort")),
    Challenge("c8", "Keep a copy", "Copy finance/captable.txt into reports/ (any name starting with 'captable'). Then: answer c8",
              "cp finance/captable.txt reports/captable_backup.txt", lambda s: s.game.week >= 12,
              lambda s, a: any(n.name.startswith("captable") for n in s.fs.listdir(f"{COMPANY}/reports")), ("cp",)),
    Challenge("c9", "Configure with a variable", "Set your default agent model to 'smart' with an environment variable, "
              "then answer with the variable: answer c9 $AGENT_MODEL",
              "export AGENT_MODEL=smart      then      answer c9 $AGENT_MODEL", lambda s: s.game.flag("runs") >= 3,
              lambda s, a: a.strip() == "smart" and s.shell.env.get("AGENT_MODEL") == "smart", ("variables", "echo")),
    Challenge("c10", "Your first script", "Create an executable script reports/weekly.sh that prints the last line of "
              "finance/metrics.csv. Then: answer c10",
              "echo 'tail -n 1 finance/metrics.csv' > reports/weekly.sh   →   chmod +x reports/weekly.sh   →   ./reports/weekly.sh",
              lambda s: len(s.game.history) >= 10, lambda s, a: _script_ok(s), ("script", "chmod", "redirect")),
]
BY_ID = {c.id: c for c in CHALLENGES}


def maybe_issue_challenge(s) -> str:
    """Every few weeks your mentor sends a shell puzzle."""
    g = s.game
    if g.week % 3 != 0 or sum(v == "open" for v in g.challenges.values()) >= 2:
        return ""
    for ch in CHALLENGES:
        if ch.id not in g.challenges and ch.ready(s):
            g.challenges[ch.id] = "open"
            s.mail("Nora (your mentor)", f"Shell challenge {ch.id}: {ch.title}",
                   f"{ch.text}\n\nAnswer with:  answer {ch.id} <your answer>\n"
                   + (f"\nHint: {ch.hint}\n" if g.level <= 2 else "\n(No hint this time - `man` and your notebook know.)\n"),
                   kind="challenge", ref=ch.id)
            return f"[cmd]✉[/cmd]  Shell challenge {ch.id} from your mentor: \"{ch.title}\" (see inbox, or `challenges`)."
    return ""


def answer(s, cid: str, text: str) -> bool:
    g = s.game
    ch = BY_ID.get(cid)
    if ch is None or g.challenges.get(cid) is None:
        s.bad(f"No challenge '{cid}'. `challenges` lists the open ones.")
        return False
    if g.challenges[cid] == "done":
        s.say("You already solved that one.")
        return False
    if ch.check(s, text):
        g.challenges[cid] = "done"
        g.energy = min(100, g.energy + 4)
        g.reputation = min(100, g.reputation + 1)
        for skill in ch.skills:
            s.profile.bash_use(skill, True)
            s.profile.bash_use(skill, True)
        s.profile.did("challenge_" + cid)
        s.good(f"Correct! Challenge {cid} solved. (Energy +4, reputation +1 - competence feels good.)")
        return True
    for skill in ch.skills[:1]:
        s.profile.bash_use(skill, False)
    s.bad(f"Not yet. Hint: {ch.hint}")
    return False


def challenge_list(s) -> Text:
    g = s.game
    out = Text()
    if not g.challenges:
        out.append("No challenges yet - your mentor sends one every few weeks.\n", style="dim")
    for cid, state in g.challenges.items():
        ch = BY_ID[cid]
        out.append(f"{'✔' if state == 'done' else '○'} {cid}  {ch.title}\n", style="green" if state == "done" else "bold")
        if state != "done":
            how = f"answer {cid}" if "Then: answer" in ch.text else f"answer {cid} <your answer>"
            out.append(f"     {ch.text}\n     {how}\n", style="")
    return out
