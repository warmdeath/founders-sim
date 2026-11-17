"""The end of a run: the ending, the debrief, and planning the next run.

The debrief is the most important teaching screen in the game: it names
what went well, what went wrong, and what an experienced founder would
have done - then updates the persistent learner profile so the NEXT run
targets what you haven't practised yet.
"""
from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from ..learn.terms import TERMS, TIERS, ORDER
from ..learn.profile import Profile
from .scenarios import scenario_of, SCENARIOS
from .session import Session, money
from . import engine

ENDINGS = {
    "profitable": ("🏆 Profitable company", True,
                   "{company} pays its own way. No investor can tell you what to do; no clock is ticking. "
                   "Most startups never get here."),
    "raised": ("🏆 Funded", True,
               "You closed a priced round. You now have fuel, a board, and people expecting a very large outcome. "
               "The real work starts here."),
    "acquired": ("🏆 Acquired", True,
                 "{company} was bought. After the waterfall you personally received {payout}."),
    "acquihired": ("🤝 Soft landing", False,
                   "{company} was sold, but after debts and investor preferences you received {payout}. "
                   "A job offer and a story - not the outcome you hoped for, and a very common one."),
    "bankrupt": ("💀 Out of cash", False,
                 "The account hit zero in week {week}. Payroll, servers and rent don't accept equity. {company} is closed."),
    "burnout": ("🔥 Burnout", False,
                "In week {week} you couldn't get out of bed. A solo founder is a single point of failure, and you failed. "
                "{company} drifts without you."),
    "timeout": ("⏳ Still standing", False,
                "{weeks} weeks in, {company} is alive but hasn't reached a win condition. "
                "Many real startups live in this in-between state for years."),
}

# topic -> (description, profile mechanics that count as "done", best scenario for it)
TOPICS = {
    "validation": ("customer interviews and choosing the right problem", ["good_validation"], "focusly"),
    "agents": ("advanced agent workflows: tests, subagents, evals", ["upgrade_subagents", "upgrade_evals"], "parsefy"),
    "fundraising": ("priced rounds, term sheets and dilution", ["raised_priced"], "tutorly"),
    "b2b": ("B2B sales cycles and enterprise deals", ["deal_won_mid", "deal_won_enterprise"], "ledgerly"),
    "debt": ("debt vs. equity: loans and revenue-based financing", ["loan_startup", "loan_term", "loan_rbf", "loan_venture"], "ledgerly"),
    "bootstrapping": ("bootstrapping to profitability without investors", ["won_profitable"], "parsefy"),
    "acquisition": ("acquisition offers, due diligence and the waterfall", ["exit_acquisition", "exit_acquihire"], "ledgerly"),
    "marketplace": ("marketplaces: GMV, take rate, network effects", ["played_tutorly"], "tutorly"),
    "margins": ("usage pricing and gross margin", ["played_parsefy"], "parsefy"),
}


