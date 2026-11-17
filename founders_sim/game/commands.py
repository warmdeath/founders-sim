"""The game's own commands (status, interview, agent, pitch, next ...).

Each is a small function `cmd_xxx(ctx)` that parses its arguments and
calls into the game modules. They are registered next to the bash
commands, so they can be piped and redirected too:

    metrics | grep -i runway
    sales > reports/pipeline.txt
"""
from __future__ import annotations

from rich.console import Group
from rich.table import Table
from rich.text import Text

from ..vfs import COMPANY, VFSError
from ..shell.interpreter import Ctx, Shell
from ..learn import notebook, missions, situations
from ..learn.terms import TERMS
from ..learn.bash_lessons import LESSONS
from .state import STAGES
from .scenarios import scenario_of
from .session import Session, money
from . import engine, agents, customers, funding, events, quiz, files


def S(ctx: Ctx) -> Session:
    return ctx.sh.session


def key_of(arg: str) -> str:
    """'investors/angel_rossi.txt' -> 'angel_rossi' (so paths and bare names both work)."""
    name = arg.rstrip("/").rpartition("/")[2]
    for ext in (".txt", ".md", ".deal"):
        if name.endswith(ext):
            name = name[:-len(ext)]
    return name


def usage(ctx: Ctx, text: str) -> int:
    ctx.err(f"usage: {text}\nTry `man {ctx.name}` for details.")
    return 2


def spark(values: list[float], width: int = 30) -> str:
    """A tiny text chart: ▁▂▃▅▇"""
    values = values[-width:]
    if not values:
        return ""
    lo, hi = min(values), max(values)
    blocks = "▁▂▃▄▅▆▇█"
    return "".join(blocks[int((v - lo) / (hi - lo) * 7) if hi > lo else 0] for v in values)


def learn_some(s: Session, terms: list[str], limit: int = 2) -> None:
    """Teach at most `limit` new terms at once - never a wall of definitions."""
    shown = 0
    for term in terms:
        if term not in s.game.notebook:
            s.learn(term)
            shown += 1
            if shown >= limit:
                break


def maybe_win(s: Session) -> None:
    """After an action that may have fulfilled a win condition."""
    g = s.game
    if not g.flags.pop("new_win", 0) or g.ended:
        return
    s.flush_learning()
    path = g.won_paths[-1]
    text = {"profitable": f"{g.company} is PROFITABLE: eight straight weeks of revenue above costs. You answer to nobody.",
            "raised": f"You closed a priced funding round for {g.company}. Professional investors bet real money on you."}[path]
    s.panel(f"[bold]{text}[/bold]\n\nThis is a win condition. You can end the run here (and see your debrief), "
            "or keep building toward another outcome.", "🏆 Victory", "green")
    if s.io.choose("What now?", ["End the run here and see my debrief", "Keep playing"]) == 0:
        g.ended = path


