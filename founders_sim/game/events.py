"""The world around the startup: competitors, market shocks, lucky
breaks, and emails that need a decision.

Each week there is a chance (higher on later runs) that one event fires.
Events arrive as emails in ~/company/inbox so the player practises
reading files; decision emails are answered with `reply <email>`.
"""
from __future__ import annotations

from .scenarios import scenario_of, level_params
from .session import Session, money
from . import engine


# ------------------------------------------------------------------ helpers
def _news(s: Session, subject: str, body: str) -> None:
    s.mail("Startup Daily (newsletter)", subject, body + "\n")


# ------------------------------------------------------------------- events
# Each event: (id, is_bad, condition(g) -> bool, fire(s) -> report line)
def competitor_launch(s):
    g, sc = s.game, scenario_of(s.game)
    hit = 0.22 * (1 - 0.7 * engine.moat(g))
    g.competitor = min(1, g.competitor + hit)
    _news(s, f"{sc.competitor} launches rival product",
          f"{sc.competitor} just launched a product aimed squarely at {g.company}'s customers, with a big ad campaign.\n"
          "Expect ads to get more expensive and some customers to be tempted away.\n"
          "Companies with a moat (network effects, integrations, switching costs) barely notice launches like this.")
    s.learn("competitor", "moat")
    return f"[warn]{sc.competitor} launched a competing product.[/warn] Competitive pressure is up (see inbox)."


def api_price_hike(s):
    g = s.game
    g.cogs_mult *= 1.25
    _news(s, "AI model provider raises prices 25%",
          "The model provider your product runs on raised prices. Your cost to serve each customer (COGS) just rose 25%.\n"
          "Check your gross margin with `metrics`. Options: raise your price, or engineer the cost down.")
    s.learn("cogs", "gross_margin")
    return "[warn]Your AI provider raised prices:[/warn] COGS per customer +25%. Check your gross margin."


def bigcorp_bundle(s):
    g, sc = s.game, scenario_of(s.game)
    g.competitor = min(1, g.competitor + 0.3 * (1 - 0.7 * engine.moat(g)))
    _news(s, f"{sc.bigcorp} bundles a free '{g.company}-like' feature",
          f"{sc.bigcorp} announced a free feature that overlaps with your product, bundled into software millions already use.\n"
          "This is the 'why won't a big company just build it?' question becoming real.\n"
          "Big companies build the generic 80%. Startups survive on the specific 20% they understand better: hidden needs.")
    s.learn("moat", "switching_costs")
    return f"[bad]{sc.bigcorp} bundled a free competing feature.[/bad] Your moat is being tested."


def downturn(s):
    g = s.game
    g.sentiment = 0.7
    g.flags["downturn"] = 1
    _news(s, "Funding winter: VC investment falls sharply",
          "Interest rates are up and investors have turned cautious. Valuations are down about 30%, rounds take longer,\n"
          "and investors now ask about profitability before growth. Companies that are default alive can wait it out.")
    s.learn("default_alive", "down_round")
    return "[bad]Market shock:[/bad] a funding downturn. Valuations are ~30% lower and investors are pickier."


def agent_accident(s):
    g = s.game
    if g.has("sandbox"):
        s.mail("Agent supervisor log", "Blocked: destructive command",
               "An agent attempted `DROP TABLE users` on what it believed was a test database. It was production.\n"
               "Your sandbox rules blocked the command and asked for approval. Nothing happened.\n")
        s.credit("guardrails")
        return "[good]Your sandbox blocked an agent from wiping production data.[/good] Guardrails just paid for themselves."
    lost = g.customers * 0.09
    g.customers -= lost
    g.energy = max(1, g.energy - 8)
    g.reputation = max(0, g.reputation - 3)
    s.mail("Agent supervisor log", "INCIDENT: production data deleted",
           "An agent 'cleaning up test data' ran a destructive command against production. It had full access.\n"
           f"You restored a backup from last night; a day of customer data is gone. {lost:.0f} customers cancelled.\n"
           "Real-world lesson: agents need guardrails - sandboxes, permission prompts for destructive commands,\n"
           "no production credentials. See `upgrade sandbox`.\n")
    s.learn("guardrails", "incident")
    g.bump("agent_accidents")
    return "[bad]An agent deleted production data.[/bad] Customers lost; a painful weekend. (`upgrade sandbox` prevents this.)"


