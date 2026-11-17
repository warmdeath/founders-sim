"""PILLAR 2a - customers: interviews, choosing the idea, pricing,
marketing channels and the B2B sales pipeline."""
from __future__ import annotations

from .state import Deal, STAGES
from .scenarios import scenario_of
from .session import Session, money
from . import engine

SIZE = {
    # size: (hours per step, min weeks between steps, base success chance)
    "smb": (3, 1, 0.80),
    "mid": (5, 2, 0.68),
    "enterprise": (7, 3, 0.58),
}


def interviews_done(g) -> int:
    return sum(lead.interviewed for lead in g.leads.values())


def interview(s: Session, key: str) -> bool:
    from . import files
    g = s.game
    sc = scenario_of(g)
    lead = g.leads[key]
    if lead.interviewed:
        s.say(f"You already interviewed {lead.name}; the notes are in customers/notes/{key}.md")
        return False
    if not s.spend_hours(3, "an interview"):
        return False
    lead.interviewed = True
    discovered = []
    for fkey in lead.reveals:
        feature = g.features[fkey]
        if not feature.known:
            feature.known = True
            discovered.append(feature)
        feature.revealed = True
    files.write_note(s, lead, discovered)
    idea_name = sc.ideas[lead.likes_idea][0]
    s.good(f"Interviewed {lead.name} ({lead.role}). Notes saved: customers/notes/{key}.md")
    s.say(f"  They lit up when talking about the problem behind [bold]{idea_name}[/bold].")
    for feature in discovered:
        s.say(f"  [good]Hidden need uncovered:[/good] {feature.title} → added to product/roadmap.md")
    s.learn("customer_interview")
    if discovered:
        s.learn("hidden_need")
    n = interviews_done(g)
    if n == 2:
        s.learn("wtp")
    if n == 3:
        s.learn("validation")
    if n == 5:
        s.learn("icp", "segment")
        s.credit("customer_interview")
    g.reputation = min(100, g.reputation + 0.5)
    return True


def pick_idea(s: Session, index: int) -> bool:
    g = s.game
    sc = scenario_of(g)
    name = sc.ideas[index][0]
    if index == g.idea:
        s.say(f"You are already building {name}.")
        return False
    n = interviews_done(g)
    if g.idea >= 0:                       # changing direction later = pivot
        if not s.spend_hours(8, "a pivot"):
            return False
        g.customers *= 0.4
        g.energy = max(1, g.energy - 8)
        for feature in g.features.values():
            if feature.shipped:
                feature.quality *= 0.7
        g.bump("pivots")
        g.idea = index
        s.say(f"[warn]Pivot![/warn] {g.company} now builds [bold]{name}[/bold]. You lost 60% of customers and some polish, "
              "but kept your code and your learning.")
        s.learn("pivot")
        return True
    g.idea = index
    g.flags["idea_interviews"] = n
    s.good(f"Decision made: {g.company} will build [bold]{name}[/bold].")
    if n < 2:
        g.flags["picked_blind"] = 1
        s.note("You picked without talking to (enough) customers. Maybe it's right. Real founders who do this "
               "usually find out months later that it wasn't.")
    else:
        votes = sum(1 for lead in g.leads.values() if lead.interviewed and lead.likes_idea == index)
        s.say(f"  {votes} of your {n} interviewees really have this problem.")
        s.learn("problem_solution_fit")
        if sc.ideas[index][2] >= 0.99:
            s.credit("validation")
            s.credit("problem_solution_fit")
    return True


def set_price(s: Session, price: float) -> None:
    g = s.game
    old = g.price
    g.price = price
    g.bump("price_changes")
    wtp = engine.wtp_now(g)
    s.good(f"Price changed: {old:g} → {price:g} ({scenario_of(g).price_unit}).")
    if engine.live(g):
        if price > wtp * 1.25:
            s.note("Signals: several prospects called this 'way too expensive'. Expect fewer signups and more churn.")
        elif price < wtp * 0.6:
            s.note("Signals: nobody blinked at the price. That usually means you could charge more.")
        else:
            s.note("Signals: some grumbling, most pay. That is roughly what a good price feels like.")
    s.learn("pricing")
    if 0.75 * wtp <= price <= 1.1 * wtp and engine.live(g):
        s.credit("pricing")
        s.credit("wtp")


