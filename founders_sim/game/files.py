"""Game state -> files in the virtual filesystem.

The player explores the company with ls/cat/grep, so every interesting
piece of state is mirrored as a text file:

    ~/company/inbox/        emails
    ~/company/product/      ideas, roadmap, specs, status
    ~/company/customers/    leads, interview notes, market, sales pipeline
    ~/company/investors/    investor profiles, deck, term sheets
    ~/company/finance/      metrics.csv, P&L, cap table, bank offers, loans
    ~/company/team/         candidates, roster
    ~/company/agents/       runs (report, tests.log, diff), usage log, upgrades
    ~/company/notebook/     the Founder's Notebook

`sync()` rewrites the files that are derived from state. Files the player
creates (specs, scripts, notes) are never touched.
"""
from __future__ import annotations

from ..vfs import HOME, COMPANY
from .state import STAGES, WEEKS_PER_MONTH
from .scenarios import scenario_of, pricing_mentions, shown_ideas
from .session import Session, money, slug
from . import engine

DIRS = ["inbox", "inbox/archive", "product", "product/specs", "customers", "customers/leads", "customers/notes",
        "customers/pipeline", "investors", "investors/termsheets", "finance", "finance/bank", "team",
        "team/candidates", "agents", "agents/runs", "notebook", "reports"]

RO = 0o444   # game-generated reports are read-only: a small lesson in permissions

SIMPLIFIED = """# What this game simplifies

The concepts and formulas are real; the world around them is smaller. Know the difference.

MONEY AND CUSTOMERS
- Customers are a number, not individuals. One blended churn rate; no cohorts tracked separately.
- One price for all self-serve customers. Revenue arrives weekly. No taxes, VAT or depreciation.
- "Fit" is one score. Real product-market fit is judged from retention, usage and what customers say.
- The valuation in `metrics` is a formula. Real startup valuations are negotiated.

AGENTS
- An agent run finishes instantly; real runs take minutes to hours and you can watch and steer them.
- `spec check` scores a spec's STRUCTURE, not whether the idea in it is good.
- Bugs are counted, not real code. Review finds and fixes in one step.

FUNDING AND DEBT
- SAFEs convert at the lower of the cap price and the discounted price, measured on pre-round shares
  (close to the older pre-money SAFE; today's standard post-money SAFE is computed slightly differently).
- One investor per round, no lawyers, closing is instant. No anti-dilution, pro-rata or vetoes are simulated
  (they are explained in the notebook).
- Loans have fixed rates; the only covenant is a minimum cash balance.
- An acquisition has one buyer, three weeks of due diligence, and is paid in cash.

THE SHELL
- Real bash syntax for what is implemented. Not implemented: while/case/functions, $((arithmetic)),
  here-documents, job control (&), sed/awk beyond the basics, and real programs like git or python.
- `nano` here is a simple editor; real nano saves with Ctrl+O and exits with Ctrl+X.
"""


def w(s: Session, rel: str, text: str, mode: int = 0o644) -> None:
    s.fs.write(f"{COMPANY}/{rel}", text, mode=mode, force=True)


