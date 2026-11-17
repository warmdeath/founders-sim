"""The economic simulation: metrics formulas and the weekly tick.

`metrics(game)` computes every number a founder tracks (MRR, burn,
runway, CAC, LTV ...) from the raw state - these are the REAL formulas.
`advance_week(session)` moves the world forward one week.

Simplifications (stated honestly): revenue is collected weekly, one
"price" for all self-serve customers, churn is one blended rate, and
customers are a fractional number rather than individual people.
"""
from __future__ import annotations

from .state import Game, Week, WEEKS_PER_MONTH, STAGES
from .scenarios import scenario_of, level_params
from .session import Session, money

W = WEEKS_PER_MONTH


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ------------------------------------------------------------ product state
def pain(g: Game) -> float:
    """How real the chosen problem is (hidden; interviews hint at it)."""
    if g.idea < 0:
        return 0.0
    return scenario_of(g).ideas[g.idea][2]


def fit(g: Game) -> float:
    """Product-market fit score 0..100: do shipped features match real needs?"""
    return 100 * pain(g) * sum(f.weight * f.quality for f in g.features.values())


def quality(g: Game) -> float:
    """Product quality 0..100: how well-built is what's live?"""
    shipped = [f for f in g.features.values() if f.shipped]
    if not shipped:
        return 0.0
    base = 100 * sum(f.quality for f in shipped) / len(shipped)
    return clamp(base - 5 * g.prod_bugs - 0.25 * g.debt, 0, 100)


def feature_quality(g: Game, kind: str) -> float:
    return max((f.quality for f in g.features.values() if f.kind == kind), default=0.0)


def moat(g: Game) -> float:
    sc = scenario_of(g)
    share = min(1.0, g.customers / sc.som[0] * 4)
    return clamp(0.6 * feature_quality(g, "moat") + 0.2 * min(g.reputation, 100) / 100 + 0.2 * share, 0, 1)


def live(g: Game) -> bool:
    return any(f.shipped for f in g.features.values())


def has_hire(g: Game, role: str) -> bool:
    return any(h.active and h.role == role for h in g.hires.values())


# ---------------------------------------------------------------- customers
def revenue_per_customer(g: Game) -> float:
    return g.price * scenario_of(g).price_mult


def wtp_now(g: Game) -> float:
    """What customers will pay rises as the product fits them better."""
    return scenario_of(g).wtp * (0.55 + 0.6 * fit(g) / 100) * (1 + 0.12 * expansion(g))


def expansion(g: Game) -> float:
    """0..2: how well the product serves its second customer segment."""
    return sum(f.quality for f in g.features.values() if f.kind == "expansion")


def price_conversion(g: Game) -> float:
    """Multiplier on signups from price: overpricing kills conversion fast,
    underpricing only helps a little."""
    ratio = g.price / max(wtp_now(g), 0.01)
    if ratio <= 1:
        return 1 + 0.25 * (1 - ratio)
    return max(0.02, ratio ** -3.5)


def monthly_churn(g: Game) -> float:
    sc = scenario_of(g)
    ratio = g.price / max(wtp_now(g), 0.01)
    churn = (sc.base_churn * (1 + 0.08 * (g.level - 1)) * (1.35 - fit(g) / 100) + 0.012 * g.prod_bugs
             + 0.10 * max(0.0, ratio - 1) - 0.03 * moat(g) + 0.03 * g.competitor * (1 - moat(g)))
    return clamp(churn, sc.min_churn, 0.6)


def paid_cac(g: Game, budget: float | None = None) -> float:
    """Cost of one customer through ads: worse fit, bigger budgets and
    more competition all make it more expensive."""
    sc = scenario_of(g)
    budget = g.ad_budget if budget is None else budget
    cac = sc.cac * (1 + 0.12 * (g.level - 1)) * (1.7 - fit(g) / 100) * (1 + budget / (sc.cac * 45)) * (1 + 0.8 * g.competitor)
    if has_hire(g, "marketer"):
        cac *= 0.8
    return cac / max(price_conversion(g), 0.05)