def security_scare(s):
    g = s.game
    g.customers *= 0.94
    g.reputation = max(0, g.reputation - 5)
    g.prod_bugs += 1
    s.mail("security@researcher.example", "Vulnerability in your product",
           "I found a way to read other users' data in your app. I'm disclosing responsibly; fix it this week.\n"
           "(This is what technical debt looks like from the outside.)\n")
    s.learn("tech_debt")
    return "[bad]A security hole was reported[/bad] - a symptom of your technical debt. Reputation and customers took a hit."


def surprise_bill(s):
    g = s.game
    g.cash -= 900
    s.mail("Studio Commercialista", "Invoice: annual filings and taxes",
           "Please find our invoice for $900: company filings, bookkeeping and tax prepayments.\n"
           "(Companies have fixed costs that don't care about your revenue.)\n")
    s.learn("fixed_variable_costs")
    return "An accountant's bill for $900 arrived and was paid. Fixed costs don't wait for revenue."


def viral_post(s):
    g = s.game
    g.audience += 350
    bump = 0
    if engine.live(g):
        bump = 20 * (0.3 + engine.fit(g) / 60) * scenario_of(g).organic / 4
        g.customers += bump
    g.reputation = min(100, g.reputation + 3)
    _news(s, f"{g.company} mentioned in a viral thread", "Someone with a big following praised what you're building.\n")
    s.learn("virality")
    return f"[good]A post about {g.company} went viral.[/good] Audience +350" + (f", {bump:.0f} new customers." if bump else ".")


def press(s):
    g = s.game
    g.reputation = min(100, g.reputation + 5)
    _news(s, f"Profile: the 18-year-old behind {g.company}", "A local tech blog ran a story on you. Reputation +5.\n")
    return "[good]Press coverage.[/good] Reputation +5."


def inbound_investor(s):
    from . import files
    g = s.game
    hidden = [i for i in g.investors.values() if not i.known and (i.kind != "corporate" or g.level >= 2)]
    if not hidden:
        return ""
    inv = hidden[0]
    inv.known, inv.warm = True, True
    s.mail(inv.name, "Loved what I'm seeing - coffee?",
           f"I've been following {g.company}'s growth. I'd like to hear your pitch.\nMy profile: investors/{inv.key}.txt\n")
    files.sync(s)
    s.learn("traction")
    return f"[good]Inbound interest:[/good] {inv.name} wants to hear your pitch (investors/{inv.key}.txt). Growth attracts investors."


def feature_request(s):
    from . import files
    g = s.game
    hidden = [f for f in g.features.values() if not f.revealed and f.weight >= 0.08]
    if not hidden:
        return ""
    feature = hidden[0]
    feature.known = feature.revealed = True
    s.mail("a customer", f"Would love: {feature.title.lower()}",
           f"Hi! I use {g.company} every week. One thing: \"{feature.quote}\".\nAny chance?\n")
    files.sync(s)
    s.learn("hidden_need")
    return f"A customer email revealed a need: [bold]{feature.title}[/bold] (added to the roadmap). Customers keep teaching you after launch."


def inbound_lead(s):
    from . import files
    from .state import Deal
    g, sc = s.game, scenario_of(s.game)
    for key, company, size, value, needs in sc.deals:
        if key not in g.deals and size != "enterprise":
            g.deals[key] = Deal(key, company, size, value, needs, 0, g.week, "open", 0, g.week)
            s.mail(company, "Can we talk?", f"We heard about {g.company} and may want it for our whole organisation.\n"
                   f"Deal file: customers/pipeline/{key}.deal - work it with `sales {key}`\n")
            files.sync(s)
            s.learn("b2b", "pipeline")
            return f"[good]Inbound B2B lead:[/good] {company} (customers/pipeline/{key}.deal)."
    return ""


