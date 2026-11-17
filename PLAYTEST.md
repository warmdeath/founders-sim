# PLAYTEST — second pass

Two full runs were played the way a first-time player would type them, through the real shell
(`ScriptedIO` replaying typed command lines, answering prompts, and editing specs through `nano`):

- **Run 1** — Focusly (B2C, guided tutorial, difficulty 1). Ended **profitable in week 37**
  after two SAFEs ($101k), 8 interviews, 9 shipped features.
- **Run 2** — Parsefy (usage-priced API, no tutorial, difficulty 2, profile carried over from run 1,
  focus topics "advanced agent workflows" and "priced rounds"). Ended **profitable in week 44**
  after a SAFE, a $300k priced round (73% ownership left), $90k venture debt, two hires and an
  enterprise deal.

Investor and mentor questions were answered right about 70% of the time, like a learner would.
Whole-run balance was then re-checked with the bots (`tests/helpers.py::Bot`) on every scenario
and difficulty.

Every problem found is listed below with its status. **Fixed** items have a commit and, where
the behaviour is testable, a test.

## Bugs

| # | What happened | Status |
|---|---|---|
| 1 | Production incidents fired in week 1, before any customer existed ("Incident! 0 cancelled"). | Fixed: needs a live product and 10+ customers. |
| 2 | "An agent deleted production data" happened with 0 customers, and in two consecutive weeks. | Fixed: needs 10+ customers, 12-week cooldown. |
| 3 | A viral post about the company happened before an idea was even chosen. | Fixed. |
| 4 | Bug types in review output vanished: `[logic]` was swallowed as rich markup. | Fixed (printed without markup). |
| 5 | `merge` leaked the hidden number of undiscovered bugs ("1 undiscovered problem went live"), which made review results meaningless as evidence. | Fixed: only says that unreviewed work shipped as-is. |
| 6 | The spec "evidence" check passed for any interview note, even one about a different feature. | Fixed: the note must be from someone who asked for *this* feature. |
| 7 | Usage-priced scenario: cost to serve a customer rose with the price, so raising the price could never improve gross margin. | Fixed: COGS depends on usage, not price. Test added. |
| 8 | Acquihire offers were priced around $690k — more than the business was worth — and counted as an acquisition *win*. | Fixed: priced as team value; an acquihire is a soft landing, never a win. Test added. |
| 9 | Building the caching feature (which exists to cut compute costs) was criticised in the debrief as "a feature no customer asked for". | Fixed: margin, moat, enterprise and new-segment features are excluded. |
| 10 | Runway displayed as "2187.3 months" when burn was tiny. | Fixed: "over 5 years". |
| 11 | An angel with a $20–60k cheque asked "If I invest $2,000,000 at a $1,500,000 pre-money...". | Fixed: question rounds now sell 10–25% of the company. |
| 12 | The shell challenge list said `answer c2 <your answer>` for challenges that have no answer value. | Fixed. |
| 13 | The notebook listed shell lessons by internal id (`ls_flags`, `redirect_append`). | Fixed: shows lesson titles. |

## Confusing moments

| # | What happened | Status |
|---|---|---|
| 14 | Concept panels printed *before* the command's own output, so the result of what you typed was buried under two explanations. | Fixed: panels are shown after the output. |
| 15 | Win targets were invisible. In run 2 a $300k priced round closed and nothing said it fell short of the ~$640k "successful raise" target. | Fixed: `goals` command, targets on the intro screen, a progress row in `status`, and a note when a round is below target. |
| 16 | Metrics showed churn of 24% but nothing said *why* customers left or where new ones came from. | Fixed: new `growth` command (signups by channel, price vs. what customers think it's worth, churn drivers, biggest lever). |
| 17 | Spec-creation instructions were repeated in full for every new spec. | Fixed: full instructions once, a one-line reminder afterwards. |
| 18 | The usage-priced scenario's interview notes said "I'd pay around 150 ($/month average usage bill per customer)"; the marketplace said "I'd pay around 17 (% take rate)". | Fixed: each business model has its own natural phrasing. |
| 19 | `review` and `merge` always needed a run id, and ids shift as you work — wrong ids were the most common typing error in both runs. | Fixed: with one run waiting, the id is optional; with several, the command lists them. `next` reminds you about unmerged work. |

## Dead ends and tedium

| # | What happened | Status |
|---|---|---|
| 20 | One agent run completed only ~25% of a feature, so every feature took 4 identical rounds of `agent run` / `review` / `merge`. | Fixed: a run does up to 22 (fast) or 34 (smart) work points per agent. Compute is billed by work done (like tokens), and your supervision hours scale with it too. |
| 21 | Every spec had to be written from scratch in nano. | Fixed: `spec new <key> --from <spec>` copies a structure; `spec check` detects unadapted copies (score capped at 35). A real `sed` (s///, d, p, addresses, -i, -n, -E) was added to the shell for quick edits, with its own lesson. |
| 22 | Mid-game emptiness: once the asked-for features shipped (around week 15), the rest of the run was mostly typing `next`. | Fixed: once the product fits and earns, a **new customer segment** appears (per scenario: parents and high-school students, accountants, non-developer ops teams, adult learners) with new people to interview and new needs. Building them raises willingness to pay and reach. Test added. |
| 23 | Run 2 was no harder to read than run 1: the real idea was always #1, and every interview summary said which idea the person "lit up" about. | Fixed: from run 2 the idea order is shuffled and `idea` no longer counts the evidence — you count it with `grep -l ... \| wc -l`. |
| 24 | `launch` with a half-built product silently wasted the once-every-10-weeks launch. The tutorial mission also pushed `launch` too early. | Fixed: a confirmation explains the trade-off; the mission now suggests `growth`, `content` or a small ad budget. |

## Balance

| # | What happened | Status |
|---|---|---|
| 25 | A $200/week test ad budget was criticised in the debrief as "premature scaling". | Fixed: only budgets of $300+/week with high churn count. |
| 26 | Higher difficulty barely mattered: an expert bot won around week 21–23 at levels 1, 3 and 5 alike. | Fixed: win targets scale with the run (0.6× → 1.5×), churn and CAC rise with the level. Now: expert ~20–45, mid ~25–67 depending on scenario and level; the careless bot still always loses. |
| 27 | Parsefy (and Ledgerly) won very early because a few high-paying customers reach a low MRR target. | Improved: higher targets and CAC. Parsefy is still the quickest scenario at levels 1–2. |
| 28 | Energy almost never mattered. | Improved: a fully used week now costs 7 energy (was 4.5). A player who works every hour must `rest` roughly every 6–8 weeks. |
| 29 | Angels and VCs could be charmed into a term sheet with almost no traction. | Fixed: investors with an MRR bar cap interest below the term-sheet threshold until you have at least half of it. |

## Still open (known, not fixed)

- **Mid-skill players win faster than intended at difficulty 1–2.** The bot that plays decently wins
  around weeks 25–35 there, instead of the 40–55 targeted in `CLAUDE.md`. Levels 3–5 are in range.
  Fixing this properly needs a slower early game for high-price scenarios, not more scaling.
- **Profitability is still the dominant win.** Raising a large enough priced round and selling the
  company both work (see tests) but take deliberate effort; the bots always end profitable.
- **The weekly mentor question repeats a term every three weeks until it is mastered.** This is
  spaced repetition by design, but a struggling player will see the same term many times.
