"""A Session ties one run together: the game state, the virtual
filesystem, the screen (io) and the learner profile.

Every game module receives the session as `s`, so a function like
`interview(s, lead)` can change numbers (s.game), write files (s.fs),
talk to the player (s.io) and teach a term (s.learn) in one place.
"""
from __future__ import annotations

from rich.panel import Panel

from ..vfs import VFS, COMPANY
from ..ui.io import IO
from ..learn.profile import Profile
from .state import Game, Email


def money(amount: float) -> str:
    """12345.6 -> '$12,346' ; -500 -> '-$500'"""
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.0f}"


def slug(text: str) -> str:
    keep = "".join(c.lower() if c.isalnum() else "_" for c in text)
    while "__" in keep:
        keep = keep.replace("__", "_")
    return keep.strip("_")[:32]


class Session:
    def __init__(self, game: Game, fs: VFS, io: IO, profile: Profile):
        self.game = game
        self.fs = fs
        self.io = io
        self.profile = profile
        self.shell = None           # set by app.py once the shell exists
        self.quiet_learning = False  # tests can silence concept panels
        self.panels_shown = 0        # concept panels printed for the current command line
        self.pending_lessons: list[str] = []   # shell lessons to show once the command finishes

    # ----------------------------------------------------------- talking
    def say(self, text: str = "", **kwargs) -> None:
        self.io.print(text, **kwargs)

    def note(self, text: str) -> None:
        """A dim side remark (tips, consequences)."""
        self.io.print(f"[dim]{text}[/dim]")

    def good(self, text: str) -> None:
        self.io.print(f"[good]✔[/good] {text}")

    def bad(self, text: str) -> None:
        self.io.print(f"[bad]✘[/bad] {text}")

    def panel(self, body, title: str = "", style: str = "cyan") -> None:
        self.io.print(Panel(body, title=title, border_style=style, title_align="left"))

    # ---------------------------------------------------------- learning
    def learn(self, *terms: str) -> None:
        from ..learn import notebook
        for term in terms:
            notebook.learn(self, term)

    def credit(self, term: str, ok: bool = True) -> None:
        """Record that the player used/answered a term correctly (or not)."""
        from ..learn import notebook
        notebook.learn(self, term, silent=True)
        self.profile.credit(term, ok)

    # ---------------------------------------------------------- resources
    def spend_hours(self, hours: float, what: str) -> bool:
        g = self.game
        if g.hours < hours:
            self.bad(f"Not enough hours left this week for {what}: needs {hours:g}h, you have {g.hours:g}h. "
                     f"End the week with [cmd]next[/cmd] (or [cmd]crunch[/cmd] for extra hours at an energy cost).")
            return False
        g.hours -= hours
        return True

    def pay(self, amount: float, what: str = "") -> None:
        """Spend cash right now (also counted in this week's costs)."""
        self.game.cash -= amount
        self.game.week_costs_extra += amount

    # -------------------------------------------------------------- mail
    def mail(self, sender: str, subject: str, body: str, kind: str = "info", ref: str = "") -> Email:
        from . import files
        g = self.game
        email = Email(len(g.emails) + 1, sender, subject, body, g.week, kind, ref)
        g.emails.append(email)
        files.write_email(self, email)
        return email

    def path(self, relative: str) -> str:
        return f"{COMPANY}/{relative}"

    def learn_some(self, terms: list[str], limit: int = 2) -> None:
        """Teach at most `limit` new terms at once - never a wall of definitions."""
        shown = 0
        for term in terms:
            if term not in self.game.notebook:
                self.learn(term)
                shown += 1
                if shown >= limit:
                    break

    # ------------------------------------------------- shell practice hooks
    def on_use(self, feature: str, ok: bool) -> None:
        """Called by the shell for every command / shell feature used."""
        from ..learn.bash_lessons import LESSONS
        g = self.game
        if ok:
            g.used[feature] = g.used.get(feature, 0) + 1
        if feature in LESSONS:
            self.profile.bash_use(feature, ok)
            if ok and "sh_" + feature not in g.notebook and feature not in self.pending_lessons:
                self.pending_lessons.append(feature)

    def after_line(self, line: str) -> None:
        """Called by the main loop after each command line has run:
        notices shell skills that live in the SYNTAX (flags, paths),
        unlocks lessons, teaches terms for files just read, checks missions."""
        import re
        from ..learn import notebook, missions
        g = self.game
        words = line.split()
        if re.search(r"(^|[;&|]\s*)ls\s+-[a-zA-Z]*[la]", line):
            g.bump("ls_flags_used")
            self.on_use("ls_flags", True)
        if re.search(r"(^|\s)(\.\.|~|/home|\./)", line):
            g.bump("paths_used")
            self.on_use("paths", True)
        if "--help" in words or (words and words[0] == "man"):
            self.on_use("man", True)
        for lesson in self.pending_lessons:
            notebook.learn_bash(self, lesson)
        self.pending_lessons.clear()
        if words and words[0] in ("cat", "less", "more", "head", "tail", "grep") and self.shell and self.shell.last_status == 0:
            for needle, terms in FILE_TERMS.items():
                if needle in line:
                    if needle == "market.md":
                        g.flags["read_market"] = 1
                    self.learn_some(terms, 2)
        missions.check_missions(self)
        self.panels_shown = 0


# reading these files teaches the matching vocabulary
FILE_TERMS = {
    "market.md": ["tam", "sam", "som"],
    "captable": ["equity", "cap_table"],
    "pnl.txt": ["income_statement", "ebitda", "net_income"],
    "termsheets/": ["term_sheet"],
    "finance/bank": ["debt", "interest"],
    "loans.txt": ["principal", "amortization"],
    ".deal": ["pipeline", "champion"],
    "tests.log": ["tests"],
    "usage.log": ["token", "compute_budget"],
    "AGENTS.md": ["agents_md"],
    "ideas.md": ["startup", "problem"],
}