def setup(s: Session) -> None:
    """Create the starting directory tree for a new game."""
    g = s.game
    sc = scenario_of(g)
    fs = s.fs
    for d in DIRS:
        fs.mkdir(f"{COMPANY}/{d}", parents=True)
    fs.write(f"{HOME}/.bashrc", "# ~/.bashrc: read by bash at startup. Real shells load aliases from here.\n"
             "alias ll='ls -l'\nalias la='ls -la'\nexport EDITOR=nano\nexport AGENT_MODEL=fast\n")
    fs.write(f"{HOME}/README.txt",
             f"Welcome, founder.\n\nEverything about {g.company} lives in ~/company as files and folders.\n"
             "Look around with: pwd, ls, cd, cat.  Stuck? Type: tutor   (or: help)\n")
    fs.write(f"{COMPANY}/.env", "# Hidden config file (names starting with . are hidden; see them with ls -a)\n"
             "AGENT_MODEL=fast\nCOMPANY_NAME=" + g.company + "\n# Never put real API keys in files you share!\n")
    ideas = "\n".join(f"{n}. {name}\n   {pitch}\n" for n, (_, (name, pitch, _pain)) in enumerate(shown_ideas(g), 1))
    w(s, "product/ideas.md",
      f"# Ideas for {g.company}\n\nThree problems you could go after. You don't know yet which one is real.\n\n{ideas}\n"
      "Interview customers (see customers/leads) to find out which problem people actually have,\n"
      "then commit with:  idea pick <number>\n")
    w(s, "customers/market.md",
      f"# Market size for {g.company}\n\n"
      f"TAM (total addressable market):       {sc.tam[0]:>12,} potential customers   {money(sc.tam[1])} per year\n"
      f"SAM (serviceable addressable market): {sc.sam[0]:>12,} potential customers   {money(sc.sam[1])} per year\n"
      f"SOM (serviceable obtainable market):  {sc.som[0]:>12,} potential customers   {money(sc.som[1])} per year\n\n"
      f"Main competitor: {sc.competitor}\nLarge corporation in this space: {sc.bigcorp}\n\n"
      "TAM = everyone who could ever buy. SAM = those your product can serve. SOM = what you can realistically win soon.\n"
      "Investors WILL ask you for these numbers.\n")
    for lead in g.leads.values():
        write_lead(s, lead)
    for person in g.hires.values():
        equity = f"{person.equity * 100:.1f}% equity" if person.equity else "no equity"
        w(s, f"team/candidates/{person.key}.txt",
          f"Name: {person.name}\nRole: {person.role}\nCost: {money(person.weekly_cost)} per week\nEquity: {equity}\n\n"
          f"{person.blurb}\n\nTo hire:  hire team/candidates/{person.key}.txt\n")
    w(s, "notebook/000_what_is_simplified.md", SIMPLIFIED, RO)
    w(s, "reports/README.txt", "A place for your own scripts and reports. Nothing here is managed by the game.\n")
    s.mail("Nora (your mentor)", "Welcome - read me first",
           f"Hi! I'm Nora. I've started three companies (one worked). I'll check in by email.\n\n"
           f"{sc.intro}\n\n"
           f"You have {money(g.cash)} and about 50 working hours a week. Every week you choose what to spend them on,\n"
           "then type `next` to let the week pass.\n\n"
           "My advice for the first weeks:\n"
           "  1. Read product/ideas.md\n"
           "  2. Talk to customers BEFORE building:  ls customers/leads\n"
           "  3. Only then pick an idea, write a spec, and put your AI agents to work.\n\n"
           "Type `tutor` whenever you want to know what to learn next. Type `status` to see how you're doing,\n"
           "and `goals` to see what winning means this time.\n\n"
           "One more thing: this is a simulation. What it simplifies is listed in notebook/000_what_is_simplified.md\n\n- Nora\n")
    sync(s)


# ------------------------------------------------------------- single files
def write_lead(s: Session, lead) -> None:
    w(s, f"customers/leads/{lead.key}.txt",
      f"Name: {lead.name}\nWho:  {lead.role}\nStatus: not interviewed yet\n\n"
      f"To talk to them:  interview customers/leads/{lead.key}.txt   (3 hours)\n")


def write_email(s: Session, email) -> None:
    body = (f"From:    {email.sender}\nSubject: {email.subject}\nDate:    week {email.week}\n\n{email.body}")
    w(s, f"inbox/{email.id:03d}_{slug(email.subject)}.txt", body)


def email_path(email) -> str:
    return f"inbox/{email.id:03d}_{slug(email.subject)}.txt"