def cloud_credits(s):
    g = s.game
    g.cash += 1500
    s.mail("CloudCore for Startups", "You've been granted $1,500 in credits",
           "Welcome to our startup program. (Booked as cash for simplicity.) This is non-dilutive: no equity given up.\n")
    return "[good]Startup program:[/good] $1,500 in credits granted - non-dilutive money."


def acquirer_knocks(s):
    from . import funding
    offer = funding.make_offer(s)
    return (f"[good]{offer.buyer} sent a letter of intent to acquire you[/good] for {money(offer.price)} "
            f"({offer.kind}). Read it in your inbox; see `mna`.")


def customer_ultimatum(s):
    g = s.game
    deal = max(engine.won_deals(g), key=lambda d: d.mrr)
    s.mail(deal.company, "We need to talk about price",
           f"Our CFO is reviewing vendors. {scenario_of(g).competitor} offered us 30% less.\n"
           f"Match it or we'll have to switch.\n\nAnswer with: reply <this email>\n", kind="decision", ref=f"ultimatum:{deal.key}")
    s.learn("switching_costs")
    return f"[warn]{deal.company} demands a 30% discount[/warn] - a decision is waiting in your inbox (`reply`)."


def custom_work(s):
    g = s.game
    s.mail("a prospect", "Paid custom project?",
           "We'd pay $4,000 for a custom one-off integration only we need. Two weeks of your time.\n\n"
           "Answer with: reply <this email>\n", kind="decision", ref="custom_work")
    return "[warn]A prospect offers $4,000 for custom one-off work[/warn] - decide in your inbox (`reply`)."


EVENTS = [
    # id, bad?, weight, condition, function
    ("competitor_launch", True, 3, lambda g: engine.live(g) and g.week > 8, competitor_launch),
    ("api_price_hike", True, 2, lambda g: engine.live(g) and g.cogs_mult < 1.5, api_price_hike),
    ("bigcorp_bundle", True, 2, lambda g: g.level >= 2 and g.week > 20 and not g.flag("ev_bigcorp_bundle"), bigcorp_bundle),
    ("downturn", True, 2, lambda g: g.level >= 2 and g.week > 12 and not g.flag("downturn"), downturn),
    ("agent_accident", True, 3, lambda g: engine.live(g) and g.customers >= 10 and g.flag("agent_accidents") < 2, agent_accident),
    ("security_scare", True, 3, lambda g: g.debt > 45 and engine.live(g), security_scare),
    ("surprise_bill", True, 1, lambda g: g.level >= 2 and g.flag("ev_surprise_bill") < 2, surprise_bill),
    ("customer_ultimatum", True, 2, lambda g: bool(engine.won_deals(g)) and not g.flag("ev_customer_ultimatum"), customer_ultimatum),
    ("custom_work", True, 2, lambda g: engine.live(g) and not g.flag("ev_custom_work"), custom_work),
    ("viral_post", False, 3, lambda g: g.week > 3 and g.idea >= 0, viral_post),
    ("press", False, 2, lambda g: engine.live(g), press),
    ("inbound_investor", False, 3, lambda g: engine.mrr(g) > 1500 and engine.metrics(g)["growth"] > 0.1, inbound_investor),
    ("feature_request", False, 3, lambda g: g.customers > 20, feature_request),
    ("inbound_lead", False, 3, lambda g: engine.live(g) and g.reputation > 10, inbound_lead),
    ("cloud_credits", False, 1, lambda g: not g.flag("ev_cloud_credits"), cloud_credits),
    ("acquirer_knocks", False, 2, lambda g: _mna_ready(g), acquirer_knocks),
]


def _mna_ready(g) -> bool:
    from . import funding
    start = 14 if "acquisition" in g.focus else 24
    return (g.week >= start and not g.offers and funding.acquisition_interest(g)[0])


FOCUS_BOOST = {       # focus topic -> events made likelier this run
    "acquisition": ["acquirer_knocks"], "b2b": ["inbound_lead", "customer_ultimatum"],
    "fundraising": ["inbound_investor"], "competition": ["competitor_launch", "bigcorp_bundle"],
    "agents": ["agent_accident"],
}