def cogs_per_customer(g: Game) -> float:
    sc = scenario_of(g)
    scale = revenue_per_customer(g) / (sc.price0 * sc.price_mult) if sc.model == "usage" else 1.0
    saving = 1 - 0.5 * feature_quality(g, "margin")
    return sc.cogs * g.cogs_mult * saving * max(scale, 0.3)


def won_deals(g: Game):
    return [d for d in g.deals.values() if d.status == "won"]


def contract_mrr(g: Game) -> float:
    return sum(d.mrr for d in won_deals(g))


def mrr(g: Game) -> float:
    return g.customers * revenue_per_customer(g) + contract_mrr(g)


# -------------------------------------------------------------------- costs
def weekly_costs(g: Game) -> dict[str, float]:
    sc = scenario_of(g)
    costs = {
        "living": sc.living,
        "infra": sc.infra,
        "cogs": (g.customers * cogs_per_customer(g) + 0.12 * contract_mrr(g)) / W,
        "ads": g.ad_budget,
        "team": sum(h.weekly_cost for h in g.hires.values() if h.active),
        "loans": sum(loan_payment(g, loan)[0] for loan in g.loans),
    }
    return costs


def loan_payment(g: Game, loan) -> tuple[float, float]:
    """(this week's payment, interest part of it)"""
    interest = loan.balance * loan.apr / 52
    if loan.kind == "rbf":
        weekly_rev = mrr(g) / W
        return min(loan.balance, loan.rev_share * weekly_rev), 0.0
    if loan.interest_only > 0:
        return interest, interest
    return min(loan.weekly_payment, loan.balance + interest), interest


def metrics(g: Game) -> dict:
    """Every number on the founder's dashboard, computed from raw state."""
    sc = scenario_of(g)
    m: dict = {}
    m["mrr"] = mrr(g)
    m["arr"] = m["mrr"] * 12
    m["contract_mrr"] = contract_mrr(g)
    m["customers"] = g.customers + len(won_deals(g))
    m["arpu"] = m["mrr"] / m["customers"] if m["customers"] >= 1 else revenue_per_customer(g)
    m["churn"] = monthly_churn(g)
    m["cogs_pc"] = cogs_per_customer(g)
    costs = weekly_costs(g)
    recent = g.history[-4:]
    last = g.history[-8:]                      # agent compute varies a lot week to week: use an average
    avg_compute = sum(w.compute for w in last) / len(last) if last else 0.0
    m["costs_week"] = sum(costs.values()) + avg_compute
    m["costs_month"] = m["costs_week"] * W
    m["cogs_month"] = costs["cogs"] * W
    m["revenue_month"] = m["mrr"]
    m["margin"] = ((m["mrr"] - m["cogs_month"]) / m["mrr"] if m["mrr"] > 0
                   else 1 - m["cogs_pc"] / max(revenue_per_customer(g), 0.01))
    m["profit_month"] = m["revenue_month"] - m["costs_month"]
    m["gross_burn"] = m["costs_month"]
    m["burn"] = max(0.0, -m["profit_month"])
    m["runway"] = g.cash / m["burn"] if m["burn"] > 0 else float("inf")
    spend = sum(w.ad_spend for w in recent) + (len(recent) * 650 if has_hire(g, "marketer") else 0)
    new = sum(w.new for w in recent)
    m["cac"] = spend / new if new >= 1 and spend > 0 else 0.0
    m["ltv"] = m["arpu"] * m["margin"] / max(m["churn"], 0.001)
    m["ltv_cac"] = m["ltv"] / m["cac"] if m["cac"] > 0 else 0.0
    gross_profit = m["arpu"] * m["margin"]
    m["payback"] = m["cac"] / gross_profit if gross_profit > 0 and m["cac"] > 0 else 0.0
    if len(g.history) >= 5 and g.history[-5].mrr > 50:
        m["growth"] = m["mrr"] / g.history[-5].mrr - 1
    else:
        m["growth"] = 0.0
    m["fit"] = fit(g)
    m["quality"] = quality(g)
    m["moat"] = moat(g)
    new_arr = (m["mrr"] - g.history[-5].mrr) * 12 if len(g.history) >= 5 else 0.0
    m["burn_multiple"] = 0.0
    if new_arr > 0:   # net burn over ~1 month divided by net new ARR in that month
        m["burn_multiple"] = m["burn"] / new_arr
    m["loan_balance"] = sum(l.balance for l in g.loans)
    m["loan_weekly"] = costs["loans"]
    m["valuation"] = valuation(g, m)
    total = sum(h.shares for h in g.holders)
    m["founder_pct"] = g.holders[0].shares / total if total else 1.0
    m["som_share"] = g.customers / sc.som[0]
    return m


