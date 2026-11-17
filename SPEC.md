# SPEC — original project prompt (saved verbatim)

First, save this entire prompt as SPEC.md in the repo, and create a CLAUDE.md with the project goals, architecture, conventions and how to run tests, keeping it updated as you work. Future sessions will rely on these files.

Build a complete, advanced, playable startup-founder simulator in Python as a terminal game. Work autonomously until it's done; commit after each working milestone; write tests for the game logic; never leave the repo broken. Don't stop to ask questions: make sensible decisions and document them in REVIEW.md.

PLAYER: an 18-year-old solo founder on Windows (running WSL/Ubuntu), learning startups, agentic AI and the real terminal. This is a learning tool first, a game second. Every mechanic must explain the real-world concept behind it the first time it appears, and record it in an in-game "Founder's Notebook" the player can reread and search.

CORE LOOP: turn-based weeks. Each week the player has limited hours + energy and chooses actions. Resources: cash, runway, hours, energy/morale, reputation, product quality, users/revenue, equity cap table. Include a metrics overview like a real founder would track.

PILLAR 1 — Agentic AI as the founder's workforce:
- The player builds the product by directing AI agents, not typing code. Mechanics model real best practices: writing clear specs, breaking work into tasks, giving context, reviewing agent output, tests as guardrails, parallel agents vs. coordination cost, token/compute budget, hallucinated or buggy output that slips through if review is skipped, technical debt.
- Upgrades unlock better workflows (planning first, subagents, automated tests, eval suites), each with a real-world explanation.

PILLAR 2 — The startup and the world around it:
- Ideas & validation: generating ideas, customer interviews (talking to customers reveals hidden needs; skipping it raises failure risk), problem/solution fit, product-market fit signals.
- Money: burn rate, runway, unit economics (CAC, LTV, churn, margins, MRR/ARR), pricing.
- Investors: finding investors (angels, accelerators, VCs), pitching (pitch deck sections, key numbers investors ask for), valuation, dilution, term sheet basics (pre/post-money, SAFE, liquidation preference, vesting), cap table.
- The wider world: banks and loans, large corporations as customers/competitors/acquirers, B2B sales cycles, competitors launching, market events, moat, go-to-market, TAM/SAM/SOM.
- Win conditions: profitable company, a successful raise, or an acquisition. Lose conditions: running out of cash or burnout.

VOCABULARY CURRICULUM (very important):
- By the end of the full progression the player must know, in depth, the vocabulary of startups, venture capital, corporate finance and agentic AI.
- Design an ordered curriculum: terms are introduced in a logical sequence, each building on earlier ones (e.g. revenue -> burn -> runway -> valuation -> dilution -> cap table), unlocked when the matching situation arises in play, never as a wall of definitions.
- For each term: plain-language definition, why it matters, a concrete example using the player's own company numbers, related terms.
- Investors, advisors and customers use these terms in dialogue; sometimes the player must answer correctly (e.g. an investor asks for your CAC) and wrong answers have consequences.
- A glossary screen shows mastered vs. unseen terms and curriculum progress.

INTERFACE — A SIMULATED BASH SHELL (very important):
- The whole game is controlled through a simulated bash-like shell with a prompt (e.g. founder@startup:~/company$). Do not use numbered menus as the main interface.
- The company is a virtual filesystem (a Python data structure): directories like ~/company/{product,customers,investors,finance,team,agents,inbox,notebook}; files are real game content (emails, term sheets, interview notes, metrics, specs). Game actions are commands (e.g. `pitch investors/angel_rossi`, `agent run spec.md`, `interview customers/acme`) alongside real bash commands.
- Teach real bash progressively as part of the curriculum, in a sensible order: pwd, ls (-l, -a), cd (., .., ~, absolute vs relative paths), cat, less, head/tail, mkdir, touch, cp, mv, rm, echo, redirection (>, >>), pipes (|), grep, wc, sort, find, history, tab completion, up-arrow recall, man/--help, environment variables, chmod/permissions basics, simple scripts. Each command gets a Notebook entry, with real-world tips for working with coding agents in a terminal.
- Behave like real bash where implemented (same syntax, flags and error messages) so skills transfer directly. Unknown commands give a helpful hint. Include `help`, `man <cmd>`, and a `tutor` command that suggests the next thing to learn.
- Some challenges require combining commands (e.g. find which customers mentioned "pricing" with grep, count unread emails with ls | wc -l).
- Use prompt_toolkit for: Tab completion of commands, paths and game entities (dropdown menu on double Tab), persistent history (up arrow, Ctrl+R search), fish-style autosuggestions from history (right arrow to accept), and arrow-key selection lists for in-game choices like dialogue answers during pitches or negotiations. Use rich for output (panels, tables, colors, text charts). Keep commands short; aliases are fine.
- A `dash` command opens a full-screen live dashboard of company metrics (Textual); q returns to the shell.
- Sandboxed: commands only affect the virtual filesystem, never the player's real machine.

QUALITY BAR & PROGRESSION: concepts must be accurate (state what's simplified). The game is designed for multiple playthroughs that build on each other:
- Each run is a substantial 3-5 hour company journey. A careless player fails; a thoughtful one can win.
- A persistent learner profile (saved across runs) tracks which terms, bash commands and mechanics the player has seen, used correctly, or struggled with.
- Difficulty and depth scale across runs: the first run is a guided, forgiving introduction to the core loop; later runs remove hand-holding, raise the stakes (tougher investors, competitors, market shocks) and deliberately steer the player toward untouched or weak topics (e.g. different business models, B2B vs B2C, bootstrapping vs VC, debt vs equity, acquisition offers).
- Different starting scenarios and win paths so each run feels different.
- After each run, show a debrief: what went well, mistakes and what a real founder would have done, terms mastered, and what the next run will focus on.
- Full curriculum mastery should take roughly 4-6 runs. Include a tutorial in the first run and save/load.

README: step-by-step for Windows: install WSL (Ubuntu) and Windows Terminal, then clone and run the game from real bash, teaching the real commands used during setup (cd, ls, python3, pip, venv, git clone) as the very first lesson.

CODE: modular and readable, clear file names and comments, so a beginner can later study individual parts (secondary goal, don't sacrifice the game for it).

When finished, write REVIEW.md: architecture overview, which files a beginner should read first, decisions made, known simplifications, the full vocabulary and bash curriculum in order, and 5 ideas for next features.