def weekly(s: Session) -> list[str]:
    from ..learn import missions
    g = s.game
    params = level_params(g)
    lines: list[str] = []
    lines += mentor_mail(s)
    if g.week > 2 and g.rng.random() < params["events"]:
        boosted = {e for topic in g.focus for e in FOCUS_BOOST.get(topic, [])}
        want_bad = g.rng.random() < params["bad"]
        pool = [(eid, w * (3 if eid in boosted else 1), fn) for eid, bad, w, cond, fn in EVENTS
                if bad == want_bad and cond(g)]
        if pool:
            total = sum(w for _, w, _ in pool)
            roll = g.rng.uniform(0, total)
            for eid, weight, fn in pool:
                roll -= weight
                if roll <= 0:
                    line = fn(s)
                    if line:
                        g.bump("ev_" + eid)
                        lines.append(line)
                    break
    line = missions.maybe_issue_challenge(s)
    if line:
        lines.append(line)
    return lines


# ------------------------------------------------------------ mentor emails
def mentor_mail(s: Session) -> list[str]:
    """Your mentor nudges you when a real founder would be worried.
    Run 1 gets all nudges; later runs only the critical ones."""
    g = s.game
    m = engine.metrics(g)
    out = []

    def nudge(flag: str, condition: bool, subject: str, body: str, levels: int = 1, terms: tuple = ()):
        if condition and not g.flag(flag) and g.level <= levels:
            g.flags[flag] = 1
            s.mail("Nora (your mentor)", subject, body + "\n\n- Nora\n")
            out.append(f"[cmd]✉[/cmd]  New mail from your mentor: \"{subject}\"")
            s.learn(*terms)

    if g.focus and g.week == 2 and not g.flag("m_focus"):
        g.flags["m_focus"] = 1
        out += focus_brief(s)
    if "b2b" in g.focus and g.week == 6 and not g.flag("ev_inbound_lead"):
        line = inbound_lead(s)
        if line:
            g.bump("ev_inbound_lead")
            out.append(line)

    if not g.flag("expansion_open") and engine.fit(g) >= 55 and m["mrr"] >= 0.25 * scenario_of(g).profit_mrr * engine.win_factor(g):
        out += open_new_segment(s)

    interviews = sum(l.interviewed for l in g.leads.values())
    nudge("m_interviews", g.week >= 3 and interviews == 0, "Have you talked to anyone yet?",
          "You've been at it for weeks and haven't interviewed a single customer.\n"
          "Everything you believe about your idea is a guess until someone outside your head confirms it.\n"
          "ls customers/leads   then   interview customers/leads/<name>.txt", 5, ("customer_interview",))
    nudge("m_runway", m["runway"] < 6 and g.week > 4, "Your runway",
          f"You have about {engine.fmt_runway(m)} of runway. Raising money takes 3-6 months.\n"
          "Decide now: cut burn, grow revenue, or start pitching. Waiting is also a decision - the worst one.\n"
          "Check: metrics | grep -i runway", 3, ("runway", "burn_rate"))
    nudge("m_runway2", m["runway"] < 2.5 and g.week > 4, "URGENT: cash",
          f"About {engine.fmt_runway(m)} left. Options: `ads 0`, pause hires, raise your price, a loan (`loan`), "
          "or any investor who will take a meeting.", 5, ("runway",))
    nudge("m_churn", engine.live(g) and m["churn"] > 0.13 and g.customers > 30, "Leaky bucket",
          f"Your monthly churn is {m['churn'] * 100:.0f}%. Customers are leaving almost as fast as they come.\n"
          "Before spending on growth: interview customers, find the hidden needs, ship those features.", 2,
          ("churn", "retention", "pmf"))
    nudge("m_debt", g.debt > 40, "Your codebase is getting scary",
          f"Technical debt is at {g.debt:.0f}/100. Every agent run now produces more bugs.\n"
          "Write better specs, review before merging, set up tests (`upgrade`), and `refactor`.", 2, ("tech_debt",))
    nudge("m_review", g.flag("merged_unreviewed") >= 2, "You're merging blind",
          "You merged agent work without reviewing it - twice. The agent's report is a claim, not a fact.\n"
          "At least: grep -c FAIL agents/runs/<run>/tests.log   and   review <run>", 3, ("code_review", "hallucination"))
    nudge("m_price", engine.live(g) and g.week > 10 and g.flag("price_changes") == 0, "Have you tested your price?",
          "You've never changed your price. Your interview notes hint at what people would pay.\n"
          "grep -ri pricing customers/notes     then try     price <amount>", 1, ("pricing", "wtp"))
    nudge("m_fundraise", g.week >= 12 and g.flag("pitches") == 0 and m["runway"] < 12, "Thinking about raising?",
          "If you want outside money: `deck` builds your pitch deck, `ls investors` shows who you know,\n"
          "`network` finds more. Read an investor's file before you pitch - each cares about something different.\n"
          "And learn your numbers by heart first: they WILL ask.", 1, ("investor", "pitch_deck"))
    nudge("m_energy", g.energy < 35, "You look tired",
          f"Energy {g.energy:.0f}/100. Burned-out founders make bad decisions, then no decisions.\n"
          "`rest` costs a few hours and is the best investment this week.", 5, ("burnout",))
    nudge("m_profit", g.profitable_weeks >= 2, "You're profitable!",
          "Revenue covers your costs. You are 'default alive': from now on, raising money is a choice, not a need.", 5,
          ("default_alive", "break_even", "ramen_profitable"))
    nudge("m_unit", g.ad_budget > 0 and m["cac"] > 0 and m["ltv_cac"] < 1 and g.week > 8, "Your ads lose money",
          f"LTV:CAC is {m['ltv_cac']:.1f}. Each customer costs {money(m['cac'])} and returns {money(m['ltv'])}.\n"
          "Lower the ad budget, raise the price, or fix churn first.", 3, ("ltv_cac", "unit_economics"))
    return out