def set_ads(s: Session, budget: float) -> None:
    g = s.game
    g.ad_budget = budget
    if budget <= 0:
        s.good("Paid ads switched off.")
        return
    cac = engine.paid_cac(g)
    m = engine.metrics(g)
    s.good(f"Ad budget set to {money(budget)}/week. Expected: about {budget / cac:.1f} new customers per week "
           f"at a CAC of {money(cac)}." if engine.live(g) else
           f"Ad budget set to {money(budget)}/week - but nothing is live yet, so this money buys nothing.")
    s.learn("cac", "channel")
    if engine.live(g):
        ltv = m["ltv"]
        if ltv < cac:
            s.note(f"Careful: a customer is worth about {money(ltv)} (LTV) but costs {money(cac)} to acquire. "
                   "You lose money on each one.")
            g.bump("ads_underwater")
            s.learn("ltv", "ltv_cac")
        if m["churn"] > 0.12:
            s.learn("premature_scaling")
            g.bump("premature_scaling")


def content(s: Session) -> bool:
    g = s.game
    if not s.spend_hours(5, "writing content"):
        return False
    gain = 60 * (0.5 + g.reputation / 40)
    g.audience += gain
    g.reputation = min(100, g.reputation + 0.8)
    s.good(f"Published a useful post. Audience +{gain:.0f} (now {g.audience:.0f}). "
           "Content is slow but compounds - and costs hours, not cash.")
    s.learn("channel", "gtm")
    return True


def launch(s: Session) -> bool:
    g = s.game
    sc = scenario_of(g)
    if not engine.live(g):
        s.bad("Nothing to launch yet: ship at least one feature (your MVP) first.")
        return False
    if g.week - g.flag("launch_week", -99) < 10:
        s.bad("You launched recently. The audience needs something new - wait a few more weeks.")
        return False
    if not s.spend_hours(8, "a launch"):
        return False
    f = engine.fit(g)
    base = (15 + 1.5 * g.reputation + 0.05 * g.audience) * (sc.organic / 4)
    wave = 0.5 * base * (0.25 + f / 60) * engine.price_conversion(g)
    g.customers += wave
    g.flags["launch_week"] = g.week
    g.launched = True
    g.bump("launches")
    if f >= 45:
        g.reputation = min(100, g.reputation + 4)
        s.good(f"Launch day! {wave:.0f} new customers signed up and people are talking. Reputation up.")
    else:
        g.reputation = max(0, g.reputation - 1)
        s.say(f"[warn]Launch day.[/warn] {wave:.0f} signed up, but reviews say 'not quite what I need'. "
              "A launch amplifies what the product already is.")
    s.learn("launch", "gtm")
    return True


def outbound(s: Session) -> bool:
    """Prospecting: creates B2B deals in the pipeline."""
    from . import files
    g = s.game
    sc = scenario_of(g)
    if not s.spend_hours(5, "outbound prospecting"):
        return False
    created = []
    for key, company, size, value, needs in sc.deals:
        if key not in g.deals and len(created) < 2:
            if size == "enterprise" and (g.reputation < 15 or not engine.live(g)):
                continue
            created.append(Deal(key, company, size, value, needs, 0, g.week, "open", 0, g.week))
    while len(created) < 1:
        n = int(g.bump("generic_deals"))
        value = round(sc.wtp * sc.price_mult * g.rng.uniform(1.0, 2.5), -1)
        created.append(Deal(f"lead_{n:02d}", f"{g.rng.choice(['Nova', 'Blue', 'Alto', 'Kite', 'Mira', 'Volt'])}"
                            f"{g.rng.choice(['works', 'labs', ' Studio', ' Group', 'point', ' & Co'])}",
                            "smb", value, "", 0, g.week, "open", 0, g.week))
    for deal in created:
        g.deals[deal.key] = deal
        s.good(f"New lead: {deal.company} ({deal.size}, worth about {money(deal.mrr)}/month) → customers/pipeline/{deal.key}.deal")
    files.sync(s)
    s.learn("b2b", "pipeline")
    return True


