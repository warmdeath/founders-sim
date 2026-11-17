# CLAUDE.md — project memory for coding agents

Read `SPEC.md` (the original brief, saved verbatim) before changing behaviour. `REVIEW.md` records the
decisions made while building and the known simplifications.

## Goal

A terminal game that teaches an 18-year-old solo founder three things at once: real bash, agentic-AI
working practices, and the vocabulary of startups / VC / corporate finance. **Learning tool first, game
second.** The player controls everything through a simulated bash shell over a virtual filesystem.

Non-negotiables from the spec:

- The shell is the interface. No numbered menus as the main UI (arrow-key lists only for dialogue choices).
- Implemented bash commands must match real bash: syntax, flags, error text.
- Sandboxed: commands touch only the virtual filesystem. The only real files are in `~/.founders_sim/`
  (profile, save, history), overridable with `FOUNDERS_SIM_HOME`.
- Every mechanic teaches its real-world concept the first time it appears and stores it in the Notebook.
  Never a wall of definitions (max two concept panels per command; the rest become one-line notes).
- Concepts must be accurate; simplifications are stated (in code comments and `REVIEW.md`).
- Runs build on each other through the persistent learner profile.

## Run and test

```bash
pip install -r requirements.txt
python3 -m founders_sim            # play (continues a save)
python3 -m founders_sim --new --seed 3
python3 -m pytest                  # 59 tests, about 2 seconds
```

Non-interactive smoke test (commands on stdin, no TTY needed):

```bash
printf 'pwd\nls\nstatus\nquit\n' | FOUNDERS_SIM_HOME=/tmp/fs python3 -m founders_sim --new
```

## Architecture

```
founders_sim/
  app.py              entry point: start/load a run, main read-run loop, prompt_toolkit session
  vfs.py              virtual filesystem (Node/File/Dir/VFS), bash-style errors
  save.py             JSON save/load of game + filesystem + shell state
  shell/
    parser.py         tokenizer + recursive-descent parser (quotes, pipes, redirects, for/if)
    interpreter.py    Shell: expansion, globbing, pipelines, redirection, aliases, scripts, hooks
    coreutils.py      simulated unix commands (ls, cat, grep, sort, find, chmod, ...)
    completion.py     Tab completion (commands, paths, game entities)
  learn/
    terms.py          THE VOCABULARY CURRICULUM: 176 ordered terms (data)
    bash_lessons.py   the bash curriculum: lessons + man pages (data)
    notebook.py       unlocking terms/lessons, notebook and glossary screens
    profile.py        persistent learner profile (mastery across runs)
    missions.py       run-1 tutorial missions, `tutor`, shell challenges
    situations.py     terms unlocked when the company reaches a state (checked weekly)
  game/
    state.py          dataclasses for all game state (+ JSON conversion)
    scenarios.py      four scenarios, investors, hire candidates, difficulty levels, new_game()
    session.py        Session = game + fs + io + profile; hooks called after each command
    engine.py         metrics formulas and the weekly tick
    agents.py         specs, agent runs, review, merge, tech debt, workflow upgrades
    customers.py      interviews, idea choice, pricing, channels, B2B pipeline
    funding.py        cap table, pitch, term sheets, loans, hiring/vesting, acquisitions
    events.py         random world events, mentor emails, decision replies
    quiz.py           questions asked by investors/bankers/advisor
    files.py          mirrors game state into files in the virtual filesystem
    commands.py       the game commands and their man pages
    debrief.py        endings, debrief, planning the next run
  ui/
    io.py             IO abstraction: TerminalIO (real) and ScriptedIO (tests)
    choices.py        arrow-key selection list
    dashboard.py      Textual full-screen dashboard (`dash`)
tests/
  helpers.py          make_session(), run(), and Bot (plays whole runs through shell commands)
```

Data flow: `app.play()` reads a line → `Shell.run_line()` parses and executes it → command functions
(`coreutils.py`, `commands.py`) receive a `Ctx` → game modules mutate `Session.game`, print via
`Session.io`, teach via `Session.learn()` → `Session.after_line()` unlocks shell lessons, teaches terms
for files just read, and advances tutorial missions.

## Conventions

- Game logic never calls `print()`/`input()`: always `s.io` (so tests can use `ScriptedIO`).
- All randomness goes through `game.rng` (seeded, saved) so runs are reproducible.
- Game state lives only in `game/state.py` dataclasses made of plain JSON-able fields. Files in the VFS
  are a *view* of state, rebuilt by `files.sync()`; never read game state back from VFS files (player
  -authored files such as specs are the exception).
- A command function returns an exit code (0 = success) like a real program; errors go to `ctx.err`.
- Output that should be pipeable goes through `ctx.out/line/show`, not straight to `s.io`.
- New term → add to `learn/terms.py` in curriculum position (prerequisites earlier; a test enforces it),
  then call `s.learn("id")` where the situation arises (or add a condition to `learn/situations.py`) and
  `s.credit("id")` when the player applies it. A test fails if any term is unreachable.
- Mastery pacing: `quiz.question_of_the_week` (1 question in run 1, 2 afterwards) is the main source of
  credits; simulated players reach ~140 mastered terms in 5-6 runs. Re-check if you change it.
- New bash command → implement in `coreutils.py` with real flags and error messages, add a `Lesson`
  (or an `EXTRA_MAN` entry) and a test in `tests/test_shell.py`.
- New game command → function in `commands.py`, entry in `GAME_MAN`, row in `register_game_commands`,
  completion entry in `_complete_table` if it takes entities.
- Balance changes: re-run the bots (see `tests/helpers.py::Bot`). Targets: careless bot (skill 0.3)
  loses; mid bot (0.75) wins around week 40–55; expert bot (1.0) around week 30.
- Code should stay readable for a beginner: short functions, docstrings that explain the *concept*.
- Commit after each working milestone; keep `python3 -m pytest` green.

## Status

All features in `SPEC.md` are implemented. Ideas for next features are listed at the end of `REVIEW.md`.
