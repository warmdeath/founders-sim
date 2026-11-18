# REVIEW — how Founder's Sim is built

Written at the end of the build and updated after the second pass (a full playtest of two runs, a
curriculum audit and a README check). `SPEC.md` is the brief; this file records how it was met, what was
decided along the way, and what is knowingly simplified. `PLAYTEST.md` lists every problem the playtest
found and what was done about each.

## 1. Architecture overview

The program is four layers, each knowing only about the ones below it:

```
app.py            the main loop: read a line → run it → react → (weekly) autosave
  │
shell/            a small bash: parser → interpreter → commands           (knows nothing about startups)
  │
game/  learn/     the simulation and the curriculum                       (know nothing about terminals)
  │
vfs.py  ui/io.py  the virtual filesystem and the screen
```

**One command, end to end.** You type `grep -c FAIL agents/runs/run_001/tests.log | wc -l`:

1. `app.play()` reads the line with prompt_toolkit (history, Tab completion, suggestions).
2. `shell/parser.py` turns the text into a tree: a pipeline of two simple commands.
3. `shell/interpreter.py` expands words (variables, `*` globs, `$(...)`), runs `grep` with its output
   captured, and feeds that text to `wc` as stdin. Redirections (`>`, `>>`, `2>`) are applied here.
4. `shell/coreutils.py` holds `cmd_grep` and `cmd_wc`. They read the **virtual** filesystem (`vfs.py`) and
   print exactly what the real tools would print.
5. Back in `app.play()`, `Session.after_line()` notices you used a pipe and `grep` for the first time,
   unlocks those two shell lessons in the Notebook, and checks whether a tutorial mission is now complete.

**One game action.** `agent run product/specs/offline.md` is a function in `game/commands.py` that parses
flags and calls `agents.start_run()`. That function scores the spec, works out how many work points the
agents get done, charges compute for that work and your supervision hours, rolls the outcome with the
game's seeded random generator, stores an `AgentRun` in the state, asks `files.py` to
write `report.md`, `tests.log` and `diff.patch` into the virtual filesystem, and calls `s.learn("agent")`
so the concept is explained the first time. Concept panels are queued and printed after the command's own
output (`Session.show_later` / `flush_learning`), never more than two per command.

**One week.** `next` calls `engine.advance_week()`: signups and churn, revenue and costs, incidents, the
pipeline, then `funding.weekly()` (term sheets, loan offers, due diligence) and `events.weekly()` (mentor
mail, the new-customer-segment moment, random world events, shell challenges). After the report,
`situations.weekly_terms()` teaches up to two terms whose situation has arisen and the mentor asks one or
two practice questions.

**State.** Everything about a run is in `game/state.py` as plain dataclasses, which is why the whole game
saves to one JSON file. Files in the virtual filesystem are a *view* of that state (`files.sync()` rewrites
them), except files you create yourself — your specs are real input to the game.

**Two memories.** `Game` (one run, saved in `save.json`) and `Profile` (you, across all runs, saved in
`profile.json`). The profile records for every term whether you have seen it, used or answered it
correctly, or got it wrong; it drives the glossary, the weekly questions, the debrief, and what the next
run steers you toward.

**Testing.** `ui/io.py` has two implementations: `TerminalIO` (rich + prompt_toolkit) and `ScriptedIO`
(answers from a list, output into a buffer). Because game code only ever talks to an `IO`, tests drive the
real game through the real shell with no terminal. `tests/helpers.py` also contains a `Bot` that plays
entire runs by issuing shell commands; it was used to balance the game and guards it in the test suite.

## 2. Files a beginner should read first

In this order — each is short enough to read in one sitting and builds on the previous one:

1. `founders_sim/vfs.py` — a filesystem as a tree of Python objects. Classes, dicts, recursion.
2. `founders_sim/learn/terms.py` — pure data. See how a curriculum is just an ordered list.
3. `founders_sim/game/state.py` — dataclasses: the shape of the whole game on one page.
4. `founders_sim/game/engine.py` — the real formulas (MRR, burn, runway, LTV, CAC) as ten-line functions,
   and `advance_week()`, which is the entire simulation loop.
5. `founders_sim/game/agents.py` — how "spec quality → bugs" is modelled; every number is commented.
6. `founders_sim/shell/coreutils.py` — pick one command (`cmd_wc` is the smallest interesting one) and
   compare it with `man wc` in a real terminal.