def work_deal(s: Session, key: str, free: bool = False) -> bool:
    """Advance one deal by one stage (`sales <deal>`)."""
    g = s.game
    deal = g.deals[key]
    hours, wait, chance = SIZE[deal.size]
    if deal.status != "open":
        s.say(f"{deal.company} is already {deal.status}.")
        return False
    if g.week - deal.stage_week < wait and deal.stage > 0:
        if not free:
            s.say(f"{deal.company} is still digesting the '{STAGES[deal.stage]}' step. "
                  f"{deal.size.upper()} deals need {wait} week(s) between steps - that's their sales cycle.")
            s.learn("sales_cycle")
        return False
    if not engine.live(g) and deal.stage >= 1:
        if not free:
            s.bad(f"{deal.company} wants to see a working product before going further. Ship your MVP.")
        return False
    if not free and not s.spend_hours(hours, f"working the {deal.company} deal"):
        return False
    deal.touched = g.week
    next_stage = STAGES[deal.stage + 1]
    if next_stage == "won" and deal.needs and not g.features[deal.needs].shipped:
        need = g.features[deal.needs]
        if not need.known:
            need.known = True
        need.revealed = True
        s.say(f"[warn]Stalled in procurement:[/warn] {deal.company} will not sign without "
              f"[bold]{need.title}[/bold]. It is on your roadmap now.")
        s.learn("procurement", "enterprise")
        return True
    odds = chance * (0.45 + engine.fit(g) / 110) * (0.8 + g.reputation / 150)
    if next_stage in ("pilot", "won"):
        odds *= 0.5 + engine.quality(g) / 150
    if g.rng.random() < min(0.95, odds):
        deal.stage += 1
        deal.stage_week = g.week
        if STAGES[deal.stage] == "won":
            deal.status = "won"
            deal.paying_from = g.week + (4 if deal.size == "enterprise" else 1)
            g.reputation = min(100, g.reputation + {"smb": 1, "mid": 3, "enterprise": 6}[deal.size])
            g.bump("deals_won")
            s.profile.did("deal_won_" + deal.size)
            s.good(f"[bold]WON:[/bold] {deal.company} signed for {money(deal.mrr)}/month "
                   f"(ACV {money(deal.mrr * 12)}).")
            s.learn("acv")
            s.credit("pipeline")
            if deal.size == "enterprise":
                s.note("They pay on net-30 terms: the first money arrives in about 4 weeks.")
                s.learn("payment_terms")
                s.credit("enterprise")
        else:
            s.good(f"{deal.company}: moved to [bold]{STAGES[deal.stage]}[/bold].")
            if STAGES[deal.stage] == "pilot":
                s.learn("pilot")
            if STAGES[deal.stage] == "demo" and deal.size != "smb":
                s.learn("champion")
            if STAGES[deal.stage] == "procurement":
                s.learn("procurement")
    else:
        if g.rng.random() < 0.3:
            deal.status = "lost"
            g.bump("deals_lost")
            s.bad(f"{deal.company} went with another option. Deal lost. (Low fit and quality make this likelier.)")
        else:
            s.say(f"{deal.company}: no progress this time ('we need to think about it'). Try again later.")
    return True


def pipeline_tick(s: Session) -> list[str]:
    """Weekly: the sales hire works a deal; neglected deals go cold."""
    g = s.game
    lines = []
    open_deals = [d for d in g.deals.values() if d.status == "open"]
    if engine.has_hire(g, "sales") and open_deals:
        deal = max(open_deals, key=lambda d: (d.stage, d.mrr))
        before = (deal.stage, deal.status)
        quiet, s.quiet_learning = s.quiet_learning, True
        work_deal(s, deal.key, free=True)
        s.quiet_learning = quiet
        if (deal.stage, deal.status) != before:
            lines.append(f"Your sales hire moved {deal.company} to '{STAGES[deal.stage]}'.")
    for deal in open_deals:
        if g.week - deal.touched > 7 and g.rng.random() < 0.35:
            deal.status = "lost"
            g.bump("deals_cold")
            lines.append(f"[warn]{deal.company} went cold[/warn] - nobody followed up for weeks. Deal lost.")
    return lines
