"""Situations: terms that are taught when the company reaches a certain
state (rather than when the player runs a specific command).

Checked once a week. At most two are taught per week, in curriculum
order, so vocabulary arrives as a steady drip and never as a wall.
Together with the `s.learn(...)` calls in the game modules this makes
sure EVERY term in the curriculum has a situation that unlocks it
(tests/test_curriculum.py checks that).
"""
from __future__ import annotations

from .terms import ORDER


def _model(g):
    from ..game.scenarios import scenario_of
    return scenario_of(g).model


def _moat_feature(g, shipped: bool) -> bool:
    return any(f.kind == "moat" and (f.shipped if shipped else f.revealed) for f in g.features.values())


def _live(g) -> bool:
    return any(f.shipped for f in g.features.values())


# term -> condition(game, metrics)
SITUATIONS = {
    "founder": lambda g, m: g.week >= 2,
    "friends_family": lambda g, m: g.week >= 3,
    "bootstrapping": lambda g, m: g.week >= 5 and g.total_raised == 0,
    "ramen_profitable": lambda g, m: m["mrr"] > 0 and m["revenue_month"] >= 0.5 * m["costs_month"],
    "llm": lambda g, m: g.flag("runs") >= 1,
    "tool_use": lambda g, m: g.flag("runs") >= 1,
    "system_prompt": lambda g, m: g.flag("runs") >= 2 or g.has("memory"),
    "rag": lambda g, m: g.flag("runs") >= 4 or g.has("memory"),
    "version_control": lambda g, m: g.flag("merges") >= 2,
    "prompt_injection": lambda g, m: any(f.kind == "ai" and f.progress > 0 for f in g.features.values())
                                     or g.flag("runs") >= 10,
    "mcp": lambda g, m: g.has("sandbox") or g.flag("runs") >= 8,
    "fine_tuning": lambda g, m: g.has("evals") or ("finetune" in g.features and g.features["finetune"].known),
    "kpi": lambda g, m: _live(g) and g.week >= 4,
    "ab_test": lambda g, m: g.flag("price_changes") >= 2,
    "freemium": lambda g, m: _live(g) and m["customers"] >= 20 and _model(g) in ("b2c", "usage"),
    "lp_gp": lambda g, m: any(i.kind == "vc" and i.known for i in g.investors.values()),
    "anti_dilution": lambda g, m: any(t.kind == "priced" for t in g.termsheets),
    "depreciation": lambda g, m: g.week >= 20 or "ebitda" in g.notebook and g.week >= 10,
    "deferred_revenue": lambda g, m: g.flag("prepaid") > 0 or m["contract_mrr"] > 0,
    "dcf": lambda g, m: m["mrr"] >= 5000 and "revenue_multiple" in g.notebook,
    "agentic_loop": lambda g, m: g.flag("runs") >= 2,
    "context": lambda g, m: g.flag("runs") >= 2,
    "acceptance_criteria": lambda g, m: g.flag("runs") >= 3,
    "task_decomposition": lambda g, m: g.flag("runs") >= 3,
    "compute_budget": lambda g, m: g.compute_total >= 300,
    "human_in_the_loop": lambda g, m: g.flag("merges") >= 1,
    "coordination_cost": lambda g, m: g.flag("conflicts") >= 1,
    "regression": lambda g, m: g.debt >= 30,
    "customer": lambda g, m: m["customers"] >= 1,
    "subscription": lambda g, m: m["customers"] >= 5 and _model(g) in ("b2c", "b2b"),
    "saas": lambda g, m: m["customers"] >= 10 and _model(g) in ("b2c", "b2b"),
    "conversion": lambda g, m: _live(g) and g.flag("price_changes") >= 1,
    "funnel": lambda g, m: _live(g) and (g.ad_budget > 0 or g.flag("launches") >= 1),
    "virality": lambda g, m: m["customers"] >= 40 and m["fit"] >= 40,
    "cohort": lambda g, m: _live(g) and len(g.history) >= 12,
    "expansion": lambda g, m: m["contract_mrr"] > 0 or (_model(g) == "usage" and m["customers"] >= 20),
    "nrr": lambda g, m: m["contract_mrr"] > 0 or (_model(g) == "usage" and m["customers"] >= 40),
    "fixed_variable_costs": lambda g, m: m["customers"] >= 30,
    "operating_leverage": lambda g, m: g.profitable_weeks >= 3,
    "b2c": lambda g, m: _model(g) in ("b2c", "marketplace") and g.week >= 3,
    "b2b": lambda g, m: _model(g) in ("b2b", "usage") and g.week >= 3,
    "gtm": lambda g, m: _live(g),
    "positioning": lambda g, m: g.competitor >= 0.15 and _live(g),
    "value_proposition": lambda g, m: g.flag("deck") > 0 or g.flag("launches") >= 1,
    "competitor": lambda g, m: g.competitor >= 0.15,
    "moat": lambda g, m: _moat_feature(g, False) or m["mrr"] >= 3000,
    "network_effects": lambda g, m: _moat_feature(g, False) and _model(g) in ("b2c", "marketplace"),
    "switching_costs": lambda g, m: _moat_feature(g, True) or (_moat_feature(g, False) and _model(g) in ("b2b", "usage")),
    "usage_pricing": lambda g, m: _model(g) == "usage" and g.week >= 2,
    "marketplace": lambda g, m: _model(g) == "marketplace" and g.week >= 2,
    "gmv": lambda g, m: _model(g) == "marketplace" and _live(g),
    "take_rate": lambda g, m: _model(g) == "marketplace" and m["customers"] >= 5,
    "enterprise": lambda g, m: any(d.size == "enterprise" for d in g.deals.values()),
    "working_capital": lambda g, m: any(d.status == "won" and d.paying_from > g.week for d in g.deals.values()),
    "stage": lambda g, m: g.flag("pitches") >= 1,
    "power_law": lambda g, m: any(i.kind == "vc" and i.known for i in g.investors.values()) and g.flag("pitches") >= 1,
    "round": lambda g, m: g.total_raised > 0,
    "convertible_note": lambda g, m: len(g.safes) >= 1,
    "pro_rata": lambda g, m: g.total_raised > 0 and g.flag("pitches") >= 2,
    "preferred_stock": lambda g, m: any(t.kind == "priced" for t in g.termsheets),
    "participating": lambda g, m: any(t.kind == "priced" for t in g.termsheets),
    "fully_diluted": lambda g, m: any(h.kind == "pool" for h in g.holders) or len(g.safes) >= 2,
    "control": lambda g, m: any(t.status == "accepted" and t.board_seat for t in g.termsheets),
    "bridge": lambda g, m: g.total_raised > 0 and m["runway"] < 5,
    "down_round": lambda g, m: g.sentiment < 1 and g.total_raised > 0,
    "strategic_investor": lambda g, m: g.investors["cvc_bigcorp"].known,
    "burn_multiple": lambda g, m: g.total_raised > 0 and m["mrr"] > 500,
    "balance_sheet": lambda g, m: bool(g.loans) or bool(g.loan_offers),
    "limited_liability": lambda g, m: any(o.guarantee for o in g.loan_offers.values()),
    "collateral": lambda g, m: bool(g.loan_offers),
    "dscr": lambda g, m: bool(g.loans),
    "cash_flow": lambda g, m: g.week >= 8,
    "revenue_multiple": lambda g, m: m["mrr"] >= 2000,
    "exit": lambda g, m: m["mrr"] >= 4000 or g.week >= 30,
    "ipo": lambda g, m: m["mrr"] >= 15000 or g.investors["vc_atlas"].known,
    "earnout": lambda g, m: bool(g.offers),
}


def weekly_terms(s, limit: int = 2) -> None:
    """Teach up to `limit` terms whose situation has arisen."""
    from ..game import engine
    g = s.game
    m = engine.metrics(g)
    due = [t for t in ORDER if t in SITUATIONS and t not in g.notebook and SITUATIONS[t](g, m)]
    for term in due[:limit]:
        s.learn(term)