def revenue_multiple(g: Game, m: dict) -> float:
    return clamp(6 + 40 * m["growth"] + 10 * (m["margin"] - 0.6) - 40 * m["churn"] + 5 * m["moat"], 3, 25)


def valuation(g: Game, m: dict) -> float:
    """A rough PRE-money valuation investors might offer. Early on it is
    driven by story and evidence; later by ARR x a multiple."""
    interviews = sum(lead.interviewed for lead in g.leads.values())
    story = 700_000 + 9_000 * m["fit"] + 12_000 * g.reputation + 40_000 * min(interviews, 6)
    by_revenue = m["arr"] * revenue_multiple(g, m)
    return max(story, by_revenue) * g.sentiment


def stage_name(m: dict) -> str:
    return "pre-seed" if m["mrr"] < 1500 else ("seed" if m["mrr"] < 30_000 else "Series A")


def fmt_runway(m: dict) -> str:
    if m["runway"] == float("inf"):
        return "unlimited (you are not burning cash)"
    return f"{m['runway']:.1f} months"


def example_vars(g: Game) -> dict:
    """Values used to fill the {placeholders} in notebook examples."""
    sc = scenario_of(g)
    m = metrics(g)
    pct = m["founder_pct"]
    last_cash = g.history[-2].cash if len(g.history) >= 2 else g.cash
    board = sum(1 for t in g.termsheets if t.status == "accepted" and t.board_seat)
    return {
        "company": g.company, "cash": money(g.cash), "burn": money(m["burn"]),
        "gross_burn": money(m["gross_burn"]), "runway": fmt_runway(m), "mrr": money(m["mrr"]),
        "arr": money(m["arr"]), "customers": f"{m['customers']:.0f}", "price": f"{g.price:g}",
        "price_unit": sc.price_unit, "arpu": money(m["arpu"]) if m["arpu"] >= 20 else f"${m['arpu']:.2f}",
        "cac": money(m["cac"]) if m["cac"] else "n/a (no paid acquisition yet)",
        "ltv": money(m["ltv"]), "ltv_cac": f"{m['ltv_cac']:.1f}" if m["cac"] else "n/a",
        "churn": f"{m['churn'] * 100:.1f}%", "retention": f"{(1 - m['churn']) * 100:.1f}%",
        "lifetime": f"{1 / max(m['churn'], 0.001):.0f}", "margin": f"{m['margin'] * 100:.0f}%",
        "cogs": f"${m['cogs_pc']:.2f}", "revenue_month": money(m["revenue_month"]),
        "costs_month": money(m["costs_month"]), "profit_month": money(m["profit_month"]),
        "growth": f"{m['growth'] * 100:+.0f}%", "fit": f"{m['fit']:.0f}", "moat": f"{m['moat'] * 100:.0f}/100",
        "tam_d": money(sc.tam[1]), "sam_d": money(sc.sam[1]), "som_d": money(sc.som[1]),
        "som_n": f"{sc.som[0]:,}", "founder_pct": f"{pct * 100:.1f}%",
        "founder_after20": f"{pct * 80:.1f}%", "shares": f"{g.holders[0].shares:,.0f}",
        "valuation": money(m["valuation"]), "competitor": sc.competitor, "bigcorp": sc.bigcorp,
        "energy": f"{g.energy:.0f}", "raised": money(g.total_raised), "debt": f"{g.debt:.0f}",
        "prod_bugs": f"{g.prod_bugs:.0f}", "compute": money(g.compute_total),
        "payback": f"{m['payback']:.1f}" if m["payback"] else "n/a",
        "pressure": f"{g.competitor * 100:.0f}/100", "stage_name": stage_name(m),
        "safes_n": str(len(g.safes)), "safes_amt": money(sum(x.amount for x in g.safes)),
        "leverage_word": "strong" if m["runway"] > 9 else ("okay" if m["runway"] > 5 else "weak - investors can smell it"),
        "burn_multiple": f"{m['burn_multiple']:.1f}" if m["burn_multiple"] else "n/a (no ARR growth yet)",
        "multiple": f"{revenue_multiple(g, m):.0f}", "cash_change": money(g.cash - last_cash),
        "loan_balance": money(m["loan_balance"]), "loan_weekly": money(m["loan_weekly"]),
        "board_seats": str(board),
    }


