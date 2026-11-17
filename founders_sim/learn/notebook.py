"""The Founder's Notebook: unlocking terms and bash lessons, and the
screens that show them (notebook, glossary).

Every entry is ALSO written as a file in ~/company/notebook/, so the
player can `cat`, `grep -ri runway notebook/` and `ls` their knowledge.
"""
from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .terms import TERMS, TIERS, ORDER, Term
from .bash_lessons import LESSONS, LEVELS, Lesson

STATUS_MARK = {"mastered": "[good]●[/good]", "practiced": "[warn]◐[/warn]", "seen": "○", "unseen": "[dim]·[/dim]"}


class _Safe(dict):
    def __missing__(self, key):
        return "?"


def example_for(s, term: Term) -> str:
    from ..game.engine import example_vars
    try:
        return term.example.format_map(_Safe(example_vars(s.game)))
    except (ValueError, IndexError):
        return term.example


def term_text(s, term: Term) -> str:
    """Plain-text notebook entry (this is what lands in the file)."""
    related = ", ".join(TERMS[r].name for r in term.related if r in TERMS)
    return (f"# {term.name}\n\n"
            f"Category: {term.category} | Curriculum stage {term.tier}: {TIERS[term.tier]}\n\n"
            f"WHAT IT IS\n{term.definition}\n\n"
            f"WHY IT MATTERS\n{term.why}\n\n"
            f"IN YOUR COMPANY (week {s.game.week})\n{example_for(s, term)}\n\n"
            f"RELATED: {related or '-'}\n")


def lesson_text(lesson: Lesson) -> str:
    examples = "\n".join(f"  $ {cmd:<52} # {text}" for cmd, text in lesson.examples)
    return (f"# {lesson.title}\n\n"
            f"Shell skill | Stage {lesson.level}: {LEVELS[lesson.level]}\n\n"
            f"WHAT IT DOES\n{lesson.what}\n\n"
            f"EXAMPLES\n{examples}\n\n"
            f"WORKING WITH AGENTS\n{lesson.tip}\n\n"
            f"TRY IT\n  $ {lesson.try_it}\n")


def _write_entry(s, key: str, text: str) -> None:
    index = len(s.game.notebook)
    s.fs.write(s.path(f"notebook/{index:03d}_{key}.md"), text, force=True)


def learn(s, term_id: str, silent: bool = False) -> bool:
    """Unlock a vocabulary term. Returns True if it was new in this run.
    Prerequisite terms are unlocked quietly first, so the notebook never
    has a term whose building blocks are missing."""
    g = s.game
    if term_id not in TERMS or term_id in g.notebook:
        return False
    term = TERMS[term_id]
    added = []
    for need in term.needs:
        if need not in g.notebook and need in TERMS:
            learn(s, need, silent=True)
            added.append(TERMS[need].name)
    known_before = s.profile.term_status(term_id)
    g.notebook.append(term_id)
    s.profile.see(term_id)
    _write_entry(s, term_id, term_text(s, term))
    if silent or s.quiet_learning:
        return True
    if known_before == "mastered":
        s.io.print(f"[dim]📓 {term.name} - you've mastered this. (`nb {term_id}` to reread)[/dim]")
        return True
    s.panels_shown += 1
    if s.panels_shown > 2:          # never a wall of definitions: the rest wait in the notebook
        s.io.print(f"[dim]📓 Also new in your notebook: [/dim][term]{term.name}[/term][dim] - read it with `nb {term_id}`[/dim]")
        return True
    body = Text()
    body.append(term.definition + "\n\n")
    body.append("Why it matters: ", style="bold")
    body.append(term.why + "\n\n")
    body.append("Your company: ", style="bold")
    body.append(example_for(s, term))
    if added:
        body.append("\n\nBuilds on: " + ", ".join(added) + " (also added to your notebook)", style="dim")
    related = [TERMS[r].name for r in term.related if r in TERMS][:4]
    if related:
        body.append("\nRelated: " + ", ".join(related), style="dim")
    title = f"📓 New concept: {term.name}" if known_before == "unseen" else f"📓 Again: {term.name}"
    s.io.print(Panel(body, title=title, subtitle=f"saved to notebook · nb {term_id}",
                     border_style="cyan", title_align="left", subtitle_align="right"))
    return True


def learn_bash(s, lesson_id: str) -> bool:
    """Unlock a shell lesson the first time the player uses the command."""
    g = s.game
    key = "sh_" + lesson_id
    if lesson_id not in LESSONS or key in g.notebook:
        return False
    lesson = LESSONS[lesson_id]
    known_before = s.profile.bash_status(lesson_id)
    g.notebook.append(key)
    _write_entry(s, key, lesson_text(lesson))
    if s.quiet_learning:
        return True
    if known_before == "mastered":
        return True
    body = Text()
    body.append(lesson.what + "\n")
    for cmd, text in lesson.examples[:3]:
        body.append(f"\n  $ {cmd}", style="bold magenta")
        body.append(f"   # {text}", style="dim")
    body.append("\n\nWith agents: ", style="bold")
    body.append(lesson.tip)
    s.io.print(Panel(body, title=f"🖥  Shell skill: {lesson.title}", subtitle=f"nb {lesson_id} · man {lesson_id}",
                     border_style="magenta", title_align="left", subtitle_align="right"))
    return True