7. `founders_sim/shell/parser.py` then `interpreter.py` — harder: how a shell understands a line.
8. `founders_sim/app.py` — how the pieces are wired together.
9. `tests/test_game.py` — tests read like a specification of the rules.

## 3. Decisions made (the brief said: decide, don't ask)

| Decision | Why |
|---|---|
| **Hours, cash and energy are the three budgets.** Reading and writing files is free; game actions cost hours; agents cost compute dollars. | Mirrors reality: looking is cheap, doing is not. It also means bash practice is never punished. |
| **Energy and morale are one stat.** | The brief lists "energy/morale" as one resource; two meters added bookkeeping without new decisions. |
| **Specs are real text files the player writes**, scored on structure (goal, context pointing at real files, 3–5 tasks, acceptance tests, out of scope, link to customer evidence). | The single most transferable agentic skill is writing the brief. The scorer can't judge meaning, but it rewards exactly the structure real agents need. |
| **An agent's report can lie; the files don't.** `report.md` is the agent's claim, `tests.log` and `diff.patch` are evidence. | "Trust but verify" becomes a `grep` you actually run. |
| **Interviews reveal hidden features and which idea has real pain; both are hidden numbers.** Building unrequested features wastes money and adds debt. | Makes "talk to customers" mechanically true rather than a slogan. |
| **Four scenarios on one engine** (B2C subscription, B2B SaaS, usage-priced AI API, marketplace), differing by parameters and content. | Different business models, one codebase a beginner can still read. |
| **Run 1 is always the B2C scenario with tutorial missions**; later runs let you choose, with a recommendation. | A guided, forgiving first run; real choice afterwards. |
| **Difficulty = run number (1–5):** less starting cash, tighter answer tolerance, tougher investors and terms, more and worse events, a more crowded market, fewer mentor hints, full win targets from run 3. | The brief's "later runs remove hand-holding and raise the stakes". |
| **Steering:** the debrief picks two topics you have never done (debt, B2B, priced round, acquisition, advanced agents...), rotates them, recommends a scenario, and the next run gives a mentor brief plus a small head start per topic and makes matching events likelier. | Deliberate practice instead of repeating the path you already know. |
| **Terms unlock from situations**, three ways: an action (`s.learn` in game code), reading a file (`FILE_TERMS`), or the company reaching a state (`learn/situations.py`, max two per week). Never more than two full panels per command; extra terms become one-line notes. A test proves every term is reachable. | "Unlocked when the matching situation arises, never as a wall of definitions." |
| **Mastery = used or answered correctly twice (and more often right than wrong).** Sources: investor/banker questions, a weekly question from your mentor (two from run 2), `quiz`, and applying a concept correctly (e.g. negotiating away a participating preference). | Seeing a definition is not knowing it. A simulated learner masters 155 of 191 terms in 6 runs. |
| **Wrong answers have consequences where a real person is listening**: investors lose interest, a loan officer can reject you. Mentor questions only affect your record. | Stakes where they're real, safe practice elsewhere. |
| **Win = first of: 8 profitable weeks above an MRR target, a priced round above a size target, an acquisition paying you enough.** After the first win you may keep playing. | Three genuinely different paths; SAFEs alone don't count as "a successful raise" because nothing was priced. |
| **Real files only in `~/.founders_sim/`** (profile, save, history). | "Sandboxed", but a persistent profile and persistent history have to live somewhere. |
| **`nano` is a multi-line prompt**, not a nano clone. | Editing specs needs an editor; emulating nano's UI teaches little. Real nano's keys are in `man nano`. |
| **Game files are read-only (`r--r--r--`), yours are not.** | A small, natural permissions lesson; `ls -l` shows the difference. |
| **Currency is the US dollar.** | The vocabulary (ARR multiples, SAFE, Series A) is taught in dollars everywhere. |
| **Game commands live beside bash commands and obey pipes and redirects.** | `metrics | grep -i runway` should just work; one mental model. |

**Decisions added in the second pass** (details and the problems behind them in `PLAYTEST.md`):