# ------------------------------------------------------------- weekly tick
def weekly_churn_rate(g: Game) -> float:
    return 1 - (1 - monthly_churn(g)) ** (1 / W)


def expected_signups(g: Game) -> dict[str, float]:
    """New customers per week by source (before random noise)."""
    sc = scenario_of(g)
    if not live(g):
        return {"organic": 0.0, "word_of_mouth": 0.0, "paid": 0.0}
    f = fit(g)
    conv = price_conversion(g)
    saturation = max(0.0, 1 - g.customers / sc.som[0])
    organic = (sc.organic * (0.4 + g.reputation / 50) * (0.3 + f / 70)
               + g.audience * 0.008 * (sc.organic / 4) * (0.3 + f / 100))
    organic *= 1 - 0.06 * (g.level - 1)          # later runs: a more crowded market
    organic *= 1 + 0.35 * expansion(g)           # a second customer segment widens your reach
    organic *= 1 - 0.5 * g.competitor * (1 - moat(g))
    viral = g.customers * sc.viral * (f / 100) ** 1.5 * (1 + 1.5 * feature_quality(g, "growth"))
    paid = g.ad_budget / paid_cac(g) if g.ad_budget > 0 else 0.0
    return {"organic": organic * conv * saturation, "word_of_mouth": viral * conv * saturation,
            "paid": paid * saturation}


def win_factor(g: Game) -> float:
    """Win targets scale with the run: easier in runs 1-2, higher in 4-5."""
    return {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.25}.get(g.level, 1.5)