def review_run(s: Session) -> tuple[list[str], list[tuple[str, str]]]:
    """(things done well, [(mistake, what a real founder would have done)])"""
    g = s.game
    m = engine.metrics(g)
    sc = scenario_of(g)
    good: list[str] = []
    bad: list[tuple[str, str]] = []
    interviews = sum(l.interviewed for l in g.leads.values())
    merged = [r for r in g.runs if r.merged]
    avg_spec = sum(r.spec_score for r in merged) / len(merged) if merged else 0

    if g.flag("picked_blind"):
        bad.append(("You chose your idea before talking to customers.",
                    "Interview 5-10 people first. An afternoon of conversations is the cheapest experiment a startup can run."))
    elif g.idea >= 0 and sc.ideas[g.idea][2] >= 0.99:
        good.append(f"You validated before building: {int(g.flag('idea_interviews'))} interviews, then picked the idea with real pain.")
        s.profile.did("good_validation")
    elif g.idea >= 0:
        bad.append((f"You built '{sc.ideas[g.idea][0]}', but most interviewees had a different problem.",
                    "Count how many people describe the pain unprompted (`idea` shows it) and follow the evidence, not your favourite."))
    if interviews >= 6:
        good.append(f"You kept talking to customers ({interviews} interviews) and uncovered hidden needs.")
    elif interviews <= 2 and g.week > 10:
        bad.append((f"Only {interviews} customer interview(s) in {g.week} weeks.",
                    "Keep interviewing after launch. Features your competitors can't guess come from those conversations."))
    if g.flag("junk_built"):
        bad.append((f"You built {int(g.flag('junk_built'))} feature(s) no customer asked for.",
                    "Build what interviews confirmed (marked 'asked for by customers' on the roadmap). Everything else is a guess that costs compute, hours and debt."))
    if merged and avg_spec >= 75:
        good.append(f"Strong specs (average {avg_spec:.0f}/100): your agents knew what 'done' meant.")
    elif merged and avg_spec < 55:
        bad.append((f"Weak specs (average {avg_spec:.0f}/100) made agents slow and buggy.",
                    "Spend the extra 20 minutes: goal, context files, 3-5 tasks, two acceptance tests, out-of-scope. It is the highest-leverage time in agentic work."))
    unrev = g.flag("merged_unreviewed")
    if merged and unrev == 0:
        good.append("You never merged unreviewed agent work.")
    elif unrev >= 2:
        bad.append((f"You merged {int(unrev)} agent runs without review; {int(g.flag('bugs_shipped'))} bugs reached customers.",
                    "Treat an agent's 'done' as a claim. Read the test log, review, and let tests/CI guard the door."))
    if g.flag("incidents") >= 3:
        bad.append((f"{int(g.flag('incidents'))} production incidents.",
                    "Install tests and CI early (`upgrade tests`, `upgrade ci`) and run `fix` when bugs pile up."))
    if g.debt > 50:
        bad.append((f"Technical debt ended at {g.debt:.0f}/100.",
                    "Pay debt continuously: good specs, tests, and a `refactor` every few features. Acquirers and future-you both inspect it."))
    if len(g.upgrades) >= 5:
        good.append(f"You built a real agent workflow ({', '.join(g.upgrades)}).")
    elif merged and len(g.upgrades) <= 1:
        bad.append(("You ran agents with almost no workflow upgrades.",
                    "Cheap habits compound: a project memory file, plan-before-code, automated tests."))
    if g.flag("agent_accidents") and not g.has("sandbox"):
        bad.append(("An agent with full access damaged production.",
                    "Sandbox agents and require approval for destructive commands from day one."))
    if g.flag("premature_scaling") or g.flag("ads_underwater"):
        bad.append(("You bought growth while churn was high or CAC exceeded LTV.",
                    "Fix retention first. Scale ads only when LTV:CAC is above ~3 and payback under a year."))
    if m["cac"] and m["ltv_cac"] >= 3:
        good.append(f"Healthy unit economics: LTV:CAC {m['ltv_cac']:.1f}.")
    if engine.live(g) and g.flag("price_changes") == 0:
        bad.append(("You never tested your price.", "Pricing is the fastest lever on revenue. Try a higher price; watch conversion and churn for two weeks."))
    if g.ended == "bankrupt":
        if g.flag("pitches") == 0 and not g.loans:
            bad.append(("You ran out of cash without ever asking anyone for money.",
                        "Watch runway weekly. At 6-9 months, start raising or cut burn - both take time to work."))
        else:
            bad.append(("You ran out of cash.", "Start fundraising with 9+ months of runway, or cut burn hard the moment a raise looks uncertain."))
        if any(l.guarantee for l in g.loans):
            bad.append(("You signed a personal guarantee - and the company failed. You still owe the bank personally.",
                        "Avoid personal guarantees unless the downside is one you can truly afford."))
    if g.ended == "burnout" or g.flag("crunches") >= 6:
        bad.append((f"You crunched {int(g.flag('crunches'))} times and ran your energy into the ground.",
                    "Pace yourself. Rest is part of the job; a company with a broken founder has no founder."))
    if g.flag("ts_expired"):
        bad.append(("You let a term sheet expire.", "Decide while the offer stands: negotiate, accept or decline - silence is the worst answer."))
    if g.flag("took_participating"):
        bad.append(("You accepted participating preferred stock.",
                    "Push for 1x non-participating - it is the market standard. Leverage comes from competing offers and runway."))
    if g.flag("lost_majority"):
        bad.append((f"You own {m['founder_pct'] * 100:.0f}% - less than half of your company.",
                    "Model dilution before each round (pool + SAFE conversion + new shares). Raise less, later, at better terms."))
    elif g.total_raised > 0 and m["founder_pct"] >= 0.6:
        good.append(f"You raised {money(g.total_raised)} and still own {m['founder_pct'] * 100:.0f}%.")
    asked = g.flag("quiz_asked")
    if asked >= 4 and g.flag("quiz_wrong") / asked <= 0.25:
        good.append("You knew your numbers and concepts when people asked.")
    elif asked >= 4 and g.flag("quiz_wrong") / asked >= 0.5:
        bad.append(("You got most questions from investors and bankers wrong.",
                    "Before any meeting: `metrics`, and learn MRR, burn, runway, churn, CAC and LTV by heart. Use `quiz` to practise."))
    if g.flag("deals_cold") >= 2:
        bad.append((f"{int(g.flag('deals_cold'))} B2B deals went cold from neglect.", "Follow up every open deal at least every couple of weeks, or qualify it out."))
    if g.flag("deals_won") >= 2:
        good.append(f"You closed {int(g.flag('deals_won'))} B2B deals.")
    if g.profitable_weeks >= 4:
        good.append("The company was default alive - revenue covered costs.")
    if not good:
        good.append("You started. Most people with an idea never do - and now you know what the first weeks feel like.")
    return good, bad


