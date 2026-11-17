"""The program's entry point: start or load a run, then loop
"read a command -> run it -> react" until the run ends.

    python3 -m founders_sim            # play (continues a saved run if there is one)
    python3 -m founders_sim --new      # abandon the save and start a new run
    python3 -m founders_sim --profile  # show your learner profile and exit
"""
from __future__ import annotations

import argparse
import random
import sys

from rich.panel import Panel
from rich.text import Text

from . import save as savefile
from .vfs import VFS, COMPANY
from .ui.io import IO, TerminalIO
from .shell.interpreter import Shell
from .shell.coreutils import register_coreutils
from .learn.profile import Profile, data_dir
from .learn import missions, notebook
from .learn.terms import TERMS
from .game import files, debrief, engine
from .game.commands import register_game_commands, GAME_MAN, _man_text
from .game.scenarios import SCENARIOS, new_game
from .game.session import Session, money

BANNER = r"""
  ___                 _           _      ___ _
 | __|__ _  _ _ _  __| |___ _ _  ( )___ / __(_)_ __
 | _/ _ \ || | ' \/ _` / -_) '_| |/(_-< \__ \ | '  \
 |_|\___/\_,_|_||_\__,_\___|_|     /__/ |___/_|_|_|_|
"""


def build_shell(s: Session, state: dict | None = None) -> Shell:
    """Create the simulated shell for a session and plug the game into it."""
    sh = Shell(s.fs, s.io, s.game)
    s.shell = sh
    register_coreutils(sh)
    register_game_commands(sh, s)
    sh.on_use = s.on_use
    sh.env["COMPANY_NAME"] = s.game.company
    if state:
        sh.env.update(state.get("env", {}))
        sh.aliases.update(state.get("aliases", {}))
        sh.exported |= set(state.get("exported", []))
        if s.fs.is_dir(state.get("cwd", COMPANY)):
            sh.cwd = state["cwd"]
    sh.aliases.update({"st": "status", "m": "metrics", "nb": "notebook", "gl": "glossary", "cap": "captable"})

    def cmd_save(ctx):
        savefile.save(s)
        ctx.line(f"Saved to {savefile.save_path()}")

    def cmd_quit(ctx):
        sh.exit_requested = True

    def cmd_dash(ctx):
        if not s.io.interactive or not sys.stdout.isatty():
            ctx.line("dash needs a real terminal. Use `metrics` instead.")
            return 1
        from .ui.dashboard import run_dashboard
        run_dashboard(s)

    for name, fn in (("save", cmd_save), ("quit", cmd_quit), ("dash", cmd_dash)):
        sh.register(name, fn, "game", GAME_MAN[name][0].split(" - ", 1)[1])
        sh.manpages[name] = _man_text(name)
    sh.commands["exit"] = sh.commands["logout"] = sh.commands["quit"]
    return sh


def choose_scenario(io: IO, profile: Profile) -> str:
    """Run 1 is always the guided B2C scenario; later the player chooses,
    with the scenario that covers untouched topics recommended."""
    if profile.runs == 0:
        return "focusly"
    _, recommended = debrief.plan_next_run(profile, profile.endings[-1]["scenario"] if profile.endings else "")
    keys = [recommended] + [k for k in SCENARIOS if k != recommended]
    options = []
    for key in keys:
        sc = SCENARIOS[key]
        played = profile.scenarios.get(key, 0)
        options.append(f"{sc.company} - {sc.tagline}" + ("  ★ recommended for what you haven't learned yet" if key == recommended else "")
                       + (f"  (played {played}x)" if played else ""))
    return keys[io.choose("\nChoose your next company:", options)]


def start_new(io: IO, profile: Profile, scenario: str | None = None, seed: int | None = None) -> Session:
    scenario = scenario or choose_scenario(io, profile)
    run_number = profile.runs + 1
    game = new_game(scenario, run_number, seed if seed is not None else random.randrange(1 << 30),
                    focus=profile.next_focus)
    game.mastered_start = [t for t in TERMS if profile.term_status(t) == "mastered"]
    s = Session(game, VFS(), io, profile)
    files.setup(s)
    profile.save()
    return s


def intro(s: Session) -> None:
    g = s.game
    sc = SCENARIOS[g.scenario]
    io = s.io
    io.print(Text(BANNER, style="bold cyan"))
    io.print(Panel(
        f"[bold]Run {g.run_number} · {g.company}[/bold] - {sc.tagline}\n\n{sc.intro}\n\n"
        f"Cash: {money(g.cash)} · {g.max_weeks} weeks · difficulty {g.level}/5\n"
        "Win: become profitable, close a priced funding round, or get acquired.\n"
        "Lose: run out of cash, or burn out.",
        border_style="cyan", title="A startup-founder simulator you play in a shell", title_align="left"))
    if g.focus:
        io.print("[warn]This run steers you toward:[/warn] "
                 + "; ".join(debrief.TOPICS[t][0] for t in g.focus if t in debrief.TOPICS))
    if g.guided:
        io.print("This is a simulated [bold]bash[/bold] shell. The commands are real - what you learn here works in any "
                 "Linux terminal. Nothing you type can touch your real computer.\n"
                 "[dim]Tab completes · ↑ recalls · Ctrl+R searches history · → accepts the grey suggestion · "
                 "`help` lists commands · `quit` saves and exits[/dim]")
        io.print(missions.mission_panel(s))
    else:
        io.print("[dim]No tutorial this time. `tutor` suggests next steps, `help` lists commands, "
                 "`cat inbox/001*` is your mentor's welcome.[/dim]")