# ------------------------------------------------------------------ screens
def find_entries(s, query: str) -> list[str]:
    """Search unlocked entries by id, name or text."""
    q = query.lower().replace(" ", "_")
    hits = []
    for key in s.game.notebook:
        if key.startswith("sh_"):
            lesson = LESSONS[key[3:]]
            text = (lesson.id + " " + lesson.title + " " + lesson.what + " " + lesson.tip).lower()
        else:
            term = TERMS[key]
            text = (term.id + " " + term.name + " " + term.definition + " " + term.why).lower()
        if q in key.lower() or query.lower() in text:
            hits.append(key)
    return hits


def show_entry(s, key: str) -> None:
    if key.startswith("sh_"):
        s.io.print(Panel(Text(lesson_text(LESSONS[key[3:]])), border_style="magenta"))
    else:
        term = TERMS[key]
        status = s.profile.term_status(key)
        s.io.print(Panel(Text(term_text(s, term)), border_style="cyan", subtitle=f"status: {status}"))


def notebook_overview(s):
    g = s.game
    table = Table(title=f"Founder's Notebook - {len(g.notebook)} entries this run", title_justify="left",
                  box=None, padding=(0, 2))
    table.add_column("#", style="dim", justify="right")
    table.add_column("entry")
    table.add_column("kind", style="dim")
    table.add_column("status")
    for i, key in enumerate(g.notebook, 1):
        if key.startswith("sh_"):
            lesson = LESSONS[key[3:]]
            table.add_row(str(i), f"[cmd]{lesson.id}[/cmd]", "shell", STATUS_MARK[s.profile.bash_status(lesson.id)])
        else:
            term = TERMS[key]
            table.add_row(str(i), f"[term]{term.name}[/term]", term.category, STATUS_MARK[s.profile.term_status(key)])
    hint = Text("nb <word> opens an entry · nb search <text> searches · files live in ~/company/notebook "
                "(try: grep -ril runway notebook)", style="dim")
    return Group(table, hint)


def glossary(s):
    """The curriculum map: every term by stage, coloured by mastery."""
    p = s.profile
    parts = []
    counts = p.counts()
    done = counts["mastered"]
    bar = "█" * int(30 * done / counts["terms"]) + "░" * (30 - int(30 * done / counts["terms"]))
    parts.append(Text.from_markup(
        f"[title]Curriculum progress[/title]  {bar}  {done}/{counts['terms']} terms mastered, "
        f"{counts['practiced']} practiced, {counts['seen']} seen   ·   shell: "
        f"{counts['bash_mastered']}/{counts['bash']} mastered\n"
        f"[good]●[/good] mastered (used/answered correctly twice)   [warn]◐[/warn] practiced   ○ seen   [dim]· not met yet[/dim]\n"))
    for tier, title in TIERS.items():
        terms = [t for t in TERMS.values() if t.tier == tier]
        mastered = sum(p.term_status(t.id) == "mastered" for t in terms)
        cells = []
        for t in terms:
            status = p.term_status(t.id)
            in_run = t.id in s.game.notebook
            name = t.name if status != "unseen" or in_run else f"[dim]{t.name}[/dim]"
            cells.append(f"{STATUS_MARK[status]} {name}")
        grid = Table.grid(padding=(0, 3))
        for _ in range(3):
            grid.add_column()
        for i in range(0, len(cells), 3):
            grid.add_row(*(cells[i:i + 3] + [""] * 3)[:3])
        parts.append(Panel(grid, title=f"Stage {tier}: {title}  ({mastered}/{len(terms)})",
                           title_align="left", border_style="cyan" if mastered < len(terms) else "green"))
    grid = Table.grid(padding=(0, 3))
    for _ in range(4):
        grid.add_column()
    cells = [f"{STATUS_MARK[p.bash_status(l.id)]} {l.id}" for l in LESSONS.values()]
    for i in range(0, len(cells), 4):
        grid.add_row(*(cells[i:i + 4] + [""] * 4)[:4])
    parts.append(Panel(grid, title="Shell skills (in teaching order)", title_align="left", border_style="magenta"))
    return Group(*parts)


def weakest_terms(s, limit: int = 5) -> list[str]:
    """Terms worth practising next: struggled first, then seen-not-mastered."""
    p = s.profile
    out = p.struggling()
    for term in ORDER:
        if term in s.game.notebook and p.term_status(term) in ("seen", "practiced") and term not in out:
            out.append(term)
    return out[:limit]