def plan_next_run(profile: Profile, scenario_just_played: str) -> tuple[list[str], str]:
    """Pick focus topics the player hasn't practised, and a scenario for them."""
    untouched = [topic for topic, (_desc, mechs, _sc) in TOPICS.items()
                 if not any(profile.mechanics.get(mech) for mech in mechs)]
    focus = untouched[:2]
    plays = profile.scenarios
    candidates = [TOPICS[t][2] for t in focus] + sorted(SCENARIOS, key=lambda k: plays.get(k, 0))
    scenario = next((c for c in candidates if c != scenario_just_played and plays.get(c, 0) == 0), None) \
        or next(c for c in candidates if c != scenario_just_played)
    return focus, scenario


def weakest_tier(profile: Profile) -> int:
    best, best_ratio = 1, 2.0
    for tier in TIERS:
        terms = [t for t in TERMS.values() if t.tier == tier]
        ratio = sum(profile.term_status(t.id) == "mastered" for t in terms) / len(terms)
        if ratio < best_ratio:
            best, best_ratio = tier, ratio
    return best


def finish_run(s: Session) -> None:
    """Show the debrief and update the persistent profile."""
    g = s.game
    p = s.profile
    m = engine.metrics(g)
    title, won, story = ENDINGS[g.ended]
    payout = money(g.flag("exit_payout"))
    story = story.format(company=g.company, week=g.week, weeks=g.week - 1, payout=payout)
    if g.ended == "timeout" and g.won_paths:
        title, won = "🏆 " + " + ".join(g.won_paths), True
        story = f"You reached {len(g.won_paths)} win condition(s) and kept building until the end."
    for path in g.won_paths:
        p.did("won_" + path)
    p.did("played_" + g.scenario)
    for up in g.upgrades:
        p.did("upgrade_" + up)
    good, bad = review_run(s)

    newly = [t for t in ORDER if p.term_status(t) == "mastered" and t not in g.mastered_start]
    seen_now = [t for t in g.notebook if not t.startswith("sh_")]
    p.runs += 1
    p.scenarios[g.scenario] = p.scenarios.get(g.scenario, 0) + 1
    focus, scenario = plan_next_run(p, g.scenario)
    p.next_focus = focus
    p.endings.append({"run": g.run_number, "scenario": g.scenario, "ending": g.ended, "weeks": g.week - 1,
                      "mrr": round(m["mrr"]), "cash": round(g.cash), "founder_pct": round(m["founder_pct"], 3),
                      "won": won})
    p.save()

    io = s.io
    io.print()
    io.print(Panel(Text(story), title=title, border_style="green" if won else "red", title_align="left"))
    io.print(Text.from_markup(
        f"[title]Final numbers[/title]  week {g.week - 1} · cash {money(g.cash)} · MRR {money(m['mrr'])} · "
        f"{m['customers']:.0f} customers · fit {m['fit']:.0f}/100 · you own {m['founder_pct'] * 100:.0f}% · "
        f"raised {money(g.total_raised)}\n"))
    body = Text()
    for line in good:
        body.append("✔ ", style="green")
        body.append(line + "\n")
    io.print(Panel(body, title="What went well", border_style="green", title_align="left"))
    body = Text()
    if not bad:
        body.append("No major mistakes detected. Next run will be harder.\n")
    for mistake, advice in bad:
        body.append("✘ ", style="red")
        body.append(mistake + "\n", style="bold")
        body.append("   A real founder would: ", style="dim")
        body.append(advice + "\n\n")
    io.print(Panel(body, title="Mistakes - and what an experienced founder would have done", border_style="red",
                   title_align="left"))
    counts = p.counts()
    body = Text()
    body.append(f"Terms met this run: {len(seen_now)}.  Newly mastered: {len(newly)}.\n")
    if newly:
        body.append("  " + ", ".join(TERMS[t].name for t in newly[:24]) + ("..." if len(newly) > 24 else "") + "\n")
    struggling = p.struggling()[:8]
    if struggling:
        body.append("Still shaky (answered wrong): " + ", ".join(TERMS[t].name for t in struggling) + "\n", style="yellow")
    body.append(f"\nCurriculum: {counts['mastered']}/{counts['terms']} terms mastered, {counts['practiced']} practiced, "
                f"{counts['seen']} only seen.  Shell: {counts['bash_mastered']}/{counts['bash']} skills mastered.\n")
    io.print(Panel(body, title="What you learned", border_style="cyan", title_align="left"))
    body = Text()
    body.append(f"Run {g.run_number + 1} will be harder: less starting cash, tougher investors, more market shocks, fewer hints.\n")
    if focus:
        body.append("It will steer you toward things you haven't done yet:\n")
        for topic in focus:
            body.append(f"  • {TOPICS[topic][0]}\n", style="bold")
    tier = weakest_tier(p)
    body.append(f"Weakest curriculum stage: {tier} - {TIERS[tier]}.\n")
    body.append(f"Suggested scenario: {SCENARIOS[scenario].company} - {SCENARIOS[scenario].tagline}.\n")
    io.print(Panel(body, title="Next run", border_style="yellow", title_align="left"))