def advance_week(s: Session) -> list[str]:
    """Simulate one week. Returns lines for the weekly report."""
    from . import events, funding, files
    g = s.game
    sc = scenario_of(g)
    lines: list[str] = []
    cash_before = g.cash

    # 1. customers: signups and churn
    signups = expected_signups(g)
    noise = g.rng.uniform(0.85, 1.15)
    new = sum(signups.values()) * noise
    churned = g.customers * weekly_churn_rate(g)
    g.customers = max(0.0, g.customers + new - churned)
    g.last_new, g.last_churned = new, churned

    # 2. money in
    revenue = g.customers * revenue_per_customer(g) / W
    revenue += sum(d.mrr for d in won_deals(g) if g.week >= d.paying_from) / W

    # 3. money out
    costs = weekly_costs(g)
    for loan in list(g.loans):
        payment, interest = loan_payment(g, loan)
        if loan.kind == "rbf":
            loan.balance -= payment
        else:
            loan.balance -= payment - interest
            if loan.interest_only > 0:
                loan.interest_only -= 1
        loan.weeks_left -= 1
        if loan.balance <= 1:
            g.loans.remove(loan)
            lines.append(f"[good]Loan from {loan.lender} fully repaid.[/good]")
            s.credit("amortization")
    total_costs = sum(costs.values())
    g.cash += revenue - total_costs
    booked_costs = total_costs + g.week_costs_extra      # extra = agent compute etc., already paid

    # covenant: term loans require a minimum cash balance
    if any(l.kind == "term" for l in g.loans) and g.cash < 3000 and g.cash >= 0:
        g.cash -= 400
        lines.append("[bad]Covenant breach:[/bad] cash fell below the $3,000 minimum in your term loan. "
                     "The bank charged a $400 penalty.")
        s.learn("covenant")
        g.bump("covenant_breaches")

    # 4. production incidents
    if live(g) and g.customers >= 10 and g.prod_bugs > 0.5 and g.rng.random() < min(0.6, 0.07 * g.prod_bugs):
        lost = g.customers * g.rng.uniform(0.03, 0.08)
        g.customers -= lost
        g.reputation = max(0, g.reputation - 3)
        g.energy -= 6
        g.flags["firefight"] = 6
        g.bump("incidents")
        g.prod_bugs = max(0, g.prod_bugs - 1)   # the worst one got found the hard way
        lines.append(f"[bad]Incident![/bad] A bug hit customers in production. {lost:.0f} cancelled, reputation "
                     f"dropped, and firefighting will eat 6 of your hours next week.")
        s.learn("incident")

    # 5. slow drifts
    g.audience *= 0.96
    growth_signal = new - churned
    if growth_signal > 0 and fit(g) > 40:
        g.reputation = min(100, g.reputation + 0.25 + min(1.0, growth_signal / 40))
    g.competitor = clamp(g.competitor - 0.004, 0.03 * g.level, 1)

    # 6. founder energy
    used = 1 - g.hours / max(g.hours_max, 1)
    runway = metrics(g)["runway"]
    delta = 4 - 11 * used - (3 if runway < 3 else 0)
    g.energy = clamp(g.energy + delta, 0, 100)

    # 7. team: salesperson works one deal; deals go cold
    funding.vesting_tick(s)
    from . import customers
    lines += customers.pipeline_tick(s)

    # 8. profitability streak
    if revenue >= booked_costs and mrr(g) > 0:
        g.profitable_weeks += 1
    else:
        g.profitable_weeks = 0

    # 9. record the week
    g.history.append(Week(g.week, round(g.cash, 2), round(mrr(g), 2), round(g.customers, 1), round(new, 1),
                          round(churned, 1), round(revenue, 2), round(booked_costs, 2), g.ad_budget,
                          round(costs["cogs"], 2), round(fit(g), 1), round(quality(g), 1),
                          round(g.reputation, 1), round(g.energy, 1), round(g.compute_week, 2)))
    lines.insert(0, f"Week {g.week} closed: revenue {money(revenue)}, costs {money(booked_costs)}, "
                    f"cash {money(cash_before)} → {money(g.cash)}. "
                    f"Customers +{new:.0f} / -{churned:.0f} = {g.customers:.0f}.")

    # 10. next week begins
    g.week += 1
    s.fs.clock = g.week
    g.compute_week = 0.0
    g.week_costs_extra = 0.0
    g.hours_max = 50 + (8 if has_hire(g, "assistant") else 0)
    if g.energy < 25:
        g.hours_max *= 0.8
        lines.append("[warn]You are exhausted: only 80% of your hours are productive this week. "
                     "Consider `rest`.[/warn]")
    g.hours = g.hours_max - g.flags.pop("firefight", 0) - (6 if g.flag("accelerator_until") >= g.week else 0)
    g.crunched = False

    lines += funding.weekly(s)
    lines += events.weekly(s)
    files.sync(s)
    check_endings(s)
    return lines


def check_endings(s: Session) -> None:
    """Set game.ended when a lose condition hits; note win conditions."""
    g = s.game
    sc = scenario_of(g)
    if g.ended:
        return
    if g.cash < 0:
        g.ended = "bankrupt"
    elif g.energy <= 0:
        g.ended = "burnout"
    elif g.week > g.max_weeks:
        g.ended = "timeout"
    if g.ended:
        return
    target = sc.profit_mrr * win_factor(g)
    if "profitable" not in g.won_paths and g.profitable_weeks >= 8 and mrr(g) >= target:
        g.won_paths.append("profitable")
        g.flags["new_win"] = 1


def pipeline_value(g: Game) -> float:
    odds = [0.1, 0.2, 0.35, 0.55, 0.8, 1.0]
    return sum(d.mrr * odds[d.stage] for d in g.deals.values() if d.status == "open")


__all__ = ["metrics", "advance_week", "fit", "quality", "moat", "mrr", "example_vars", "STAGES"]