def open_new_segment(s: Session) -> list[str]:
    """Mid-game: a second kind of customer shows up. New people to
    interview, new hidden needs, a bigger market."""
    from . import files
    from .scenarios import EXPANSION, open_expansion
    g = s.game
    g.flags["expansion_open"] = g.week
    segment = EXPANSION[g.scenario]["segment"]
    leads = open_expansion(g)
    for lead in leads:
        files.write_lead(s, lead)
    s.mail("Nora (your mentor)", "A new kind of customer is knocking",
           f"Your first customers are staying. Now people you never targeted are writing in: {segment}.\n\n"
           "This is how companies grow after the first product works: an adjacent segment with the same core problem\n"
           "but its own needs. Serving them widens your market (your SAM) and raises what the product is worth.\n\n"
           "You don't know yet what they need. You know how to find out:\n"
           + "".join(f"  interview customers/leads/{lead.key}.txt\n" for lead in leads)
           + "\nA warning from experience: don't chase a second segment before the first one is happy.\n\n- Nora\n")
    s.learn("segment", "sam")
    return [f"[cmd]✉[/cmd]  [good]A new customer segment is asking about {g.company}:[/good] {segment}. "
            f"{len(leads)} new people to interview (`ls customers/leads`)."]


FOCUS_BRIEFS = {
    "validation": "Interview at least five people before `idea pick`, and follow the evidence shown by `idea`.",
    "agents": "Build a real agent workflow this time: `upgrade` lists the steps. Get to `tests`, then `subagents` and "
              "`evals`, and try `agent run <spec> --agents 3`. I've sent $300 of compute credits to get you started.",
    "fundraising": "Try to close a priced round: `network` to meet VCs, `deck`, then `pitch`. Two competing term sheets "
                   "give you leverage in `ts negotiate`. I've warmed up the investors I know for you.",
    "b2b": "Work the B2B pipeline: `outbound`, then `sales <deal>` stage by stage. Mid-size and enterprise deals need "
           "patience and specific features. A lead I know will write to you soon.",
    "debt": "Look at debt as an alternative to selling equity: `loan` shows offers, `cat finance/bank/*.txt` the terms. "
            "A bank I know is ready to talk to you early. Read the personal-guarantee clause twice.",
    "bootstrapping": "Try to win WITHOUT investors: reach profitability on customer revenue alone. Watch burn weekly.",
    "acquisition": "Explore selling the company: once you have revenue or reputation, `mna explore`. Then `waterfall "
                   "<price>` shows who would get what. Keep technical debt low - buyers inspect it.",
    "marketplace": "This company is a marketplace: revenue = GMV x take rate. Watch what happens when `price` (the take "
                   "rate) is too high, and build the feature that stops people going around you.",
    "margins": "This company has heavy compute costs. Watch gross margin in `metrics`; find the roadmap feature that "
               "cuts COGS; price so that each customer is worth serving.",
}