def write_note(s: Session, lead, discovered) -> None:
    g = s.game
    sc = scenario_of(g)
    lines = [f"# Interview: {lead.name}", f"{lead.role} - week {g.week}", "", "## What they said"]
    for key in lead.reveals:
        feature = g.features[key]
        lines.append(f"- \"{feature.quote}\"")
        lines.append(f"  (about: {feature.title})")
    idea = sc.ideas[lead.likes_idea]
    lines += ["", "## Which problem is real for them",
              f"- Described the problem behind '{idea[0]}' without being asked, with a recent example.",
              "- Shrugged at the other ideas ('sure, maybe')."]
    lines += ["", "## Money"]
    if lead.key in pricing_mentions(g.scenario):
        if sc.model == "marketplace":
            lines.append(f"- On pricing: \"The platform keeping about {lead.wtp:g}% of each lesson would be fair - "
                         "more than that and we'd arrange it between ourselves.\"")
        elif sc.model == "usage":
            lines.append(f"- On pricing: \"For our volume I'd expect a bill of around ${lead.wtp:g} a month - if it really worked.\"")
        else:
            lines.append(f"- On pricing: \"I'd pay around ${lead.wtp:g} a month if it really worked.\"")
        lines.append("- Already pays for something similar or loses real money/time to the problem.")
    else:
        lines.append("- Didn't want to name a number. Not a buyer yet - or you asked too early.")
    if discovered:
        lines += ["", "## New for the roadmap"] + [f"- {f.title} (key: {f.key})" for f in discovered]
    lines += ["", "## Interview tip",
              "Good questions ask about the past: 'When did this last happen? What did you do?'",
              "Weak questions ask for opinions: 'Would you use this?' People are polite and say yes."]
    w(s, f"customers/notes/{lead.key}.md", "\n".join(lines) + "\n")
    w(s, f"customers/leads/{lead.key}.txt",
      f"Name: {lead.name}\nWho:  {lead.role}\nStatus: interviewed in week {g.week} - notes in customers/notes/{lead.key}.md\n")


def write_run(s: Session, run, info: dict) -> None:
    """Create agents/runs/<id>/ with report, test log and diff summary.
    The files tell the truth to anyone who actually reads them."""
    g = s.game
    feature = g.features[run.feature]
    base = f"agents/runs/{run.id}"
    s.fs.mkdir(f"{COMPANY}/{base}", parents=True)
    n_tests = 6 + 2 * max(1, info["tasks"]) + (10 if g.has("tests") else 0)
    failing = [b for b in run.bugs if b.visible_in_tests]
    log = [f"$ run-tests --feature {run.feature}", f"collected {n_tests} tests", ""]
    for i in range(1, n_tests + 1):
        if i <= len(failing):
            bug = failing[i - 1]
            log.append(f"FAIL test_{run.feature}_{i:02d} - {bug.text}")
        else:
            log.append(f"PASS test_{run.feature}_{i:02d}")
    log += ["", f"{n_tests - len(failing)} passed, {len(failing)} failed"]
    w(s, f"{base}/tests.log", "\n".join(log) + "\n")
    halluc = [b for b in run.bugs if b.kind == "hallucination"]
    claim = "All tests pass." if not failing or g.rng.random() < 0.5 else f"{len(failing)} test(s) need attention."
    report = [f"# Agent report: {run.id}", f"Feature: {feature.title} ({run.feature})",
              f"Spec: {run.spec_path} (spec score {run.spec_score}/100)",
              f"Agents: {run.agents} x {run.model} model | compute cost: {money(run.cost)} | week {run.week}", "",
              "## Summary (written by the agent - a claim, not a fact)",
              f"Implemented {run.work_done * feature.complexity:.0f} of {feature.complexity} work points "
              f"({run.work_done * 100:.0f}% of the feature). {claim} Ready to merge.", ""]
    if halluc:
        report += ["## Notes", "- Integrated with the official SDK using `client.auto_sync_all()` for reliability.",
                   "- Edge cases are fully handled.", ""]
    else:
        report += ["## Notes", "- Followed the tasks listed in the spec.", ""]
    report += ["## How to check this yourself", f"  grep -c FAIL {base}/tests.log", f"  cat {base}/diff.patch",
               f"  review {run.id}        (finds and fixes problems before you merge)",
               f"  merge {run.id}         (ships it - with whatever is still wrong)"]
    w(s, f"{base}/report.md", "\n".join(report) + "\n")
    files_changed = 2 + int(run.work_done * feature.complexity / 4)
    diff = [f" {files_changed} files changed, {int(run.work_done * feature.complexity * 23)} insertions(+), "
            f"{int(run.work_done * feature.complexity * 4)} deletions(-)", ""]
    diff += [f" src/{run.feature}/{name}.py | {10 + 7 * i} +++" for i, name in
             enumerate(["core", "api", "models", "utils", "views", "sync"][:files_changed])]
    if any(b.kind == "conflict" for b in run.bugs):
        diff.append(" WARNING: overlapping edits by different agents in src/" + run.feature + "/core.py")
    if halluc:
        diff.append(" note: `client.auto_sync_all` is not defined anywhere in the SDK or this codebase")
    w(s, f"{base}/diff.patch", "\n".join(diff) + "\n")
    if g.has("planning"):
        tasks = info["sections"].get("Tasks", []) or ["(no tasks in spec - the agent made up its own plan)"]
        w(s, f"{base}/plan.md", f"# Plan for {feature.title}\n\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(tasks, 1))
          + "\n\nApproved by: you\n")
    with_log = s.fs.read(f"{COMPANY}/agents/usage.log") if s.fs.exists(f"{COMPANY}/agents/usage.log") else ""
    w(s, "agents/usage.log", with_log + f"week={run.week} run={run.id} model={run.model} agents={run.agents} cost={run.cost:.0f}\n")