# ================================================================= overview
def cmd_status(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    m = engine.metrics(g)
    sc = scenario_of(g)
    t = Table.grid(padding=(0, 3))
    t.add_column(); t.add_column(); t.add_column(); t.add_column()
    energy_style = "good" if g.energy > 60 else ("warn" if g.energy > 30 else "bad")
    runway_style = "good" if m["runway"] > 9 else ("warn" if m["runway"] > 4 else "bad")
    t.add_row("Cash", f"[money]{money(g.cash)}[/money]", "Runway", f"[{runway_style}]{engine.fmt_runway(m)}[/{runway_style}]")
    t.add_row("MRR", money(m["mrr"]), "Customers", f"{m['customers']:.0f}")
    t.add_row("Hours left", f"{g.hours:g} of {g.hours_max:g}", "Energy/morale", f"[{energy_style}]{g.energy:.0f}/100[/{energy_style}]")
    t.add_row("Reputation", f"{g.reputation:.0f}/100", "You own", f"{m['founder_pct'] * 100:.1f}%")
    t.add_row("Product fit", f"{m['fit']:.0f}/100", "Quality", f"{m['quality']:.0f}/100")
    todo = []
    pending = [r.id for r in g.runs if not r.merged and not r.discarded]
    if pending:
        todo.append(f"agent runs to review/merge: {', '.join(pending)}")
    open_ts = [x.id for x in funding.open_termsheets(g)]
    if open_ts:
        todo.append(f"term sheets: {', '.join(open_ts)}")
    waiting = [e for e in g.emails if e.kind == "decision" and not e.done and e.ref != "offer"]
    if waiting:
        todo.append(f"{len(waiting)} email(s) need a `reply`")
    if funding.current_offer(g):
        todo.append("an acquisition offer is on the table (`mna`)")
    open_ch = [c for c, v in g.challenges.items() if v == "open"]
    if open_ch:
        todo.append(f"shell challenges: {', '.join(open_ch)}")
    body = Group(t, Text("\n" + ("Waiting for you: " + "; ".join(todo) if todo else "Nothing waiting. `tutor` suggests a next step."),
                         style="dim"))
    from rich.panel import Panel
    ctx.show(Panel(body, title=f"{g.company} · {sc.tagline} · week {g.week}/{g.max_weeks}", border_style="cyan",
                   title_align="left"))
    learn_some(s, ["cash", "runway", "burnout"], 1)


def metrics_rows(g) -> list[tuple[str, str, str]]:
    m = engine.metrics(g)
    sc = scenario_of(g)
    pct = lambda x: f"{x * 100:.1f}%"
    rows = [
        ("Cash", money(g.cash), "money in the bank"),
        ("Revenue / month", money(m["revenue_month"]), "what customers pay you"),
        ("Costs / month", money(m["costs_month"]), "gross burn: everything you spend"),
        ("Net burn / month", money(m["burn"]), "costs - revenue"),
        ("Runway", engine.fmt_runway(m), "cash / net burn"),
        ("Profit / month", money(m["profit_month"]), "revenue - costs"),
        ("MRR", money(m["mrr"]), "monthly recurring revenue"),
        ("ARR", money(m["arr"]), "MRR x 12"),
        ("MRR growth (MoM)", f"{m['growth'] * 100:+.1f}%", "vs. four weeks ago"),
        ("Paying customers", f"{m['customers']:.0f}", f"of {sc.som[0]:,} obtainable (SOM)"),
        ("New / churned last week", f"+{g.last_new:.0f} / -{g.last_churned:.0f}", ""),
        ("Churn (monthly)", pct(m["churn"]), "share of customers leaving per month"),
        ("ARPU", f"${m['arpu']:.2f}", "revenue per customer per month"),
        ("Gross margin", pct(m["margin"]), "(revenue - COGS) / revenue"),
        ("COGS per customer", f"${m['cogs_pc']:.2f}", "monthly cost to serve one customer"),
        ("CAC", money(m["cac"]) if m["cac"] else "n/a", "marketing spend / new customers (4 weeks)"),
        ("LTV", money(m["ltv"]), "ARPU x margin / churn"),
        ("LTV:CAC", f"{m['ltv_cac']:.1f}" if m["cac"] else "n/a", "3+ is healthy, below 1 loses money"),
        ("CAC payback", f"{m['payback']:.1f} months" if m["payback"] else "n/a", "months to earn back CAC"),
        ("Burn multiple", f"{m['burn_multiple']:.1f}" if m["burn_multiple"] else "n/a", "net burn / net new ARR"),
        ("Product-market fit", f"{m['fit']:.0f}/100", "do shipped features match real needs?"),
        ("Product quality", f"{m['quality']:.0f}/100", f"{g.prod_bugs:.0f} bugs live, debt {g.debt:.0f}/100"),
        ("Moat", f"{m['moat'] * 100:.0f}/100", "how hard you are to copy or leave"),
        ("Competitive pressure", f"{g.competitor * 100:.0f}/100", sc.competitor),
        ("Pipeline (weighted)", money(engine.pipeline_value(g)), "open B2B deals x odds, per month"),
        ("Est. valuation (pre-money)", money(m["valuation"]), f"stage: {engine.stage_name(m)}"),
        ("Founder ownership", pct(m["founder_pct"]), f"raised so far: {money(g.total_raised)}"),
        ("Loans outstanding", money(m["loan_balance"]), f"payments {money(m['loan_weekly'])}/week"),
    ]
    return rows


def cmd_metrics(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    table = Table(title=f"{g.company} - metrics, week {g.week}", title_justify="left", box=None, padding=(0, 2))
    table.add_column("metric", style="bold")
    table.add_column("value", justify="right", style="money")
    table.add_column("what it is", style="dim")
    for name, value, what in metrics_rows(g):
        table.add_row(name, value, what)
    ctx.show(table)
    if g.history and not ctx.piped:
        ctx.show(Text.from_markup(f"MRR   {spark([w.mrr for w in g.history])}  {money(g.history[-1].mrr)}\n"
                                  f"Cash  {spark([w.cash for w in g.history])}  {money(g.history[-1].cash)}\n"
                                  "[dim]Raw data: finance/metrics.csv · any term: nb <term> · full screen: dash[/dim]"))
    m = engine.metrics(g)
    order = ["revenue", "costs", "burn_rate", "runway", "profit"]
    if engine.live(g):
        order += ["customer", "subscription", "mrr", "churn", "arpu", "arr", "retention", "growth_rate", "pmf",
                  "cogs", "gross_margin", "ltv"]
    if m["cac"]:
        order += ["cac", "ltv_cac", "payback", "unit_economics"]
    if m["mrr"] > 1000:
        order += ["break_even", "default_alive", "burn_multiple", "revenue_multiple"]
    if not ctx.piped:
        learn_some(s, order, 2)


def cmd_next(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if g.hours > g.hours_max * 0.5 and g.guided and not g.flag("warned_idle"):
        g.flags["warned_idle"] = 1
        s.note(f"(You still had {g.hours:g} unused hours. Unused hours are gone for good - but resting matters too.)")
    lines = engine.advance_week(s)
    s.say("")
    for line in lines:
        s.say(line)
    m = engine.metrics(g)
    s.say(f"[title]── Week {g.week} ──[/title] {g.hours:g}h available · cash {money(g.cash)} · "
          f"runway {engine.fmt_runway(m)} · energy {g.energy:.0f}")
    if not g.ended:
        learn_some(s, ["revenue", "costs", "cash", "burn_rate", "runway", "iteration"], 1)
        situations.weekly_terms(s, 2 - min(2, s.panels_shown))
        s.flush_learning()
        if g.week >= 3 and not g.flags.get("new_win"):
            quiz.question_of_the_week(s)
    maybe_win(s)


def cmd_rest(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if not s.spend_hours(10, "resting"):
        return 1
    g.energy = min(100, g.energy + 14)
    s.good(f"You took real time off. Energy: {g.energy:.0f}/100.")
    s.learn("burnout")


def cmd_crunch(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if g.crunched:
        s.bad("You already crunched this week. There are only so many hours in a night.")
        return 1
    g.crunched = True
    g.hours += 15
    g.energy = max(0, g.energy - 12)
    g.bump("crunches")
    s.say(f"[warn]Crunch:[/warn] +15 hours this week, energy -12 (now {g.energy:.0f}). Useful rarely, ruinous as a habit.")
    s.learn("burnout")
    engine.check_endings(s)


# ================================================================ customers
def cmd_idea(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    sc = scenario_of(g)
    if ctx.args[:1] == ["pick"] and len(ctx.args) == 2 and ctx.args[1].isdigit() and 1 <= int(ctx.args[1]) <= len(sc.ideas):
        customers.pick_idea(s, int(ctx.args[1]) - 1)
        files.sync(s)
        return 0
    if ctx.args:
        return usage(ctx, "idea [pick <number>]")
    for i, (name, pitch, _) in enumerate(sc.ideas):
        votes = sum(1 for l in g.leads.values() if l.interviewed and l.likes_idea == i)
        mark = "  [good]← you are building this[/good]" if i == g.idea else ""
        ctx.show(Text.from_markup(f"{i + 1}. [bold]{name}[/bold] - {pitch}{mark}\n"
                                  f"   [dim]interviewees who really have this problem: {votes} of {customers.interviews_done(g)}[/dim]"))
    s.learn("problem")


def cmd_interview(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if not ctx.args:
        waiting = [l.key for l in g.leads.values() if not l.interviewed]
        return usage(ctx, "interview customers/leads/<name>.txt\nnot yet interviewed: " + ", ".join(waiting))
    code = 0
    for arg in ctx.args:
        key = key_of(arg)
        if key not in g.leads:
            ctx.err(f"interview: {arg}: no such lead (see `ls customers/leads`)")
            code = 1
        elif not customers.interview(s, key):
            code = 1
    files.sync(s)
    return code


def cmd_price(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    sc = scenario_of(g)
    if not ctx.args:
        ctx.line(f"{g.price:g} ({sc.price_unit})")
        return 0
    value = quiz.parse_number(ctx.args[0])
    if value is None or value <= 0:
        return usage(ctx, "price <amount>")
    customers.set_price(s, value)


def cmd_ads(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if not ctx.args:
        ctx.line(f"{g.ad_budget:g} per week")
        return 0
    value = quiz.parse_number(ctx.args[0])
    if value is None or value < 0:
        return usage(ctx, "ads <weekly budget>     (ads 0 switches them off)")
    customers.set_ads(s, value)


def cmd_content(ctx: Ctx):
    return 0 if customers.content(S(ctx)) else 1


def cmd_launch(ctx: Ctx):
    return 0 if customers.launch(S(ctx)) else 1


def cmd_outbound(ctx: Ctx):
    return 0 if customers.outbound(S(ctx)) else 1


def cmd_sales(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if ctx.args:
        key = key_of(ctx.args[0])
        if key not in g.deals:
            return ctx.fail(f"{ctx.args[0]}: no such deal (see `sales`)")
        ok = customers.work_deal(s, key)
        files.sync(s)
        return 0 if ok else 1
    if not g.deals:
        s.say("No deals yet. `outbound` (5h) goes looking for business customers.")
        return 0
    table = Table(title="Sales pipeline", title_justify="left", box=None, padding=(0, 2))
    for col in ("deal", "company", "size", "$/month", "stage", "status"):
        table.add_column(col)
    for d in g.deals.values():
        style = {"won": "green", "lost": "dim"}.get(d.status, "")
        table.add_row(d.key, d.company, d.size, money(d.mrr), STAGES[d.stage], d.status, style=style)
    ctx.show(table)
    if not ctx.piped:
        s.note("Work a deal one stage forward: sales <deal>   ·   stages: " + " → ".join(STAGES))
        learn_some(s, ["b2b", "pipeline", "sales_cycle"], 1)


# ================================================================== product
def cmd_spec(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    args = ctx.args
    if args[:1] == ["new"] and (len(args) == 2 or (len(args) == 4 and args[2] == "--from")):
        key = key_of(args[1])
        feature = g.features.get(key)
        if feature is None or not feature.known:
            known = ", ".join(f.key for f in g.features.values() if f.known and not f.shipped)
            return ctx.fail(f"'{key}' is not on the roadmap. Available: {known}")
        if g.idea < 0:
            return ctx.fail("pick an idea first (`idea pick <n>`): you can't specify a product you haven't chosen.")
        path = f"{COMPANY}/product/specs/{key}.md"
        if ctx.fs.exists(path):
            return ctx.fail(f"product/specs/{key}.md already exists. Edit it: nano product/specs/{key}.md")
        if len(args) == 4:                      # reuse the structure of a spec you already wrote
            source = ctx.fs.read(args[3], ctx.sh.cwd)
            body = source.split("\n## ", 1)[1] if "\n## " in source else ""
            ctx.fs.write(path, f"# Spec: {feature.title}\nfeature: {key}\n\n## {body}")
            s.good(f"Created product/specs/{key}.md from {args[3]}.")
            s.note("It still describes the OTHER feature. Rewrite the goal, context, tasks and tests for this one "
                   f"(`nano product/specs/{key}.md`, or `sed -i 's/old words/new words/' product/specs/{key}.md`).\n"
                   "An agent given a copied spec builds the wrong thing - `spec check` will tell you.")
            s.learn("spec")
            return 0
        ctx.fs.write(path, agents.spec_template(feature))
        s.good(f"Created product/specs/{key}.md - a template with five sections.")
        s.note("Replace each TODO line with real content: `nano product/specs/" + key + ".md`, or append lines with\n"
               "  echo '- imports a 20-page PDF in under 10 seconds' >> product/specs/" + key + ".md\n"
               "(appended lines land in the LAST section, so nano is easier). Then: spec check product/specs/" + key + ".md\n"
               "Later specs go faster: `spec new <key> --from product/specs/" + key + ".md` reuses this one's structure.")
        s.learn("spec", "prompt")
        return 0
    if args[:1] == ["check"] and len(args) == 2:
        text = ctx.fs.read(args[1], ctx.sh.cwd)
        key = agents.spec_feature(text, args[1])
        info = agents.score_spec(s, text, key)
        s.say(f"[title]Spec review: {args[1]}[/title]  feature: {key}")
        for kind, note in info["notes"]:
            s.good(note) if kind == "good" else s.bad(note)
        style = "good" if info["score"] >= 75 else ("warn" if info["score"] >= 50 else "bad")
        s.say(f"Score: [{style}]{info['score']}/100[/{style}]"
              + ("  - agents will struggle with this." if info["score"] < 50 else ""))
        g.flags["best_spec"] = max(g.flag("best_spec"), info["score"])
        learn_some(s, ["spec", "context", "task_decomposition", "acceptance_criteria"], 2)
        if info["score"] >= 80:
            s.credit("spec")
            for term, ok in (("context", info["context"]), ("task_decomposition", 2 <= info["tasks"] <= 6),
                             ("acceptance_criteria", info["tests"] >= 2)):
                if ok:
                    s.credit(term)
        return 0
    if not args:
        specs = [n.name for n in ctx.fs.listdir(f"{COMPANY}/product/specs")]
        ctx.line("\n".join(specs) if specs else "no specs yet. Start one: spec new <feature key from product/roadmap.md>")
        return 0
    return usage(ctx, "spec new <feature> [--from <existing spec>] | spec check <file>")


def find_run(ctx: Ctx, arg: str):
    key = key_of(arg)
    return next((r for r in S(ctx).game.runs if r.id == key), None)


def cmd_agent(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    args = list(ctx.args)
    sub = args.pop(0) if args else "status"
    if sub == "run":
        n_agents, model, path = 1, ctx.sh.env.get("AGENT_MODEL", "fast"), None
        while args:
            arg = args.pop(0)
            if arg in ("--agents", "-n") and args:
                value = args.pop(0)
                if not value.isdigit() or not 1 <= int(value) <= 6:
                    return ctx.fail("--agents takes a number from 1 to 6")
                n_agents = int(value)
            elif arg in ("--model", "-m") and args:
                model = args.pop(0)
            elif arg.startswith("-"):
                return usage(ctx, "agent run <spec file> [--agents N] [--model fast|smart]")
            else:
                path = arg
        if path is None:
            return usage(ctx, "agent run <spec file> [--agents N] [--model fast|smart]")
        if model not in agents.MODELS:
            return ctx.fail(f"unknown model '{model}' (choose: fast, smart; default comes from $AGENT_MODEL)")
        if not ctx.fs.is_file(path, ctx.sh.cwd):
            return ctx.fail(f"{path}: No such file. Create a spec with `spec new <feature>`")
        run = agents.start_run(s, path, n_agents, model)
        if run is None:
            return 1
        g.flags["best_spec"] = max(g.flag("best_spec"), run.spec_score)
        feature = g.features[run.feature]
        s.say(f"[title]{run.id}[/title]: {n_agents} {model} agent(s) worked on [bold]{feature.title}[/bold] "
              f"(spec score {run.spec_score}/100). Cost: {money(run.cost)} of compute, {g.flag('last_run_hours'):g}h of your time.")
        total = min(1.0, feature.progress + run.work_done)
        s.say(f"  Agent says: \"{'Feature complete' if total >= 0.999 else f'Feature {total * 100:.0f}% complete'}. "
              f"All good. Ready to merge.\"")
        if total < 0.999:
            s.note("  One agent can only do so much in one run. After merging, run the spec again to finish it - "
                   "or use a bigger model / more agents (`man agent`).")
        s.note(f"  Evidence is in agents/runs/{run.id}/ (report.md, tests.log, diff.patch). "
               f"Next: `review {run.id}` then `merge {run.id}`.")
        if run.spec_score < 50:
            s.note("  The spec was weak, so expect more bugs and less done. `spec check` shows what to add.")
        files.sync(s)
        return 0
    if sub == "discard" and args:
        run = find_run(ctx, args[0])
        if run is None or run.merged:
            return ctx.fail("no such unmerged run")
        run.discarded = True
        s.say(f"{run.id} thrown away. The compute money is gone; the lesson stays.")
        return 0
    if sub == "models":
        for name, (cost, cap, bugs, hall) in agents.MODELS.items():
            ctx.line(f"{name:<6} ${cost} per work point   up to {cap} points per agent per run   "
                     f"{bugs} bugs per 10 points   hallucination risk {hall * 100:.0f}%")
        ctx.line("Feature sizes (work points) are in product/roadmap.md. A good spec raises what a run gets done.")
        learn_some(s, ["model_tier", "compute_budget"], 1)
        return 0
    if sub == "status":
        if not g.runs:
            ctx.line("no agent runs yet. Start one: agent run product/specs/<feature>.md")
            return 0
        table = Table(title=f"Agent runs (compute spent: {money(g.compute_total)})", title_justify="left", box=None, padding=(0, 2))
        for col in ("run", "week", "feature", "agents", "spec", "done", "review", "state"):
            table.add_column(col)
        for r in g.runs:
            state = "merged" if r.merged else ("discarded" if r.discarded else "[warn]waiting[/warn]")
            table.add_row(r.id, str(r.week), r.feature, f"{r.agents}x{r.model}", str(r.spec_score),
                          f"{r.work_done * 100:.0f}%", r.review, state)
        ctx.show(table)
        return 0
    return usage(ctx, "agent run <spec> [--agents N] [--model fast|smart] | agent status | agent models | agent discard <run>")


def cmd_review(ctx: Ctx):
    s = S(ctx)
    args = [a for a in ctx.args if a != "--deep"]
    if not args:
        return usage(ctx, "review <run> [--deep]")
    run = find_run(ctx, args[0])
    if run is None:
        return ctx.fail(f"{args[0]}: no such run (see `agent status`)")
    if run.merged or run.discarded:
        return ctx.fail(f"{run.id} is already {'merged' if run.merged else 'discarded'}")
    deep = "--deep" in ctx.args
    found = agents.review_run(s, run, deep)
    if found is None:
        return 1
    if found:
        s.good(f"{'Deep' if deep else 'Quick'} review of {run.id}: found and fixed {len(found)} problem(s):")
        for bug in found:
            s.say(f"    ({bug.kind}) {bug.text}", markup=False)
    else:
        s.say(f"{'Deep' if deep else 'Quick'} review of {run.id}: found nothing.")
    s.note("  A quick review mostly catches what the tests already show. `--deep` reads the code (more hours, finds more)."
           if not deep else "  Even a deep review misses things. Tests and good specs prevent what review can't catch.")


def cmd_merge(ctx: Ctx):
    s = S(ctx)
    if not ctx.args:
        return usage(ctx, "merge <run>")
    run = find_run(ctx, ctx.args[0])
    if run is None:
        return ctx.fail(f"{ctx.args[0]}: no such run (see `agent status`)")
    if run.merged or run.discarded:
        return ctx.fail(f"{run.id} is already {'merged' if run.merged else 'discarded'}")
    if run.review == "none" and s.game.guided and not s.game.flag("warned_merge"):
        s.game.flags["warned_merge"] = 1
        if s.io.choose(f"You haven't reviewed {run.id}. Merge anyway?",
                       ["No - let me review first", "Yes, ship it unreviewed"]) == 0:
            return 1
    ok = agents.merge_run(s, run)
    files.sync(s)
    return 0 if ok else 1


def cmd_fix(ctx: Ctx):
    return 0 if agents.fix_bugs(S(ctx)) else 1


def cmd_refactor(ctx: Ctx):
    return 0 if agents.refactor(S(ctx)) else 1


def cmd_upgrade(ctx: Ctx):
    s = S(ctx)
    if not ctx.args:
        ctx.out(ctx.fs.read(f"{COMPANY}/agents/upgrades.txt"))
        return 0
    key = ctx.args[-1]
    if key not in agents.UPGRADES:
        return ctx.fail(f"unknown upgrade '{key}'. Options: {', '.join(agents.UPGRADES)}")
    return 0 if agents.buy_upgrade(s, key) else 1


# ================================================================== funding
def cmd_deck(ctx: Ctx):
    return 0 if funding.build_deck(S(ctx)) else 1


def cmd_network(ctx: Ctx):
    return 0 if funding.network(S(ctx)) else 1


def cmd_pitch(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if not ctx.args:
        return usage(ctx, "pitch investors/<name>.txt")
    key = key_of(ctx.args[0])
    inv = g.investors.get(key)
    if inv is None or not inv.known:
        return ctx.fail(f"{ctx.args[0]}: you don't know such an investor (see `ls investors`, or `network`)")
    ok = funding.pitch(s, key)
    files.sync(s)
    return 0 if ok else 1


def find_ts(g, arg: str):
    key = key_of(arg)
    return next((t for t in g.termsheets if t.id == key or t.investor == key), None)


def cmd_ts(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    args = ctx.args
    if not args:
        if not g.termsheets:
            ctx.line("no term sheets yet. They arrive after a successful `pitch`.")
        for ts in g.termsheets:
            what = (f"SAFE {money(ts.amount)} cap {money(ts.cap)}" if ts.kind == "safe"
                    else f"priced {money(ts.amount)} at {money(ts.pre_money)} pre")
            ctx.line(f"{ts.id:<28} {what:<40} {ts.status}" + (f" (expires week {ts.expires})" if ts.status == "open" else ""))
        return 0
    if len(args) != 2 or args[0] not in ("show", "negotiate", "accept", "decline"):
        return usage(ctx, "ts [show|negotiate|accept|decline] <term sheet>")
    ts = find_ts(g, args[1])
    if ts is None:
        return ctx.fail(f"{args[1]}: no such term sheet (see `ts`)")
    if args[0] == "show":
        ctx.out(funding.describe_termsheet(g, ts))
        learn_some(s, ["term_sheet"] + (["safe", "valuation_cap"] if ts.kind == "safe" else ["pre_money", "post_money", "liquidation_preference"]), 2)
        return 0
    if ts.status != "open":
        return ctx.fail(f"{ts.id} is {ts.status}")
    if args[0] == "negotiate":
        funding.negotiate(s, ts)
    elif args[0] == "accept":
        if ts.kind == "priced" and not s.game.flag("confirm_priced"):
            after = funding.founder_after(g, ts)
            if s.io.choose(f"Signing means: {money(ts.amount)} in, and your ownership goes from "
                           f"{funding.founder_pct(g) * 100:.1f}% to about {after * 100:.1f}%. Sign?", ["Sign", "Not yet"]) == 1:
                return 1
        funding.accept(s, ts)
    else:
        funding.decline(s, ts)
    files.sync(s)
    maybe_win(s)


def cmd_captable(ctx: Ctx):
    s = S(ctx)
    ctx.out(ctx.fs.read(f"{COMPANY}/finance/captable.txt"))
    if not ctx.piped:
        learn_some(s, ["equity", "cap_table"] + (["safe", "fully_diluted"] if s.game.safes else []), 2)


def cmd_waterfall(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    price = quiz.parse_number(ctx.args[0]) if ctx.args else None
    if price is None:
        return usage(ctx, "waterfall <sale price>      e.g. waterfall 3m")
    ctx.line(f"If {g.company} were sold for {money(price)}:")
    for name, amount in funding.waterfall(g, price):
        ctx.line(f"  {name:<40} {money(amount):>14}")
    if not ctx.piped:
        learn_some(s, ["exit", "waterfall", "liquidation_preference"], 2)


def cmd_loan(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if ctx.args[:1] == ["apply"] and len(ctx.args) == 2:
        key = key_of(ctx.args[1])
        if key not in g.loan_offers:
            return ctx.fail(f"{ctx.args[1]}: no such offer (see `loan`)")
        ok = funding.apply_loan(s, key)
        files.sync(s)
        return 0 if ok else 1
    if ctx.args:
        return usage(ctx, "loan | loan apply <offer>")
    ctx.out(ctx.fs.read(f"{COMPANY}/finance/loans.txt"))
    open_offers = [o for o in g.loan_offers.values() if o.status == "open"]
    ctx.line("\nOffers on the table:" if open_offers else "\nNo loan offers right now. Banks approach you once you look bankable.")
    for o in open_offers:
        ctx.line(f"  {o.key:<14} {funding.LOAN_NAMES[o.kind]:<26} {money(o.amount):>10}   cat finance/bank/{o.key}.txt")
    if not ctx.piped and (open_offers or g.loans):
        learn_some(s, ["debt", "principal", "interest"], 1)


def cmd_mna(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    sc = scenario_of(g)
    offer = funding.current_offer(g)
    sub = ctx.args[0] if ctx.args else "show"
    if sub == "explore":
        if offer:
            return ctx.fail("there is already an offer on the table")
        if not s.spend_hours(6, "corporate development talks"):
            return 1
        ok, why = funding.acquisition_interest(g)
        s.learn("acquisition")
        if not ok:
            s.say(f"You had coffee with {sc.bigcorp}'s corporate development team. {why}")
            return 0
        offer = funding.make_offer(s)
        s.good(f"{sc.bigcorp} is interested in {why} and sent a letter of intent: {money(offer.price)} ({offer.kind}).")
        return 0
    if offer is None:
        s.say(f"No acquisition offer on the table. `mna explore` (6h) sounds out {sc.bigcorp}.")
        return 0
    if sub == "show":
        ctx.line(f"{offer.buyer} offers {money(offer.price)} ({offer.kind}) - status: {offer.status}"
                 + (f", closing in week {offer.close_week}" if offer.status == "diligence" else ""))
        ctx.line("Who gets what at this price (the liquidation waterfall):")
        for name, amount in funding.waterfall(g, offer.price):
            ctx.line(f"  {name:<40} {money(amount):>14}")
        if not ctx.piped:
            learn_some(s, ["loi", "waterfall", "earnout"], 2)
        return 0
    if offer.status != "open":
        return ctx.fail("the offer is already in due diligence")
    if sub == "negotiate":
        funding.negotiate_offer(s, offer)
    elif sub == "accept":
        if s.io.choose(f"Sell {g.company} to {offer.buyer} for {money(offer.price)}? This ends the run when it closes.",
                       ["Sign the LOI", "Not yet"]) == 0:
            funding.accept_offer(s, offer)
    elif sub == "decline":
        offer.status = "dead"
        s.say(f"You turned {offer.buyer} down. Your company, your call.")
    else:
        return usage(ctx, "mna [explore|show|negotiate|accept|decline]")


def cmd_hire(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if not ctx.args:
        return usage(ctx, "hire team/candidates/<name>.txt")
    key = key_of(ctx.args[0])
    if key not in g.hires:
        return ctx.fail(f"{ctx.args[0]}: no such candidate (see `ls team/candidates`)")
    ok = funding.hire(s, key) if ctx.name == "hire" else funding.fire(s, key)
    files.sync(s)
    return 0 if ok else 1


# =========================================================== mail & learning
def cmd_inbox(ctx: Ctx):
    g = S(ctx).game
    for e in g.emails[-15:]:
        flag = "!" if e.kind == "decision" and not e.done else ("?" if e.kind == "challenge" and g.challenges.get(e.ref) == "open" else " ")
        ctx.line(f"{flag} wk{e.week:<3} {files.email_path(e):<52} {e.sender}")
    ctx.line("\n! = needs `reply <file>`   ? = open challenge   Read with: cat inbox/<file>")


def cmd_reply(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if not ctx.args:
        return usage(ctx, "reply inbox/<email file>")
    name = key_of(ctx.args[0])
    email = next((e for e in g.emails if name == key_of(files.email_path(e)) or name == f"{e.id:03d}" or name == str(e.id)), None)
    if email is None:
        return ctx.fail(f"{ctx.args[0]}: no such email")
    ok = events.reply(s, email)
    files.sync(s)
    return 0 if ok else 1


def cmd_notebook(ctx: Ctx):
    s = S(ctx)
    args = ctx.args
    if not args:
        ctx.show(notebook.notebook_overview(s))
        return 0
    query = " ".join(args[1:] if args[0] in ("search", "-s") else args)
    hits = notebook.find_entries(s, query)
    exact = [h for h in hits if h == query or h == "sh_" + query]
    if exact or len(hits) == 1:
        notebook.show_entry(s, (exact or hits)[0])
        return 0
    if not hits:
        locked = [t for t in TERMS.values() if query.lower() in t.name.lower() or query == t.id]
        if locked:
            ctx.line(f"'{locked[0].name}' is in the curriculum but you haven't met it yet in this run. "
                     "It unlocks when the situation arises.")
        else:
            ctx.line(f"nothing in your notebook matches '{query}'.")
        return 1
    for key in hits:
        name = LESSONS[key[3:]].title if key.startswith("sh_") else TERMS[key].name
        ctx.line(f"{key.replace('sh_', ''):<24} {name}")
    ctx.line("\nopen one with: nb <name>")


def cmd_glossary(ctx: Ctx):
    ctx.show(notebook.glossary(S(ctx)))


def cmd_tutor(ctx: Ctx):
    ctx.show(missions.tutor(S(ctx)))


def cmd_quiz(ctx: Ctx):
    s, g = S(ctx), S(ctx).game
    if len([t for t in g.notebook if not t.startswith("sh_")]) < 3:
        s.say("Your notebook is still nearly empty. Play a little first - the quiz uses terms you've met.")
        return 0
    if not s.spend_hours(1, "office hours with your advisor"):
        return 1
    right = quiz.office_hours(s, 3)
    g.energy = min(100, g.energy + right)
    s.note(f"{right}/3. Mastery is tracked in `glossary` - terms answered correctly twice count as mastered.")


def cmd_challenges(ctx: Ctx):
    ctx.show(missions.challenge_list(S(ctx)))


def cmd_answer(ctx: Ctx):
    if not ctx.args:
        return usage(ctx, "answer <challenge id> <your answer>")
    return 0 if missions.answer(S(ctx), ctx.args[0], " ".join(ctx.args[1:])) else 1


def cmd_help(ctx: Ctx):
    sh = ctx.sh
    if ctx.args:
        ctx.args = ctx.args[:1]
        return sh.commands["man"].fn(ctx)
    groups = [
        ("Overview", ["status", "metrics", "dash", "next", "rest", "crunch", "inbox", "reply"]),
        ("Customers", ["idea", "interview", "price", "ads", "content", "launch", "outbound", "sales"]),
        ("Product & agents", ["spec", "agent", "review", "merge", "fix", "refactor", "upgrade"]),
        ("Money & people", ["deck", "network", "pitch", "ts", "captable", "waterfall", "loan", "mna", "hire", "fire"]),
        ("Learning", ["tutor", "notebook", "glossary", "quiz", "challenges", "answer", "man", "help"]),
        ("Game", ["save", "quit"]),
    ]
    t = Table.grid(padding=(0, 2))
    t.add_column(style="bold"); t.add_column()
    for title, names in groups:
        t.add_row(f"[title]{title}[/title]", "")
        for name in names:
            if name in sh.commands:
                t.add_row(f"  [cmd]{name}[/cmd]", sh.commands[name].summary)
    ctx.show(t)
    bash = sorted({c.name for c in sh.commands.values() if c.kind == "bash" and len(c.name) > 1})
    ctx.show(Text("\nReal shell commands that work here:\n  " + " ".join(bash)
                  + "\n\nDetails for any command: man <command>   ·   What to learn next: tutor"
                    "\nAliases: st=status m=metrics nb=notebook gl=glossary cap=captable todo=tutor", style="dim"))


GAME_MAN = {
    "status": ("status - one-screen summary of the company", "status   (alias: st)",
               "Shows cash, runway, MRR, hours left this week, energy, and anything waiting for a decision."),
    "metrics": ("metrics - the founder's dashboard", "metrics   (alias: m)",
                "Every number you should know by heart before an investor meeting. Pipe it: `metrics | grep -i churn`. "
                "The weekly history is in finance/metrics.csv."),
    "next": ("next - end the week", "next   (alias: week)",
             "Lets one week pass: customers sign up and churn, revenue arrives, costs are paid, events happen. "
             "Your hours reset. Unused hours are lost."),
    "rest": ("rest - recover energy", "rest", "Costs 10 hours, restores 14 energy. Energy at 0 = burnout = game over."),
    "crunch": ("crunch - work nights", "crunch", "+15 hours this week, -12 energy. Once per week."),
    "idea": ("idea - list ideas / choose one", "idea | idea pick <number>",
             "`idea` shows the candidate ideas and how many interviewees really have each problem. "
             "`idea pick N` commits. Picking again later is a pivot (costly)."),
    "interview": ("interview - talk to a potential customer", "interview customers/leads/<name>.txt ...",
                  "Costs 3 hours. Writes notes to customers/notes/<name>.md, may reveal hidden needs (new roadmap features) "
                  "and hints at willingness to pay."),
    "price": ("price - show or set your price", "price [amount]",
              "Without argument prints the price. Price too far above willingness to pay kills signups and raises churn."),
    "ads": ("ads - weekly paid advertising budget", "ads [weekly budget]",
            "Buys customers at your current CAC. `ads 0` stops. Compare CAC with LTV in `metrics` before scaling."),
    "content": ("content - content marketing", "content",
                "5 hours. Builds an audience that keeps sending signups for weeks. Costs hours, not cash."),
    "launch": ("launch - public launch", "launch",
               "8 hours, needs a live product, at most every 10 weeks. A one-time wave of signups scaled by fit and reputation."),
    "outbound": ("outbound - prospect for business customers", "outbound",
                 "5 hours. Adds B2B deals to customers/pipeline/."),
    "sales": ("sales - the B2B pipeline", "sales | sales <deal>",
              "`sales` lists deals. `sales <deal>` spends hours to move one deal a stage forward "
              "(lead → discovery → demo → pilot → procurement → won). Bigger customers need more weeks between steps."),
    "spec": ("spec - write specifications for agents", "spec | spec new <feature> [--from <existing spec>] | spec check <file>",
             "`spec new` creates a template in product/specs/ (`--from` copies the structure of a spec you already wrote - then adapt it). Fill in the five sections (Goal, Context, Tasks, "
             "Acceptance tests, Out of scope) with nano or echo >>. `spec check` scores it 0-100 and says what is missing. "
             "Spec quality drives how much agents get done and how many bugs they create."),
    "agent": ("agent - direct your AI coding agents", "agent run <spec> [--agents N] [--model fast|smart] | agent status | agent models | agent discard <run>",
              "`agent run` starts agents on a spec: costs compute dollars and hours, writes agents/runs/<run>/. "
              "More agents = more done per run, but conflicts unless the spec has at least as many separate tasks. "
              "Default model: $AGENT_MODEL."),
    "review": ("review - check an agent run before merging", "review <run> [--deep]",
               "Quick review: 2h, catches most failures visible in tests.log. Deep review: 5h, reads the code, "
               "catches most hidden bugs and hallucinations. Found problems are fixed."),
    "merge": ("merge - ship an agent run to customers", "merge <run>",
              "Adds the run's work to the product. Undiscovered bugs go live with it and become incidents and churn."),
    "fix": ("fix - bug-fixing sweep", "fix", "4 hours + $60 compute. Removes most known production bugs."),
    "refactor": ("refactor - pay down technical debt", "refactor", "6 hours + $140 compute. Risky without tests."),
    "upgrade": ("upgrade - improve your agent workflow", "upgrade [name]",
                "Lists (no argument) or installs a workflow upgrade: planning, memory, sandbox, tests, ci, reviewer, subagents, evals."),
    "deck": ("deck - build your pitch deck", "deck", "4 hours. Writes investors/deck.md from the evidence you really have."),
    "network": ("network - meet investors", "network", "6 hours + $60. Finds new investors and warm introductions."),
    "pitch": ("pitch - pitch an investor", "pitch investors/<name>.txt",
              "5 hours. Needs a deck. The investor asks questions about your numbers and about concepts - "
              "you cannot look anything up during the meeting. Outcome: term sheet, 'keep me posted', or a pass."),
    "ts": ("ts - term sheets", "ts | ts show|negotiate|accept|decline <id>   (alias: termsheet)",
           "Term sheets live in investors/termsheets/. Negotiating works better with competing offers and long runway."),
    "captable": ("captable - who owns the company", "captable   (alias: cap)", "Prints finance/captable.txt."),
    "waterfall": ("waterfall - simulate a sale", "waterfall <price>",
                  "Shows who would receive what if the company were sold for <price>: loans, then liquidation preferences, then shares."),
    "loan": ("loan - debt financing", "loan | loan apply <offer>",
             "Lists your loans and open offers (finance/bank/). `loan apply` is a meeting with the loan officer."),
    "mna": ("mna - mergers and acquisitions", "mna [explore|show|negotiate|accept|decline]",
            "`mna explore` (6h) sounds out the big corporation. An accepted offer goes through 3 weeks of due diligence."),
    "hire": ("hire - add someone to the team", "hire team/candidates/<name>.txt", "Adds their weekly cost; may grant equity with vesting."),
    "fire": ("fire - let someone go", "fire <name>", "Stops the cost. Unvested equity returns to the company."),
    "inbox": ("inbox - list recent email", "inbox   (alias: mail)", "Lists recent emails; ! marks emails needing `reply`."),
    "reply": ("reply - answer a decision email", "reply inbox/<file>", "Opens the choices for an email that needs a decision."),
    "notebook": ("notebook - the Founder's Notebook", "notebook | notebook <term> | notebook search <text>   (alias: nb)",
                 "Everything you've been taught in this run. Entries are also files in ~/company/notebook."),
    "glossary": ("glossary - curriculum map", "glossary   (alias: gl)", "All terms by stage, coloured by mastery across all your runs."),
    "tutor": ("tutor - what to learn next", "tutor   (alias: todo)", "Suggests the next shell skill, the most urgent company issue and vocabulary to practise."),
    "quiz": ("quiz - practise vocabulary", "quiz", "1 hour of office hours with your advisor: three questions on terms you haven't mastered."),
    "challenges": ("challenges - shell puzzles", "challenges", "Lists shell challenges from your mentor."),
    "answer": ("answer - answer a shell challenge", "answer <id> <answer>", "Example: answer c1 7"),
    "help": ("help - list all commands", "help [command]", "Lists game commands by group and the real shell commands available. `help <command>` is the same as `man <command>`."),
    "dash": ("dash - full-screen dashboard", "dash", "Live company dashboard. Press q to return to the shell."),
    "save": ("save - save the game", "save", "Writes the run to ~/.founders_sim/save.json on your real disk. The game also autosaves every week."),
    "quit": ("quit - save and leave", "quit   (also: exit, Ctrl+D)", "Saves and exits. Continue later by starting the game again."),
}


def _man_text(name: str) -> str:
    title, synopsis, description = GAME_MAN[name]
    return f"NAME\n       {title}\n\nSYNOPSIS\n       {synopsis}\n\nDESCRIPTION\n       {description}"


# ----------------------------------------------------------- tab completion
def _complete_table(s: Session) -> dict:
    g = s.game
    runs = lambda: [r.id for r in g.runs if not r.merged and not r.discarded]
    return {
        "pitch": lambda: [f"investors/{i.key}.txt" for i in g.investors.values() if i.known],
        "interview": lambda: [f"customers/leads/{l.key}.txt" for l in g.leads.values() if not l.interviewed],
        "review": runs, "merge": runs,
        "sales": lambda: [d.key for d in g.deals.values() if d.status == "open"],
        "hire": lambda: [f"team/candidates/{h.key}.txt" for h in g.hires.values() if not h.active],
        "fire": lambda: [h.key for h in g.hires.values() if h.active],
        "upgrade": lambda: [u for u in agents.UPGRADES if not g.has(u)],
        "notebook": lambda: ["search"] + [k.replace("sh_", "") for k in g.notebook],
        "ts": lambda: ["show", "negotiate", "accept", "decline"] + [t.id for t in g.termsheets if t.status == "open"],
        "loan": lambda: ["apply"] + [o.key for o in g.loan_offers.values() if o.status == "open"],
        "mna": lambda: ["explore", "show", "negotiate", "accept", "decline"],
        "idea": lambda: ["pick"],
        "spec": lambda: ["new", "check"] + [f.key for f in g.features.values() if f.known and not f.shipped],
        "agent": lambda: ["run", "status", "models", "discard", "--agents", "--model", "fast", "smart"],
        "answer": lambda: [c for c, v in g.challenges.items() if v == "open"],
        "man": lambda: sorted(s.shell.manpages), "help": lambda: sorted(s.shell.manpages),
        "reply": lambda: [files.email_path(e) for e in g.emails if e.kind == "decision" and not e.done],
    }


def register_game_commands(sh: Shell, s: Session) -> None:
    from ..learn.bash_lessons import EXTRA_MAN
    sh.session = s
    table = [
        ("status", cmd_status, ("st",)), ("metrics", cmd_metrics, ("m",)), ("next", cmd_next, ("week",)),
        ("rest", cmd_rest, ()), ("crunch", cmd_crunch, ()), ("idea", cmd_idea, ("ideas",)),
        ("interview", cmd_interview, ()), ("price", cmd_price, ()), ("ads", cmd_ads, ()),
        ("content", cmd_content, ()), ("launch", cmd_launch, ()), ("outbound", cmd_outbound, ()),
        ("sales", cmd_sales, ()), ("spec", cmd_spec, ()), ("agent", cmd_agent, ("agents",)),
        ("review", cmd_review, ()), ("merge", cmd_merge, ()), ("fix", cmd_fix, ()),
        ("refactor", cmd_refactor, ()), ("upgrade", cmd_upgrade, ()), ("deck", cmd_deck, ()),
        ("network", cmd_network, ()), ("pitch", cmd_pitch, ()), ("ts", cmd_ts, ("termsheet",)),
        ("captable", cmd_captable, ("cap",)), ("waterfall", cmd_waterfall, ()), ("loan", cmd_loan, ("loans",)),
        ("mna", cmd_mna, ()), ("hire", cmd_hire, ()), ("fire", cmd_hire, ()), ("inbox", cmd_inbox, ("mail",)),
        ("reply", cmd_reply, ()), ("notebook", cmd_notebook, ("nb",)), ("glossary", cmd_glossary, ("gl",)),
        ("tutor", cmd_tutor, ("todo", "mission")), ("quiz", cmd_quiz, ()), ("challenges", cmd_challenges, ()),
        ("answer", cmd_answer, ()), ("help", cmd_help, ()),
    ]
    for name, fn, aliases in table:
        sh.register(name, fn, "game", GAME_MAN[name][0].split(" - ", 1)[1], aliases=aliases)
    sh.manpages = {name: _man_text(name) for name in GAME_MAN}
    sh.manpages.update({lesson.id: lesson.man for lesson in LESSONS.values() if lesson.man})
    sh.manpages.update(EXTRA_MAN)
    sh.manpages["sh"] = sh.manpages["source"] = sh.manpages["bash"] = LESSONS["script"].man
    sh.manpages["printenv"] = sh.manpages["env"]
    sh.manpages["export"] = LESSONS["variables"].man
    sh.manpages["unset"] = sh.manpages["export"]
    sh.manpages["more"] = sh.manpages["less"]
    sh.manpages["type"] = sh.manpages["which"]
    sh.manpages["["] = sh.manpages["test"]
    sh.entity_completers = _complete_table(s)