| Decision | Why |
|---|---|
| **An agent run does a large chunk of work** (up to 22 work points per fast agent, 34 per smart one), **compute is billed per work point** and your supervision hours scale with the size of the job. | Four identical runs per feature taught nothing after the first. Billing by work done mirrors token billing. |
| **Win targets are shown everywhere:** intro screen, a row in `status`, and a `goals` command. | In the playtest a priced round silently fell short of the "successful raise" target - a dead end the player couldn't see. |
| **`growth` explains the funnel and churn in words** (signups by channel, price vs. what it is worth, churn drivers, biggest lever). | Numbers alone didn't tell a first-time player what to do about 24% churn. |
| **A second customer segment appears mid-game** once the product fits and earns. | Weeks 15-35 were mostly `next`. The segment adds interviews, hidden needs and a market-widening decision - how real companies grow. |
| **From run 2 the idea list is shuffled and `idea` stops counting the evidence for you**; you count it with `grep -l ... \| wc -l`. | Run 1 holds your hand; later runs make reading the notes - and using the shell - the way to decide. |
| **Business buyers ask questions built from the deal** (ACV, pilot criteria, payment terms, gross margin). | The brief asks that customers, not only investors, use the vocabulary. |
| **An acquihire is never a win**, and is priced as the value of the team. | It was priced above the business and counted as a win. |
| **A real `sed`** (s///, d, p, addresses, `-i`, `-n`, `-E`) **and `spec new --from`**, with copy detection in `spec check`. | Writing every spec from scratch was the main tedium; `sed -i` is also how agents make small edits. |
| **Some entries get a "Go deeper" section** (benchmarks, common mistakes, practice), shown in the Notebook but not in the pop-up. Practice questions vary: recognise the definition, explain why it matters, spot it in your company. | "Know in depth" without turning pop-ups into walls of text. |
| **The game states its own simplifications** in `notebook/000_what_is_simplified.md`, linked from the first email. | The brief asks to state what is simplified; REVIEW.md is not something a player reads. |

## 4. Known simplifications (what is not like reality)

**Economy**
- Customers are a number (with decimals), not individuals; one blended churn rate; revenue is collected
  weekly; one price for everyone. No taxes, depreciation or VAT. No annual plans (except one event).
- "Fit" is a single score from hidden feature weights; real product-market fit is not one number.
- CAC is blended (all marketing spend / all new customers over four weeks).
- The valuation shown is a formula (story early, ARR × multiple later). Real valuations are negotiated.
- Marketplace: only the demand side is simulated; supply appears through features (vetting, tutor tools).
- Usage pricing: "price" is the average monthly bill per customer.

**Agents**
- A run finishes instantly; real agent work takes minutes to hours and you can watch it.
- Spec scoring checks structure, not meaning. A well-structured bad idea scores well.
- Bugs are counts with a type; review "finds and fixes" in one step; model tiers are just two.
- Upgrades are one-time purchases; in reality tests and memory files need continuous care.

**Funding**
- SAFEs convert at `min(cap ÷ pre-round shares, discounted round price)` — closer to the older pre-money
  SAFE. Today's standard post-money SAFE is computed slightly differently.
- The option pool is sized as a percentage of pre-round shares.
- One investor per round (no syndicates, no pro-rata participation), no legal fees, closing is instant.
  Anti-dilution, pro-rata rights and protective provisions are taught, not simulated.
- Liquidation waterfall: debt → preferences → pro-rata, with non-participating holders choosing the better
  of preference or conversion. No seniority stacks, caps on participation, or dividends.
- Vesting is tracked for hires but not for the founder. Warrants are issued as plain shares.
- Loans: fixed-rate amortization; the covenant is a single minimum-cash rule; default = game over.
- Acquisition: one buyer, a three-week diligence, all cash, no earn-out mechanics (the term is taught).

**Shell**
- Implemented: quoting, variables, `$(...)`, globs, pipes, `> >> < 2> 2>> 2>&1 &>`, `/dev/null`, `; && ||`,
  aliases, history (`!!`, `!n`), scripts with `$1..$9`, `for` and `if`, `test`/`[`, and `sed` (s, d, p).
- Not implemented: job control (`&`, `fg`), `while`/`case`/functions, here-documents, arithmetic `$((..))`,
  brace expansion, `awk`, signals. Unknown tools give a hint instead.
- `less` pages with Enter/q; `nano` is a simple editor; `date` shows the game's date; there is one user.
- stdout and stderr of a pipeline stage are collected and passed on when the stage ends (not streamed).

## 5. The curriculum, in order

### Vocabulary (191 terms)

Each term has: a plain definition, why it matters, an example filled with your company's numbers, and
related terms; 53 key terms also have a "Go deeper" section. Within a stage, terms are listed in teaching order; a term's prerequisites always come
earlier (enforced by a test). Source: `founders_sim/learn/terms.py`.

**Stage 1 — Foundations: problems, customers, money in and out** (21 terms)

Startup → Founder → Problem (customer pain) → Customer interview → Hidden need (customer insight) → Willingness to pay (WTP) → Validation → Problem/solution fit → MVP (minimum viable product) → Iteration → Pivot → Revenue → Pricing → Costs (expenses) → Profit → Cash → Burn rate → Runway → Bootstrapping → Ramen profitable → Burnout

**Stage 2 — Building with AI agents** (36 terms)

LLM (large language model) → AI agent (coding agent) → Tool use (function calling) → Agentic loop → Prompt → System prompt → Spec (specification) → Context (and context window) → RAG (retrieval-augmented generation) → Token → Compute budget → Model tier (fast vs. smart) → Task decomposition → Acceptance criteria → Hallucination → Review (code review) → Human in the loop → Bug → Automated tests → Merge (ship) → Version control (git) → Technical debt → Refactoring → Incident → Plan mode (plan before code) → Project memory file (AGENTS.md / CLAUDE.md) → Parallel agents → Coordination cost → Subagents (orchestration) → CI (continuous integration) → Regression → Evals (evaluation suite) → Fine-tuning → Guardrails (sandbox and permissions) → Prompt injection → MCP (Model Context Protocol)

**Stage 3 — Growth and unit economics** (29 terms)

Customer vs. user → Subscription (recurring revenue) → MRR (monthly recurring revenue) → ARR (annual recurring revenue) → Growth rate (MoM) → KPI and north-star metric → Churn → Retention → ARPU (average revenue per user) → COGS (cost of goods sold) → Gross margin → CAC (customer acquisition cost) → LTV (customer lifetime value) → LTV:CAC ratio → CAC payback period → Unit economics → Product-market fit (PMF) → Premature scaling → Conversion rate → A/B test (experiment) → Freemium → Funnel → Word of mouth (virality) → Cohort → Net revenue retention (NRR) → Expansion revenue → Default alive / default dead → Break-even → Fixed vs. variable costs

**Stage 4 — Go-to-market, markets and competition** (29 terms)

B2C (business-to-consumer) → B2B (business-to-business) → SaaS (software as a service) → ICP (ideal customer profile) → Market segment → TAM (total addressable market) → SAM (serviceable addressable market) → SOM (serviceable obtainable market) → Go-to-market (GTM) → Acquisition channel → Launch → Positioning → Value proposition → Competitor → Moat (defensibility) → Network effects → Switching costs → Sales cycle → Sales pipeline → ACV (annual contract value) → Enterprise sales → Champion → Pilot (proof of concept) → Procurement → Payment terms (net-30) and accounts receivable → Usage-based pricing → Marketplace → GMV (gross merchandise value) → Take rate

**Stage 5 — Fundraising and ownership** (45 terms)

Equity (shares) → Investor → Friends and family round → Angel investor → Accelerator → Venture capital (VC) → LPs and GPs (how a VC fund works) → Power law (venture returns) → Funding stages (pre-seed, seed, Series A) → Funding round → Pitch → Pitch deck → Traction → The ask (use of funds) → Warm introduction → Due diligence → Valuation → Pre-money valuation → Post-money valuation → Dilution → Cap table (capitalization table) → SAFE (simple agreement for future equity) → Valuation cap → Discount (SAFE / note) → Convertible note → Priced round → SAFE conversion → Term sheet → Lead investor → Negotiating leverage (competing offers) → Liquidation preference → Preferred vs. common stock → Participating preferred → Option pool (ESOP) → Fully diluted shares → Vesting → Cliff → Board of directors (board seat) → Pro-rata rights → Burn multiple → Down round → Anti-dilution protection → Bridge round → Demo day → Strategic investor (corporate VC)

**Stage 6 — Corporate finance, debt and exits** (31 terms)

Income statement (P&L) → EBITDA / operating profit → Depreciation and amortisation → Net income (the bottom line) → Cash flow → Balance sheet → Working capital → Deferred revenue → Debt financing → Principal → Interest and APR → Amortization (loan repayment schedule) → Collateral → Personal guarantee → Limited liability → Covenant → Debt service coverage (DSCR) → Revenue-based financing (RBF) → Venture debt → Warrant → Revenue multiple → DCF (discounted cash flow) → Exit → Acquisition (M&A) → LOI (letter of intent) → Acquihire → Liquidation waterfall → Earn-out → IPO (initial public offering) → Operating leverage → Control


### Bash (38 lessons)

Each lesson has an explanation, examples, a tip for working with coding agents, a suggested command to
try, and (for commands) a `man` page. Lessons unlock the first time you use the command successfully;
`tutor` suggests the next one in order. Source: `founders_sim/learn/bash_lessons.py`.

1. **Finding your way: pwd, ls, cd, cat** — `pwd`, `ls`, `cd`, `cat`
2. **Looking closer: ls flags, paths, less, head, tail** — `ls_flags`, `paths`, `less`, `head`, `tail`
3. **Making and moving things: mkdir, touch, cp, mv, rm** — `mkdir`, `touch`, `cp`, `mv`, `rm`, `glob`
4. **Writing text: echo and redirection** — `echo`, `quoting`, `redirect`, `redirect_append`, `stderr`
5. **Combining commands: pipes, grep, wc, sort** — `pipe`, `exit_status`, `grep`, `wc`, `sort`, `uniq`, `cut`
6. **Finding and remembering: find, history, Tab, man** — `find`, `history`, `tab`, `up_arrow`, `man`
7. **Power tools: variables, permissions, scripts** — `variables`, `chmod`, `script`, `alias`, `xargs`, `sed`

Ten **shell challenges** (emails from your mentor, answered with `answer <id> <value>`) require combining
these: counting with `ls | wc -l`, `grep -il ... | wc -l`, `cat */tests.log | grep -c FAIL`,
`find ... | wc -l`, `sort -t, -k2 -n | tail -n 1`, `sort | uniq -c`, `mv` with globs, `cp`, an environment
variable, and writing an executable script. The game checks the real state of the virtual filesystem.

## 6. How the quality bar was checked

- **70 automated tests** (`python3 -m pytest`, ~2.5 s): real-bash behaviour and error messages (including
  `sed`, stderr redirection, `/dev/null`, exit status), sandboxing, curriculum integrity (complete, ordered,
  every term reachable, every generated question well-formed), metric formulas, spec scoring and copy
  detection, agent/review/merge rules, SAFE-conversion and priced-round share math, the liquidation
  waterfall, loan amortization, acquisition diligence, acquihires, the new-segment moment, buyer questions,
  every event, tutorial missions, challenges, save/load, and whole runs on every scenario.
- **A human-style playtest of two full runs** (see `PLAYTEST.md`): run 1 guided, run 2 at difficulty 2 with
  the profile carried over. 30+ problems found and fixed; the remaining open ones are listed there.
- **Simulated players** on every scenario and difficulty (6 seeds each):

  | | expert | decent | careless |
  |---|---|---|---|
  | difficulty 1 | wins, week ~20-27 | wins, week ~26-36 | always loses |
  | difficulty 3 | wins, week ~23-29 | wins, week ~37-46 | always loses |
  | difficulty 5 | wins, week ~32-37 | mostly wins, week ~48-67 | always loses |

- **Curriculum pace:** a simulated learner playing six runs (answering ~85% correctly) mastered 22 terms
  after run 1, 83 after run 3 and 155 of 191 after run 6. The remaining terms belong to paths that bot
  never takes (loans, acquisitions); the focus system steers a human toward them.
- **The README's Linux steps were executed as written** in a fresh clone and virtual environment, on
  Python 3.10 (Ubuntu 22.04's version) and 3.13; the game and all tests pass on both.
- **A real pseudo-terminal session** exercised Tab completion (including the menu), history recall, the
  editor, arrow-key choices and the Textual dashboard.

Not verified: the Windows-side steps (WSL install, Windows Terminal) could not be run here, so they are
written from Microsoft's documented procedure and common failure modes; and the 3-5 hour estimate is
derived from week counts, not from timing a human.

## 7. Five ideas for next features

1. **A co-founder path.** Start with (or recruit) a co-founder: equity split, founder vesting, shared hours,
   and the possibility of a break-up - the most common real reason startups die that the game omits.
2. **Real agents inside the game.** Optionally send the player's spec to a real model (Claude API) for
   feedback on its *meaning*, replacing the structural scorer, so spec-writing skill is judged for real.
3. **A real git layer.** Simulate `git status/add/commit/diff/log/branch` over the virtual filesystem, with
   agents working on branches and merges that can conflict - the next terminal skill after bash (the
   `version_control` term already introduces it).
4. **Cohorts and A/B tests.** Track signup cohorts individually and let the player run a real A/B price test
   on half of new signups, with results in CSV files to analyse with `cut`, `sort` and `grep` - turning
   two of the newest terms from explanations into mechanics.
5. **Board meetings and investor updates.** After a priced round: a monthly update to write (a file the
   game scores for honesty and clarity) and quarterly board meetings where decisions can be vetoed -
   teaching governance, reporting and control.