def focus_brief(s: Session) -> list[str]:
    """Later runs steer the player toward untouched topics: a concrete
    brief from the mentor plus a small head start for each topic."""
    from . import files
    g = s.game
    lines = [f"- {FOCUS_BRIEFS[t]}" for t in g.focus if t in FOCUS_BRIEFS]
    if not lines:
        return []
    if "agents" in g.focus:
        g.cash += 300
    if "fundraising" in g.focus:
        for inv in g.investors.values():
            if inv.known:
                inv.warm = True
        g.investors["vc_seedline"].known = g.investors["vc_seedline"].warm = True
    s.mail("Nora (your mentor)", "What to try this time",
           "You've done this before, so let's stretch. Things you haven't really practised yet:\n\n"
           + "\n\n".join(lines) + "\n\n- Nora\n")
    files.sync(s)
    return ["[cmd]✉[/cmd]  Your mentor wrote about what to try in this run (see inbox: \"What to try this time\")."]


# -------------------------------------------------------- decision replies
def reply(s: Session, email) -> bool:
    """Handle `reply <email>` for decision emails."""
    g = s.game
    if email.kind != "decision" or email.done:
        s.say("That email doesn't need a decision (or you already answered).")
        return False
    if email.ref.startswith("ultimatum:"):
        deal = g.deals[email.ref.split(":")[1]]
        m = engine.metrics(g)
        pick = s.io.choose(f"\n{deal.company} wants 30% off or they leave. Your answer:",
                           ["Give the 30% discount", "Hold your price - explain the value",
                            "Offer 10% off for a 12-month prepaid contract"])
        if pick == 0:
            deal.mrr *= 0.7
            s.say(f"They stay at {money(deal.mrr)}/month. (Discounts given under pressure tend to become permanent.)")
        elif pick == 1:
            stay = 0.3 + 0.5 * m["moat"] + m["quality"] / 250
            if g.rng.random() < stay:
                s.good("They grumble, compare alternatives - and stay at full price. Switching would have cost them more.")
                s.credit("switching_costs")
            else:
                deal.status = "lost"
                s.bad(f"They leave for {scenario_of(g).competitor}. Without switching costs, price was all that kept them.")
        else:
            if m["quality"] > 55:
                cash = deal.mrr * 0.9 * 12
                deal.mrr *= 0.9
                deal.paying_from = g.week + 52
                g.cash += cash
                s.good(f"Deal: they prepay a year - {money(cash)} in the bank today. Cash now beats cash later.")
                s.credit("cash_flow")
            else:
                deal.status = "lost"
                s.bad("They don't trust the product enough to commit for a year. They leave.")
    elif email.ref == "custom_work":
        pick = s.io.choose("\n$4,000 for two weeks of custom work only they need:",
                           ["Take the money", "Politely decline and stay focused"])
        if pick == 0:
            g.cash += 4000
            g.flags["firefight"] = g.flag("firefight") + 20
            g.debt = min(100, g.debt + 8)
            s.say("[warn]$4,000 banked.[/warn] It costs you 20 hours next week and leaves one-off code behind (debt +8). "
                  "Services money is real money - and it is how product startups quietly become agencies.")
        else:
            g.reputation = min(100, g.reputation + 1)
            s.good("You stay focused on the product every customer needs.")
    elif email.ref == "offer":
        s.say("Use the `mna` command for acquisition offers.")
        return False
    email.done = True
    return True