def write_run_review(s: Session, run, found) -> None:
    base = f"agents/runs/{run.id}"
    lines = [f"# Review of {run.id} ({run.review})", ""]
    lines += [f"- FIXED [{b.kind}] {b.text}" for b in found] or ["- nothing found this time"]
    lines += ["", "A review that finds nothing does not prove there is nothing."]
    old = s.fs.read(f"{COMPANY}/{base}/review.md") if s.fs.exists(f"{COMPANY}/{base}/review.md") else ""
    w(s, f"{base}/review.md", old + "\n".join(lines) + "\n\n")
    lines = s.fs.read(f"{COMPANY}/{base}/tests.log").split("\n")
    for bug in found:                         # a fixed bug's test now passes
        for i, line in enumerate(lines):
            if bug.visible_in_tests and line.startswith("FAIL ") and line.endswith(" - " + bug.text):
                lines[i] = "PASS " + line[5:].split(" - ")[0]
                break
    tests = [line for line in lines if line.startswith(("PASS test_", "FAIL test_"))]
    failed = sum(line.startswith("FAIL") for line in tests)
    head = [line for line in lines if not line.endswith(" failed") and line.strip()]
    w(s, f"{base}/tests.log", "\n".join(head[:2] + [""] + tests) + f"\n\n{len(tests) - failed} passed, {failed} failed\n")


def write_termsheet(s: Session, ts) -> None:
    from . import funding
    w(s, f"investors/termsheets/{ts.id}.txt", funding.describe_termsheet(s.game, ts))


def write_deck(s: Session, sections, score: float) -> None:
    g = s.game
    lines = [f"# {g.company} - pitch deck", f"built in week {g.week} | overall strength {score * 100:.0f}%", ""]
    for i, (title, grade, text) in enumerate(sections, 1):
        mark = {1.0: "STRONG", 0.5: "OK", 0.0: "WEAK"}[grade]
        lines += [f"## Slide {i}: {title}   [{mark}]", text, ""]
    lines += ["A deck can't be stronger than the evidence behind it. Rebuild it (`deck`) after real progress."]
    w(s, "investors/deck.md", "\n".join(lines) + "\n")