def prompt_text(s: Session) -> str:
    host = "".join(c for c in s.game.company.lower() if c.isalnum()) or "startup"
    return f"founder@{host}:{s.shell.prompt_path()}$ "


def make_reader(s: Session):
    """Returns a function that reads one command line. In a real terminal it
    is a prompt_toolkit session (completion, history, suggestions)."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        def plain() -> str:
            line = sys.stdin.readline()
            if not line:
                raise EOFError
            s.io.write(prompt_text(s) + line)
            return line
        return plain

    from prompt_toolkit import PromptSession
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.shortcuts import CompleteStyle
    from .shell.completion import ShellCompleter

    keys = KeyBindings()

    @keys.add("up")
    def _up(event):                       # same as default, but we notice the skill being used
        s.on_use("up_arrow", True)
        event.current_buffer.auto_up(count=event.arg)

    session = PromptSession(history=FileHistory(str(data_dir() / "history")),
                            auto_suggest=AutoSuggestFromHistory(), completer=ShellCompleter(s.shell),
                            complete_while_typing=False, complete_style=CompleteStyle.COLUMN,
                            key_bindings=keys, enable_history_search=False)

    def fancy() -> str:
        g = s.game
        m = engine.metrics(g)
        bar = (f" week {g.week}/{g.max_weeks} · {g.hours:g}h left · cash {money(g.cash)} · runway {engine.fmt_runway(m)} · "
               f"energy {g.energy:.0f} · MRR {money(m['mrr'])} ")
        text = FormattedText([("ansigreen bold", f"founder@{''.join(c for c in g.company.lower() if c.isalnum())}"),
                              ("", ":"), ("ansiblue bold", s.shell.prompt_path()), ("", "$ ")])
        return session.prompt(text, bottom_toolbar=bar)
    return fancy


def play(s: Session) -> str:
    """The main loop. Returns 'ended' (run finished) or 'quit'."""
    sh = s.shell
    read = make_reader(s)
    while True:
        try:
            line = read()
        except KeyboardInterrupt:
            continue                       # Ctrl+C clears the line, like bash
        except EOFError:                   # Ctrl+D
            s.io.write("exit\n")
            break
        week_before = s.game.week
        sh.run_line(line)
        s.after_line(line)
        if s.game.ended:
            debrief.finish_run(s)
            savefile.delete_save()
            return "ended"
        if sh.exit_requested:
            break
        if s.game.week != week_before:
            savefile.save(s)               # autosave every week
    savefile.save(s)
    s.io.print(f"[dim]Game saved. Run `python3 -m founders_sim` to continue.[/dim]")
    return "quit"


def show_profile(io: IO, profile: Profile) -> None:
    game = new_game("focusly", profile.runs + 1)
    s = Session(game, VFS(), io, profile)
    io.print(f"[title]Learner profile[/title] - {profile.runs} completed run(s)")
    for e in profile.endings:
        io.print(f"  run {e['run']}: {SCENARIOS[e['scenario']].company} → {e['ending']} after {e['weeks']} weeks, MRR {money(e['mrr'])}")
    io.print(notebook.glossary(s))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="founders_sim", description="Startup-founder simulator in a simulated bash shell.")
    parser.add_argument("--new", action="store_true", help="start a new run (discarding any saved run)")
    parser.add_argument("--scenario", choices=list(SCENARIOS), help="pick the scenario directly")
    parser.add_argument("--seed", type=int, help="random seed (for reproducible runs)")
    parser.add_argument("--profile", action="store_true", help="show your learner profile and exit")
    parser.add_argument("--reset-profile", action="store_true", help="forget everything you've learned (asks first)")
    args = parser.parse_args(argv)
    io = TerminalIO()
    profile = Profile.load()
    if args.reset_profile:
        if io.choose("Really delete your learner profile and saved run?", ["No", "Yes, delete"]) == 1:
            savefile.delete_save()
            profile = Profile()
            profile.save()
            io.print("Profile reset.")
        return 0
    if args.profile:
        show_profile(io, profile)
        return 0
    while True:
        s, state = None, None
        if savefile.has_save() and not args.new:
            loaded = savefile.load(io, profile)
            if loaded is None:
                io.print("[bad]The save file could not be read; starting a new run.[/bad]")
            else:
                s, state = loaded
                io.print(f"[good]Continuing {s.game.company}, week {s.game.week}.[/good] "
                         "[dim](`python3 -m founders_sim --new` starts over)[/dim]")
        fresh = s is None
        if fresh:
            s = start_new(io, profile, args.scenario, args.seed)
        build_shell(s, state)
        if fresh:
            intro(s)
        elif s.game.guided and s.game.mission < len(missions.MISSIONS):
            io.print(missions.mission_panel(s))
        args.new = False
        args.scenario = None
        if play(s) == "quit":
            return 0
        if not sys.stdin.isatty() or io.choose("\nStart the next run now?", ["Yes", "No, quit"]) == 1:
            return 0


if __name__ == "__main__":
    sys.exit(main())