# ------------------------------------------------------------ derived files
def sync(s: Session) -> None:
    """Rewrite every file that mirrors game state."""
    g = s.game
    sc = scenario_of(g)
    fs = s.fs
    fs.clock = g.week
    for d in DIRS:                                   # heal the tree if the player rm -rf'd something
        fs.mkdir(f"{COMPANY}/{d}", parents=True)
    m = engine.metrics(g)

    # product
    rows = ["# Roadmap", "", "Features you could build. Which ones customers REALLY need is not written here -",
            "you learn that from interviews (customers/notes).", "",
            f"{'key':<20}{'feature':<36}{'size':>5}  status", "-" * 78]
    for f in g.features.values():
        if not f.known:
            continue
        if f.shipped:
            status = f"LIVE (quality {f.quality * 100:.0f}%)"
        elif f.progress > 0:
            status = f"{f.progress * 100:.0f}% built"
        else:
            who = "your new segment" if f.kind == "expansion" else "customers"
            status = "idea" + (f" - asked for by {who}" if f.revealed else "")
        rows.append(f"{f.key:<20}{f.title:<36}{f.complexity:>5}  {status}")
    rows += ["", "Start one with:  spec new <key>"]
    w(s, "product/roadmap.md", "\n".join(rows) + "\n", RO)
    idea = sc.ideas[g.idea][0] if g.idea >= 0 else "not chosen yet (see product/ideas.md)"
    w(s, "product/status.md",
      f"# Product status - week {g.week}\n\nIdea:            {idea}\n"
      f"Live features:   {', '.join(f.title for f in g.features.values() if f.shipped) or 'none'}\n"
      f"Fit score:       {m['fit']:.0f}/100   (do shipped features match real needs?)\n"
      f"Quality:         {m['quality']:.0f}/100\n"
      f"Production bugs: {g.prod_bugs:.0f}\n"
      f"Technical debt:  {g.debt:.0f}/100\n"
      f"Moat:            {m['moat'] * 100:.0f}/100\n"
      f"Agent upgrades:  {', '.join(g.upgrades) or 'none'}\n", RO)

    # customers: pipeline
    for deal in g.deals.values():
        need = g.features[deal.needs].title if deal.needs else "none"
        w(s, f"customers/pipeline/{deal.key}.deal",
          f"Company: {deal.company}\nSize: {deal.size}\nValue: {deal.mrr:.0f} per month (ACV {deal.mrr * 12:.0f})\n"
          f"Stage: {STAGES[deal.stage]}\nStatus: {deal.status}\nIn this stage since: week {deal.stage_week}\n"
          f"Champion: your contact inside {deal.company}\nEconomic buyer: controls the budget - signs at procurement\n"
          f"Hard requirement: {need if STAGES[deal.stage] in ('procurement', 'won') or deal.size != 'enterprise' else 'unknown until procurement'}\n\n"
          f"Stages: {' -> '.join(STAGES)}\nWork it:  sales {deal.key}\n", RO)

    # investors
    for inv in g.investors.values():
        if not inv.known:
            continue
        kind = {"angel": "Angel investor", "accelerator": "Accelerator", "vc": "Venture capital fund",
                "corporate": "Corporate venture arm (strategic investor)"}[inv.kind]
        w(s, f"investors/{inv.key}.txt",
          f"Name: {inv.name}\nType: {inv.kind}\nWho: {kind} - {inv.firm}\n"
          f"Typical check: {money(inv.check_min)} - {money(inv.check_max)}\n"
          f"Wants to see: {'at least ' + money(inv.min_mrr) + ' MRR' if inv.min_mrr else 'a founder who learns fast; revenue not required'}\n"
          f"Cares most about: {inv.cares}\n"
          f"Instrument: {'SAFE' if inv.kind in ('angel', 'accelerator') else 'priced round (preferred shares)'}\n"
          f"Relationship: {'warm introduction' if inv.warm else 'cold (no introduction yet)'}\n"
          f"Status: {inv.status}\n\nTo pitch:  pitch investors/{inv.key}.txt\n", RO)
    for ts in g.termsheets:
        if ts.status == "open":
            write_termsheet(s, ts)
        else:
            path = f"{COMPANY}/investors/termsheets/{ts.id}.txt"
            if fs.exists(path) and "STATUS:" not in fs.read(path):
                fs.write(path, f"STATUS: {ts.status.upper()}\n\n" + fs.read(path), force=True)

    # finance
    header = "week,cash,mrr,customers,new,churned,revenue,costs,ad_spend,cogs,fit,quality,reputation,energy"
    rows = [header] + [",".join(f"{getattr(wk, col):g}" for col in header.split(",")) for wk in g.history]
    w(s, "finance/metrics.csv", "\n".join(rows) + "\n", RO)
    costs = engine.weekly_costs(g)
    Wm = WEEKS_PER_MONTH
    interest = sum(engine.loan_payment(g, l)[1] for l in g.loans) * Wm
    compute = g.compute_total / max(1, g.week - 1) * Wm if g.week > 1 else 0
    opex = (costs["living"] + costs["infra"] + costs["ads"] + costs["team"]) * Wm + compute
    gross = m["mrr"] - m["cogs_month"]
    w(s, "finance/pnl.txt",
      f"{g.company} - income statement (P&L), monthly run-rate, week {g.week}\n" + "=" * 60 + "\n"
      f"Revenue (MRR)                         {money(m['mrr']):>14}\n"
      f"- COGS (cost of serving customers)    {money(m['cogs_month']):>14}\n"
      f"= Gross profit                        {money(gross):>14}   (gross margin {m['margin'] * 100:.0f}%)\n\n"
      f"- Founder living costs                {money(costs['living'] * Wm):>14}\n"
      f"- Infrastructure and tools            {money(costs['infra'] * Wm):>14}\n"
      f"- Marketing (ads)                     {money(costs['ads'] * Wm):>14}\n"
      f"- Team                                {money(costs['team'] * Wm):>14}\n"
      f"- Agent compute (average)             {money(compute):>14}\n"
      f"= Operating profit (EBITDA)           {money(gross - opex):>14}\n\n"
      f"- Loan interest                       {money(interest):>14}\n"
      f"= Net income                          {money(gross - opex - interest):>14}\n\n"
      f"Cash in bank: {money(g.cash)}   Net burn: {money(m['burn'])}/month   Runway: {engine.fmt_runway(m)}\n"
      "(Simplified: no taxes or depreciation. Loan principal repayments reduce cash but are not an expense.)\n", RO)
    from . import funding
    total = funding.total_shares(g)
    cap = [f"{g.company} - cap table, week {g.week}", "=" * 70,
           f"{'holder':<38}{'shares':>12}{'%':>8}{'invested':>12}", "-" * 70]
    for h in g.holders:
        cap.append(f"{h.name:<38}{h.shares:>12,.0f}{h.shares / total * 100:>7.1f}%{money(h.invested) if h.invested else '':>12}")
    cap += ["-" * 70, f"{'TOTAL':<38}{total:>12,.0f}{100:>7.1f}%"]
    if g.safes:
        cap += ["", "Outstanding SAFEs (not shares yet - they convert at the next priced round):"]
        cap += [f"  {x.investor}: {money(x.amount)}, cap {money(x.cap)}, discount {x.discount * 100:.0f}%  "
                f"(~{x.amount / x.cap * 100:.1f}% if converted at the cap)" for x in g.safes]
    w(s, "finance/captable.txt", "\n".join(cap) + "\n", RO)
    for offer in g.loan_offers.values():
        text = funding.describe_loan(offer)
        if offer.status != "open":
            text = f"STATUS: {offer.status.upper()}\n\n" + text
        w(s, f"finance/bank/{offer.key}.txt", text, RO)
    loans = [f"Loans - week {g.week}", "=" * 40]
    for loan in g.loans:
        pay, interest_part = engine.loan_payment(g, loan)
        loans.append(f"{loan.lender} ({funding.LOAN_NAMES[loan.kind]}): balance {money(loan.balance)}, "
                     f"this week's payment {money(pay)} (interest {money(interest_part)})"
                     + (", PERSONAL GUARANTEE" if loan.guarantee else ""))
    w(s, "finance/loans.txt", "\n".join(loans if g.loans else loans + ["No loans."]) + "\n", RO)

    # team
    roster = [f"Team - week {g.week}", "You (founder, CEO, everything else)"]
    for person in g.hires.values():
        if person.active:
            roster.append(f"{person.name} - {person.role} - {money(person.weekly_cost)}/week - since week {person.hired_week}")
    w(s, "team/roster.txt", "\n".join(roster) + "\n", RO)

    # agents
    from .agents import UPGRADES
    ups = ["Agent workflow upgrades", "=" * 40]
    for key, (title, hours, cash, requires, _term, what) in UPGRADES.items():
        state = "INSTALLED" if g.has(key) else f"{hours}h" + (f" + {money(cash)}" if cash else "")
        ups.append(f"{key:<10} {title:<34} {state:<12} {('needs ' + requires) if requires and not g.has(key) else ''}")
        ups.append(f"           {what}")
    ups += ["", "Install with:  upgrade <name>"]
    w(s, "agents/upgrades.txt", "\n".join(ups) + "\n", RO)
    if g.has("memory"):
        w(s, "agents/AGENTS.md",
          f"# AGENTS.md - project memory for {g.company}\n\nAgents read this file at the start of every session.\n\n"
          f"## What we build\n{sc.ideas[g.idea][1] if g.idea >= 0 else 'TBD'}\n\n"
          "## Conventions\n- Small changes, one task at a time.\n- Run the tests before reporting done.\n"
          "- Never claim something works without running it.\n- Ask before deleting anything.\n\n"
          "## Where things are\n- Customer evidence: customers/notes/\n- Specs: product/specs/\n")
