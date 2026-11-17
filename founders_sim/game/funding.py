"""PILLAR 2b - money from outside: investors, pitching, term sheets, the
cap table, bank loans, hiring with equity, and acquisition offers.

The share arithmetic here is the real thing (simplified where noted):
    price per share   = pre-money valuation / shares before the round
    new shares        = investment / price per share
    investor ownership = investment / post-money valuation
"""
from __future__ import annotations

from .state import (TermSheet, Holder, Safe, Loan, LoanOffer, Offer, Investor, WEEKS_PER_MONTH)
from .scenarios import scenario_of, level_params
from .session import Session, money
from . import engine, quiz

W = WEEKS_PER_MONTH


# ================================================================ cap table
def total_shares(g) -> float:
    return sum(h.shares for h in g.holders)


def ownership(g) -> list[tuple[Holder, float]]:
    total = total_shares(g)
    return [(h, h.shares / total) for h in g.holders]


def founder_pct(g) -> float:
    return g.holders[0].shares / total_shares(g)


def pool(g) -> Holder | None:
    return next((h for h in g.holders if h.kind == "pool"), None)


def issue(g, name: str, kind: str, shares: float, invested: float = 0.0, liq_pref: float = 0.0,
          participating: bool = False) -> Holder:
    holder = Holder(name, kind, shares, invested, liq_pref, participating, g.week)
    g.holders.append(holder)
    return holder


def grant_equity(s: Session, name: str, kind: str, fraction: float) -> None:
    """Give `fraction` of the company to an employee/advisor: from the
    option pool if there is one, otherwise by issuing new shares."""
    g = s.game
    shares = total_shares(g) * fraction
    the_pool = pool(g)
    if the_pool and the_pool.shares >= shares:
        the_pool.shares -= shares
        issue(g, name, kind, shares)
        s.note(f"{fraction * 100:.1f}% granted from the option pool - no extra dilution for you.")
    else:
        shares = total_shares(g) * fraction / (1 - fraction)
        issue(g, name, kind, shares)
        s.note(f"No option pool yet, so new shares were issued: everyone (you) is diluted by {fraction * 100:.1f}%.")
    s.learn("equity", "vesting", "cliff")


def vesting_tick(s: Session) -> None:
    pass   # vesting is computed on demand from Holder.vest_start (see vested_fraction)


def vested_fraction(g, holder: Holder) -> float:
    """4-year vesting with a 1-year cliff (advisors: 2 years, no cliff)."""
    weeks = g.week - holder.vest_start
    if holder.kind == "advisor":
        return min(1.0, weeks / 104)
    if holder.kind != "employee":
        return 1.0
    return 0.0 if weeks < 52 else min(1.0, weeks / 208)


def waterfall(g, price: float) -> list[tuple[str, float]]:
    """Who gets what if the company is sold for `price`.
    Order: loans -> liquidation preferences -> everyone by ownership.
    (Simplified: SAFEs are treated as converting at their cap.)"""
    out: list[tuple[str, float]] = []
    debt = min(price, sum(l.balance for l in g.loans))
    if debt:
        out.append(("Lenders (loans repaid first)", debt))
    left = price - debt
    holders = [Holder(h.name, h.kind, h.shares, h.invested, h.liq_pref, h.participating) for h in g.holders]
    total = sum(h.shares for h in holders)
    for safe in g.safes:                         # unconverted SAFEs convert at the cap
        shares = total * (safe.amount / safe.cap) / max(1e-9, 1 - safe.amount / safe.cap)
        holders.append(Holder(f"{safe.investor} (SAFE)", "investor", shares, safe.amount, 1.0, False))
    payouts = {id(h): 0.0 for h in holders}
    converting = [h for h in holders]
    # non-participating preferred choose: take the preference OR convert to common
    for _ in range(3):
        prefs = 0.0
        for h in holders:
            if h.liq_pref > 0 and (h.participating or h not in converting):
                prefs += h.liq_pref * h.invested
        rest = max(0.0, left - prefs)
        shares = sum(h.shares for h in converting)
        changed = False
        for h in list(converting):
            if h.liq_pref > 0 and not h.participating:
                as_common = rest * h.shares / shares if shares else 0
                if as_common < h.liq_pref * h.invested:
                    converting.remove(h)
                    changed = True
        if not changed:
            break
    prefs_due = [(h, h.liq_pref * h.invested) for h in holders
                 if h.liq_pref > 0 and (h.participating or h not in converting)]
    prefs_total = sum(amount for _, amount in prefs_due)
    scale = min(1.0, left / prefs_total) if prefs_total else 1.0
    for h, amount in prefs_due:
        payouts[id(h)] += amount * scale
    rest = max(0.0, left - prefs_total * scale)
    shares = sum(h.shares for h in converting)
    for h in converting:
        payouts[id(h)] += rest * h.shares / shares if shares else 0
    for h in holders:
        if h.kind != "pool" or payouts[id(h)] > 0:
            out.append((h.name, payouts[id(h)]))
    return out


# ================================================================ investors
def traction_score(g, inv: Investor) -> float:
    m = engine.metrics(g)
    if inv.min_mrr > 0:
        return min(1.5, m["mrr"] / inv.min_mrr)
    interviews = sum(l.interviewed for l in g.leads.values())
    shipped = sum(f.shipped for f in g.features.values())
    return min(1.2, interviews / 8 * 0.45 + shipped / 3 * 0.45 + m["mrr"] / 1500)


def base_interest(g, inv: Investor) -> float:
    m = engine.metrics(g)
    score = 12 + 26 * traction_score(g, inv) + 16 * g.flag("deck") + (10 if inv.warm else 0)
    score += 0.2 * g.reputation + min(12, 60 * max(0.0, m["growth"])) + (g.sentiment - 1) * 30
    if inv.kind == "vc" and scenario_of(g).tam[1] < 2_000_000_000:
        score -= 6                                        # VCs want giant markets
    if inv.kind == "corporate":
        score += 15 * m["moat"]
    if inv.status == "watching" and m["mrr"] > inv.last_mrr * 1.2:
        score += 8                                        # you came back with progress
    return score - 12 * (inv.tough - 1)


PREFER = {
    "angel_rossi": ["customer_interview", "runway", "burn_rate", "pmf"],
    "angel_chen": ["churn", "pmf", "premature_scaling", "customer"],
    "angel_dubois": ["cac", "ltv", "ltv_cac", "payback", "gross_margin"],
    "accel_launchpad": ["customer_interview", "growth_rate", "spec", "mrr"],
    "vc_seedline": ["growth_rate", "tam", "mrr", "post_money", "dilution"],
    "vc_northstar": ["ltv_cac", "gross_margin", "churn", "option_pool", "liquidation_preference"],
    "vc_atlas": ["moat", "arr", "participating", "board", "tam"],
    "cvc_bigcorp": ["moat", "arr", "acquisition", "gross_margin"],
}


def pitch(s: Session, key: str) -> bool:
    g = s.game
    inv = g.investors[key]
    params = level_params(g)
    if inv.status == "invested":
        s.say(f"{inv.name} already invested. Send them updates, not pitches.")
        return False
    if inv.status == "termsheet":
        s.say(f"{inv.name} already sent a term sheet - see investors/termsheets/.")
        return False
    if g.week - inv.last_pitch < 6:
        s.say(f"You pitched {inv.name} {g.week - inv.last_pitch} week(s) ago. Come back with new progress "
              "(investors track the line between your updates, not single dots).")
        return False
    if not g.flag("deck"):
        s.bad("You have no pitch deck. Build one first with `deck`.")
        return False
    if not s.spend_hours(5, "a pitch meeting"):
        return False
    inv.last_pitch = g.week
    g.bump("pitches")
    s.learn("investor", "pitch")
    s.learn({"angel": "angel", "accelerator": "accelerator", "vc": "vc", "corporate": "strategic_investor"}[inv.kind])
    if not inv.warm:
        s.note("(This is a cold pitch - no introduction. Warm intros start with more trust: `network`.)")
        s.learn("warm_intro")
    interest = base_interest(g, inv)
    s.say(f"\n[title]Meeting with {inv.name}[/title] [dim]({inv.firm})[/dim]")
    s.say(f"[dim]You walk through your deck. Then the questions start. No looking things up now.[/dim]")
    questions = quiz.pick(s, params["questions"], PREFER.get(key, []),
                          numbers=2, calcs=1 if inv.kind != "angel" or g.level > 1 else 0)
    right = 0
    for q in questions:
        if quiz.ask(s, q, inv.name.split()[0]):
            right += 1
            interest += 8
        else:
            interest -= 10
    if inv.min_mrr > 0 and traction_score(g, inv) < 0.5:
        interest = min(interest, 58)        # charm does not replace the traction this investor needs
    inv.interest = int(interest)
    inv.last_mrr = engine.mrr(g)
    m = engine.metrics(g)
    s.say("")
    if interest >= 62:
        inv.status = "termsheet"
        g.scheduled.append([g.week + (1 if inv.kind != "vc" else 2), "termsheet", key])
        s.good(f"{inv.name}: \"I like this. Let me do my homework - you'll hear from me in a week or two.\"")
        s.learn("due_diligence", "traction")
        g.reputation = min(100, g.reputation + 1)
    elif interest >= 45:
        inv.status = "watching"
        s.say(f"[warn]{inv.name}:[/warn] \"Interesting, but too early for me. Keep me posted.\" "
              f"[dim](Come back in 6+ weeks with MRR at least 20% higher.)[/dim]")
    else:
        inv.status = "passed"
        g.energy = max(1, g.energy - 3)
        s.bad(f"{inv.name} passes.")
    if interest < 62:   # honest feedback on the weakest point
        reasons = []
        if traction_score(g, inv) < 0.8:
            want = f"about {money(inv.min_mrr)} MRR" if inv.min_mrr else "customer interviews and a shipped product"
            reasons.append(f"traction - they want to see {want} (you: {money(m['mrr'])} MRR)")
        if g.flag("deck") < 0.6:
            reasons.append("a thin deck - several slides have no evidence behind them (`cat investors/deck.md`)")
        if right < len(questions) - 1:
            reasons.append("you didn't know your numbers - study `metrics` before a meeting")
        if not inv.warm:
            reasons.append("no warm introduction")
        if reasons:
            s.note("Why: " + "; ".join(reasons) + ".")
    return True


def build_termsheet(g, inv: Investor) -> TermSheet:
    m = engine.metrics(g)
    params = level_params(g)
    tough = inv.tough
    value = m["valuation"] * g.rng.uniform(0.85, 1.1) / (0.75 + 0.35 * tough)
    need = max(m["gross_burn"], 3000) * 18
    amount = engine.clamp(need, inv.check_min, inv.check_max)
    amount = round(amount, -3)
    ts = TermSheet(f"ts_{len(g.termsheets) + 1:02d}_{inv.key}", inv.key, "safe", amount, expires=g.week + 5)
    if inv.kind == "accelerator":
        ts.cap, ts.discount = round(amount / 0.07, -4), 0.0
    elif inv.kind == "angel":
        ts.cap, ts.discount = max(round(value * 1.15, -5), amount * 6), 0.2
    else:
        ts.kind = "priced"
        ts.pre_money = max(round(value, -5), amount * 2.5)
        ts.liq_pref = 1.0 if tough < 1.25 else 1.5
        ts.participating = tough >= 1.2 and g.level >= 3
        ts.pool_pct = 0.10 if tough < 1.2 else 0.15
        ts.board_seat = True
    del params
    return ts


def describe_termsheet(g, ts: TermSheet) -> str:
    inv = g.investors[ts.investor]
    lines = [f"TERM SHEET - {inv.name} ({inv.firm})", f"Company: {g.company}", "=" * 52, ""]
    if ts.kind == "safe":
        pct = ts.amount / ts.cap * 100
        lines += [f"Instrument:        SAFE (simple agreement for future equity)",
                  f"Investment:        {money(ts.amount)}",
                  f"Valuation cap:     {money(ts.cap)}",
                  f"Discount:          {ts.discount * 100:.0f}%",
                  "",
                  f"What it means: no shares are issued today. At your next priced round this converts",
                  f"into shares at the cap price or the discounted round price, whichever is lower.",
                  f"If it converts at the cap it buys about {pct:.1f}% of the company."]
    else:
        post = ts.pre_money + ts.amount
        lines += [f"Instrument:        Preferred shares (priced round)",
                  f"Investment:        {money(ts.amount)}",
                  f"Pre-money:         {money(ts.pre_money)}",
                  f"Post-money:        {money(post)}",
                  f"Investor ownership: {ts.amount / post * 100:.1f}% (investment / post-money)",
                  f"Liquidation pref:  {ts.liq_pref:g}x {'PARTICIPATING' if ts.participating else 'non-participating'}",
                  f"Option pool:       {ts.pool_pct * 100:.0f}% created BEFORE the investment (dilutes existing holders only)",
                  f"Board seat:        {'yes' if ts.board_seat else 'no'}",
                  f"Founder vesting:   4 years, 1-year cliff (credit for time served)",
                  "",
                  f"Note: outstanding SAFEs convert into shares in this round."]
        own_after = founder_after(g, ts)
        lines += [f"Your ownership after closing (pool + SAFEs + new shares): about {own_after * 100:.1f}%"]
    lines += ["", f"Valid until week {ts.expires}.",
              f"Commands: ts negotiate {ts.id} | ts accept {ts.id} | ts decline {ts.id}"]
    return "\n".join(lines) + "\n"


def _priced_round_shares(g, ts: TermSheet):
    """Share math of a priced round. Returns (pool_new, [(safe, shares)], investor_shares).
    Simplification: the pool is sized as a % of pre-round shares; SAFEs
    convert at min(cap price, discounted round price)."""
    existing = total_shares(g)
    pool_new = existing * ts.pool_pct / (1 - ts.pool_pct) if ts.pool_pct else 0.0
    pre_shares = existing + pool_new
    pps = ts.pre_money / pre_shares
    safe_shares = []
    for safe in g.safes:
        cap_price = safe.cap / existing
        price = min(cap_price, pps * (1 - safe.discount))
        safe_shares.append((safe, safe.amount / price))
    return pool_new, safe_shares, ts.amount / pps


def founder_after(g, ts: TermSheet) -> float:
    pool_new, safe_shares, inv_shares = _priced_round_shares(g, ts)
    total = total_shares(g) + pool_new + sum(sh for _, sh in safe_shares) + inv_shares
    return g.holders[0].shares / total


def open_termsheets(g) -> list[TermSheet]:
    return [t for t in g.termsheets if t.status == "open"]


def negotiate(s: Session, ts: TermSheet) -> None:
    g = s.game
    inv = g.investors[ts.investor]
    m = engine.metrics(g)
    others = len(open_termsheets(g)) - 1
    s.learn("term_sheet", "leverage")
    power = 0.30 + 0.22 * others + (0.15 if m["runway"] > 6 else -0.1 if m["runway"] < 3 else 0) \
        + g.reputation / 250 - 0.17 * ts.pushes - 0.1 * (inv.tough - 1)
    s.say(f"[dim]Your leverage: {others} competing offer(s), runway {engine.fmt_runway(m)}. "
          f"{'You can push.' if power > 0.5 else 'You are negotiating from a weak position.'}[/dim]")
    if ts.kind == "safe":
        options = ["Ask for a higher valuation cap (+20%)", "Ask for more money (+25%)",
                   "Leave it as it is"]
    else:
        options = ["Ask for a higher pre-money valuation (+15%)",
                   "Ask for 1x NON-participating liquidation preference" if (ts.participating or ts.liq_pref > 1)
                   else "Ask for a smaller option pool (-5 points)",
                   "Ask to drop the board seat" if ts.board_seat else "Ask for more money (+20%)",
                   "Leave it as it is"]
    pick = s.io.choose(f"\nWhat do you push {inv.name} on?", options)
    if options[pick].startswith("Leave"):
        s.say("You leave the terms unchanged.")
        return
    ts.pushes += 1
    if g.rng.random() < engine.clamp(power, 0.05, 0.9):
        if "cap" in options[pick]:
            ts.cap = round(ts.cap * 1.2, -4)
        elif "pre-money" in options[pick]:
            ts.pre_money = round(ts.pre_money * 1.15, -4)
        elif "NON-participating" in options[pick]:
            ts.participating, ts.liq_pref = False, 1.0
            s.credit("liquidation_preference")
        elif "option pool" in options[pick]:
            ts.pool_pct = max(0.05, ts.pool_pct - 0.05)
            s.credit("option_pool")
        elif "board" in options[pick]:
            ts.board_seat = False
            s.credit("board")
        else:
            ts.amount = round(ts.amount * (1.25 if ts.kind == "safe" else 1.2), -3)
        s.good(f"{inv.name} agrees. The term sheet has been updated.")
        s.credit("leverage")
    elif power < 0.35 and g.rng.random() < 0.3:
        ts.status = "withdrawn"
        inv.status = "passed"
        s.bad(f"{inv.name}: \"I don't think we're aligned. I'm withdrawing the offer.\" "
              "Pushing hard with no alternatives and little runway is a gamble.")
        g.bump("ts_withdrawn")
    else:
        s.say(f"[warn]{inv.name}:[/warn] \"That's my best offer.\" Terms unchanged.")


def accept(s: Session, ts: TermSheet) -> None:
    """Sign a term sheet: money in, cap table changes."""
    g = s.game
    sc = scenario_of(g)
    inv = g.investors[ts.investor]
    before = founder_pct(g)
    ts.status = "accepted"
    inv.status = "invested"
    g.cash += ts.amount
    g.total_raised += ts.amount
    g.reputation = min(100, g.reputation + (3 if ts.kind == "safe" else 8))
    if ts.kind == "safe":
        g.safes.append(Safe(inv.name, ts.amount, ts.cap, ts.discount))
        s.good(f"Signed. {money(ts.amount)} from {inv.name} is in the bank (cash: {money(g.cash)}).")
        s.note(f"No shares issued yet: you still show {before * 100:.1f}% - but this SAFE will convert at your next "
               f"priced round into roughly {ts.amount / ts.cap * 100:.1f}%.")
        s.learn("safe", "valuation_cap", "discount")
        s.credit("safe")
        s.profile.did("raised_safe")
        if inv.kind == "accelerator":
            g.flags["accelerator_until"] = g.week + 10
            g.scheduled.append([g.week + 10, "demo_day", ""])
            s.note("The program takes 6 of your hours every week for 10 weeks and ends with a demo day.")
            s.profile.did("accelerator")
    else:
        pool_new, safe_shares, inv_shares = _priced_round_shares(g, ts)
        if pool_new:
            existing_pool = pool(g)
            if existing_pool:
                existing_pool.shares += pool_new
            else:
                issue(g, "Option pool (unallocated)", "pool", pool_new)
        for safe, shares in safe_shares:
            issue(g, f"{safe.investor} (converted SAFE)", "investor", shares, safe.amount, 1.0, False)
        converted = len(g.safes)
        g.safes.clear()
        issue(g, inv.name, "investor", inv_shares, ts.amount, ts.liq_pref, ts.participating)
        after = founder_pct(g)
        s.good(f"Round closed! {money(ts.amount)} from {inv.name} at {money(ts.pre_money)} pre-money "
               f"({money(ts.pre_money + ts.amount)} post). Cash: {money(g.cash)}.")
        s.say(f"  Your ownership: {before * 100:.1f}% → [bold]{after * 100:.1f}%[/bold]"
              + (f" (option pool {ts.pool_pct * 100:.0f}%" if pool_new else " (")
              + (f", {converted} SAFE(s) converted" if converted else "") + f", new investor {inv_shares / total_shares(g) * 100:.1f}%)")
        s.learn("priced_round", "pre_money", "post_money", "dilution", "cap_table")
        if converted:
            s.learn("safe_conversion")
        if pool_new:
            s.learn("option_pool")
        s.learn("liquidation_preference", "board", "lead_investor")
        for term in ("priced_round", "dilution", "cap_table"):
            s.credit(term)
        s.profile.did("raised_priced")
        if ts.participating:
            g.flags["took_participating"] = 1
        if ts.amount >= sc.raise_target * engine.win_factor(g) and "raised" not in g.won_paths:
            g.won_paths.append("raised")
            g.flags["new_win"] = 1
        # venture debt becomes available after a priced round
        g.scheduled.append([g.week + 3, "venture_debt", str(ts.amount)])
    for other in open_termsheets(g):          # other offers on the table react
        if ts.kind == "priced" and other.kind == "priced":
            other.status = "expired"
            g.investors[other.investor].status = "passed"
    if founder_pct(g) < 0.5:
        g.flags["lost_majority"] = 1
        s.learn("control")


def decline(s: Session, ts: TermSheet) -> None:
    ts.status = "declined"
    s.game.investors[ts.investor].status = "passed"
    s.say(f"You declined {ts.id}. (Saying no to money on bad terms is a real founder skill.)")


def build_deck(s: Session) -> bool:
    """`deck`: assemble the pitch deck from the evidence you really have."""
    from . import files
    g = s.game
    if not s.spend_hours(4, "building the pitch deck"):
        return False
    m = engine.metrics(g)
    sc = scenario_of(g)
    interviews = sum(l.interviewed for l in g.leads.values())
    shipped = [f.title for f in g.features.values() if f.shipped]

    def grade(strong: bool, ok: bool) -> float:
        return 1.0 if strong else (0.5 if ok else 0.0)

    sections = [
        ("Problem", grade(interviews >= 4, interviews >= 1),
         f"Based on {interviews} customer interviews." if interviews else "No customer evidence yet - just your opinion."),
        ("Solution", grade(len(shipped) >= 2, len(shipped) >= 1 or g.idea >= 0),
         f"{sc.ideas[g.idea][1] if g.idea >= 0 else 'Undecided.'} Live features: {', '.join(shipped) or 'none'}."),
        ("Market", grade(g.flag("read_market") > 0, True),
         f"TAM {money(sc.tam[1])}/yr, SAM {money(sc.sam[1])}/yr, SOM {money(sc.som[1])}/yr ({sc.som[0]:,} customers)."
         + ("" if g.flag("read_market") else " (You haven't studied customers/market.md - you'd be reading this off the slide.)")),
        ("Traction", grade(m["mrr"] >= 3000 and m["growth"] > 0.1, m["mrr"] > 0),
         f"MRR {money(m['mrr'])}, {m['customers']:.0f} customers, {m['growth'] * 100:+.0f}% month over month."),
        ("Business model", grade(m["ltv_cac"] >= 3, m["mrr"] > 0),
         f"Price {g.price:g} ({sc.price_unit}). Gross margin {m['margin'] * 100:.0f}%. "
         + (f"LTV:CAC {m['ltv_cac']:.1f}." if m["cac"] else "No paid acquisition data yet.")),
        ("Competition", grade(m["moat"] > 0.3, m["moat"] > 0.1),
         f"Main competitor: {sc.competitor}. Our moat score: {m['moat'] * 100:.0f}/100."),
        ("Team", grade(g.reputation >= 30 or engine.has_hire(g, "engineer"), g.reputation >= 10),
         f"Solo founder directing AI agents; {sum(f.shipped for f in g.features.values())} features shipped in {g.week} weeks."),
        ("The ask", 1.0,
         f"Raising about {money(round(max(m['gross_burn'], 3000) * 18, -3))} for 18 months of runway."),
    ]
    score = sum(sec[1] for sec in sections) / len(sections)
    g.flags["deck"] = round(score, 2)
    g.flags["deck_week"] = g.week
    files.write_deck(s, sections, score)
    s.good(f"Deck built: investors/deck.md (strength {score * 100:.0f}%). Weak slides are marked - "
           "they reflect missing evidence, not missing design.")
    s.learn("pitch_deck", "the_ask")
    if score >= 0.7:
        s.credit("pitch_deck")
    return True


def network(s: Session) -> bool:
    """`network`: go to events, ask for intros. Finds investors and leads."""
    from . import files
    g = s.game
    if not s.spend_hours(6, "networking"):
        return False
    s.pay(60, "travel")
    found = False
    unknown = [i for i in g.investors.values() if not i.known]
    m = engine.metrics(g)
    for inv in unknown[:2]:
        if inv.kind == "corporate" and g.level < 2:
            continue
        inv.known = True
        inv.warm = g.rng.random() < 0.35 + g.reputation / 120 + (0.3 if engine.has_hire(g, "advisor") else 0)
        s.good(f"You met {inv.name} ({inv.firm})" + (" - and got a warm introduction!" if inv.warm else ".")
               + f" → investors/{inv.key}.txt")
        found = True
    if not found:
        cold = [i for i in g.investors.values() if i.known and not i.warm and i.status in ("new", "watching")]
        if cold:
            inv = g.rng.choice(cold)
            inv.warm = True
            s.good(f"A founder friend offered a warm introduction to {inv.name}.")
            found = True
    g.reputation = min(100, g.reputation + 1)
    if not found:
        s.say("Good conversations, no new contacts this time. Reputation +1.")
    del m
    s.learn("investor", "warm_intro")
    files.sync(s)
    return True


# ==================================================================== loans
def make_loan_offers(s: Session) -> list[str]:
    """Banks approach you as you become 'bankable'."""
    g = s.game
    m = engine.metrics(g)
    out = []

    def offer(key, lender, kind, amount, apr, months, **extra):
        if key in g.loan_offers:
            return
        g.loan_offers[key] = LoanOffer(key, lender, kind, round(amount, -2), apr, months, **extra)
        out.append(key)

    if g.week >= (2 if "debt" in g.focus else 6):
        offer("startup_loan", "Cassa Locale Bank", "startup", 15000, 0.105, 36, guarantee=True)
    if m["mrr"] >= 3000:
        offer("term_loan", "Cassa Locale Bank", "term", min(120000, m["mrr"] * 4), 0.085, 24)
    if m["mrr"] >= 5000 and m["margin"] >= 0.5:
        offer("rbf_advance", "FlexCapital", "rbf", m["mrr"] * 4, 0.0, 0, rev_share=0.10, repay_multiple=1.25)
    return out


def describe_loan(offer: LoanOffer) -> str:
    lines = [f"LOAN OFFER - {offer.lender}", "=" * 44, f"Type:        {LOAN_NAMES[offer.kind]}",
             f"Amount:      {money(offer.amount)}"]
    if offer.kind == "rbf":
        lines += [f"Repayment:   {offer.rev_share * 100:.0f}% of revenue each week until "
                  f"{money(offer.amount * offer.repay_multiple)} is repaid ({offer.repay_multiple:g}x)",
                  "Interest:    none stated - the cost is the 0.25x on top. Repay fast and the implied rate is high.",
                  "Dilution:    none"]
    else:
        weekly = weekly_payment(offer.amount, offer.apr, offer.months)
        lines += [f"Interest:    {offer.apr * 100:.1f}% APR", f"Term:        {offer.months} months",
                  f"Payment:     about {money(weekly)} per week ({money(weekly * W)} per month)",
                  f"Total cost:  about {money(weekly * offer.months * W - offer.amount)} of interest over the term"]
        if offer.kind == "venture":
            lines += [f"Interest-only for the first 6 months, then amortizing.",
                      f"Warrants:    {offer.warrants * 100:.2f}% of the company (a little dilution inside the loan)"]
        if offer.kind == "term":
            lines += ["Covenant:    keep at least $3,000 in the bank at all times (penalty if breached)"]
        lines += [f"Personal guarantee: {'YES - you personally owe this if the company fails' if offer.guarantee else 'no'}"]
    lines += ["", f"Commands: loan apply {offer.key}"]
    return "\n".join(lines) + "\n"


LOAN_NAMES = {"startup": "Startup loan", "term": "Business term loan", "rbf": "Revenue-based financing",
              "venture": "Venture debt"}


def weekly_payment(amount: float, apr: float, months: int) -> float:
    """Standard amortization formula, per week."""
    n = max(1, round(months * W))
    r = apr / 52
    return amount * r / (1 - (1 + r) ** -n) if r else amount / n


def apply_loan(s: Session, key: str) -> bool:
    g = s.game
    offer = g.loan_offers[key]
    if offer.status != "open":
        s.say(f"That offer is {offer.status}.")
        return False
    if not s.spend_hours(3, "the bank meeting"):
        return False
    s.learn("debt", "principal", "interest")
    s.say(f"\n[title]Meeting with {offer.lender}[/title]")
    prefer = {"startup": ["personal_guarantee", "interest", "burn_rate"], "term": ["cash_flow", "interest", "debt", "mrr"],
              "rbf": ["rbf", "gross_margin", "mrr"], "venture": ["debt", "runway", "burn_rate"]}[offer.kind]
    questions = quiz.pick(s, 2, prefer, numbers=1, calcs=0)
    right = sum(quiz.ask(s, q, "Loan officer") for q in questions)
    if right == 0:
        s.bad("The loan officer closes the folder: \"Come back when you know your business better.\" Application rejected.")
        offer.status = "declined"
        return True
    if offer.guarantee:
        s.learn("personal_guarantee", "collateral")
        pick = s.io.choose("\nThe contract includes a PERSONAL GUARANTEE: if the company can't pay, you must. Sign?",
                           ["Sign it", "Walk away"])
        if pick == 1:
            s.say("You walk away. No loan, no personal risk.")
            s.credit("personal_guarantee")
            return True
    offer.status = "taken"
    g.cash += offer.amount
    if offer.kind == "rbf":
        loan = Loan(key, offer.lender, "rbf", offer.amount, offer.amount * offer.repay_multiple, 0.0, 999,
                    rev_share=offer.rev_share)
        s.learn("rbf")
    else:
        weekly = weekly_payment(offer.amount, offer.apr, offer.months)
        loan = Loan(key, offer.lender, offer.kind, offer.amount, offer.amount, offer.apr, round(offer.months * W),
                    weekly, offer.guarantee, interest_only=26 if offer.kind == "venture" else 0)
        s.learn("amortization")
        if offer.kind == "term":
            s.learn("covenant")
        if offer.kind == "venture":
            shares = total_shares(g) * offer.warrants
            issue(g, f"{offer.lender} (warrants)", "lender", shares)
            s.learn("venture_debt", "warrant")
    g.loans.append(loan)
    g.bump("loans_taken")
    s.profile.did("loan_" + offer.kind)
    s.good(f"Loan signed: {money(offer.amount)} from {offer.lender} is in your account. Cash: {money(g.cash)}.")
    pay, _ = engine.loan_payment(g, loan)
    s.note(f"First payment next week: about {money(pay)}. Loan payments are a fixed cost - they shorten your runway "
           "like any other, and don't shrink when revenue does" + (" (except RBF, which flexes with revenue)." if offer.kind == "rbf" else "."))
    s.credit("debt")
    return True


# ================================================================== hiring
def hire(s: Session, key: str) -> bool:
    g = s.game
    person = g.hires[key]
    if person.active:
        s.say(f"{person.name} already works with you.")
        return False
    person.active = True
    person.hired_week = g.week
    s.good(f"{person.name} joins as {person.role}. Cost: {money(person.weekly_cost)}/week.")
    if person.equity:
        grant_equity(s, person.name, "advisor" if person.role == "advisor" else "employee", person.equity)
    if person.role == "advisor":
        for inv in g.investors.values():
            if inv.known and not inv.warm and g.rng.random() < 0.5:
                inv.warm = True
        s.note("Your advisor made some introductions: several known investors are now warm.")
    g.bump("hires")
    s.learn("costs", "fixed_variable_costs")
    return True


def fire(s: Session, key: str) -> bool:
    g = s.game
    person = g.hires[key]
    if not person.active:
        s.say(f"{person.name} doesn't work with you.")
        return False
    person.active = False
    holder = next((h for h in g.holders if h.name == person.name), None)
    if holder:
        vested = vested_fraction(g, holder)
        unvested = holder.shares * (1 - vested)
        holder.shares -= unvested
        the_pool = pool(g)
        if the_pool:
            the_pool.shares += unvested
        if holder.shares < 1:
            g.holders.remove(holder)
        s.note(f"{vested * 100:.0f}% of their equity had vested; the unvested rest returns to the company. "
               "That is what vesting and the cliff are for.")
        s.credit("vesting")
        s.credit("cliff")
    g.energy = max(1, g.energy - 4)
    s.say(f"{person.name} has left the company.")
    return True


# ============================================================= acquisition
def acquisition_interest(g) -> tuple[bool, str]:
    """Would the big corporation want to buy you? (eligible?, their reason)"""
    m = engine.metrics(g)
    sc = scenario_of(g)
    if m["mrr"] >= 4000 * engine.win_factor(g) and m["fit"] >= 40:
        return True, "your revenue and customers"
    if g.reputation >= 35 and sum(f.shipped for f in g.features.values()) >= 4:
        return True, "your team's ability to ship with agents (an acquihire)"
    return False, (f"{sc.bigcorp} says: come back with real revenue (about {money(4000 * engine.win_factor(g))} MRR "
                   "and a product customers keep), or a reputation for shipping.")


def make_offer(s: Session) -> Offer:
    g = s.game
    sc = scenario_of(g)
    m = engine.metrics(g)
    by_revenue = m["arr"] * engine.clamp(engine.revenue_multiple(g, m) * 0.6, 2.5, 9)
    acquihire = 120_000 + 4_000 * g.reputation          # an acquihire pays for the team, not the business
    strategic = 1 + 0.6 * m["moat"]
    if by_revenue * strategic >= acquihire and m["mrr"] >= 2500:
        offer = Offer(sc.bigcorp, round(by_revenue * strategic * g.sentiment, -4), "acquisition", g.week)
    else:
        offer = Offer(sc.bigcorp, round(acquihire, -4), "acquihire", g.week)
    g.offers.append(offer)
    founder_gets = dict(waterfall(g, offer.price)).get(g.holders[0].name, 0)
    s.mail(f"{sc.bigcorp} Corporate Development", f"Letter of intent to acquire {g.company}",
           f"Dear founder,\n\n{sc.bigcorp} would like to acquire {g.company}.\n\n"
           f"Type of deal:   {'Acquisition of the business' if offer.kind == 'acquisition' else 'Acquihire (we mainly want the team: you)'}\n"
           f"Headline price: {money(offer.price)}\n"
           f"Process:        3 weeks of due diligence after you accept, then closing.\n"
           f"                We will inspect code quality (technical debt), production stability and churn.\n"
           f"                Findings can lower the price.\n\n"
           f"By your cap table and the liquidation waterfall, your personal share at this price would be\n"
           f"about {money(founder_gets)}.\n\n"
           f"This letter is non-binding. Commands: mna | mna negotiate | mna accept | mna decline\n",
           kind="decision", ref="offer")
    s.learn("acquisition", "loi", "exit")
    if offer.kind == "acquihire":
        s.learn("acquihire")
    return offer


def current_offer(g) -> Offer | None:
    return next((o for o in g.offers if o.status in ("open", "diligence")), None)


def negotiate_offer(s: Session, offer: Offer) -> None:
    g = s.game
    m = engine.metrics(g)
    power = 0.3 + (0.2 if m["runway"] > 6 else -0.1) + 0.3 * m["moat"] + (0.2 if open_termsheets(g) else 0) - 0.2 * offer.pushes
    offer.pushes += 1
    if g.rng.random() < engine.clamp(power, 0.05, 0.85):
        offer.price = round(offer.price * 1.15, -4)
        s.good(f"{offer.buyer} raises the offer to {money(offer.price)}.")
        s.credit("leverage")
    elif power < 0.25 and g.rng.random() < 0.35:
        offer.status = "dead"
        s.bad(f"{offer.buyer} walks away from the table.")
    else:
        s.say(f"[warn]{offer.buyer}:[/warn] \"This is our final number.\"")


def accept_offer(s: Session, offer: Offer) -> None:
    g = s.game
    offer.status = "diligence"
    offer.close_week = g.week + 3
    s.good(f"You signed the LOI. Due diligence runs for 3 weeks (closing in week {offer.close_week}).")
    s.note("Tip: this is the moment clean code and stable production pay off. `refactor` and `fix` still count until closing.")
    s.learn("due_diligence")


def close_offer(s: Session, offer: Offer) -> list[str]:
    """Due diligence ends: the price may be 'retraded', or the deal dies."""
    g = s.game
    m = engine.metrics(g)
    lines = []
    cut = 0.0
    if g.debt > 30:
        cut += min(0.3, (g.debt - 30) / 150)
        lines.append(f"Diligence finding: technical debt {g.debt:.0f}/100 - 'significant rework needed'.")
    if g.prod_bugs > 3:
        cut += 0.08
        lines.append("Diligence finding: unstable production.")
    if m["churn"] > 0.10 and offer.kind == "acquisition":
        cut += 0.1
        lines.append(f"Diligence finding: {m['churn'] * 100:.0f}% monthly churn - 'customers aren't sticky'.")
    if cut >= 0.38:
        offer.status = "dead"
        lines.append(f"[bad]{offer.buyer} pulled out after due diligence.[/bad] Too many problems under the hood.")
        g.bump("mna_failed")
        return lines
    if cut:
        offer.price = round(offer.price * (1 - cut), -3)
        lines.append(f"[warn]Price retraded down {cut * 100:.0f}% to {money(offer.price)}.[/warn]")
    else:
        lines.append("Due diligence came back clean. The price holds.")
        s.credit("due_diligence")
    offer.status = "closed"
    payout = dict(waterfall(g, offer.price)).get(g.holders[0].name, 0)
    g.flags["exit_price"] = offer.price
    g.flags["exit_payout"] = payout
    lines.append(f"[good]Deal closed at {money(offer.price)}.[/good] After loans and investor preferences, "
                 f"you personally receive {money(payout)}.")
    s.learn("waterfall")
    s.credit("acquisition")
    s.credit("waterfall")
    s.profile.did("exit_" + offer.kind)
    # an acquihire is a soft landing, never a win; an acquisition wins if it really pays you
    g.ended = "acquired" if offer.kind == "acquisition" and payout >= 300_000 * engine.win_factor(g) else "acquihired"
    if g.ended == "acquired":
        g.won_paths.append("acquired")
    return lines


# =================================================================== weekly
def weekly(s: Session) -> list[str]:
    """Funding-side events at the start of each week."""
    from . import files
    g = s.game
    sc = scenario_of(g)
    lines = []
    for item in list(g.scheduled):
        week, kind, arg = item
        if week > g.week:
            continue
        g.scheduled.remove(item)
        if kind == "termsheet":
            inv = g.investors[arg]
            ts = build_termsheet(g, inv)
            g.termsheets.append(ts)
            files.write_termsheet(s, ts)
            s.mail(inv.name, "Term sheet attached", f"As promised - my offer is in investors/termsheets/{ts.id}.txt\n"
                   f"It is valid until week {ts.expires}. Read every line, not just the amount.\n\n{inv.name}\n")
            lines.append(f"[good]A term sheet from {inv.name} arrived:[/good] investors/termsheets/{ts.id}.txt")
            s.learn("term_sheet")
            if ts.kind == "priced":
                s.learn("valuation")
        elif kind == "demo_day":
            for inv in g.investors.values():
                if inv.kind in ("vc", "angel"):
                    inv.known = True
                    inv.warm = True
            g.reputation = min(100, g.reputation + 6)
            lines.append("[good]Demo day![/good] You pitched to a full room. Every angel and VC in investors/ is now a warm contact.")
            s.learn("demo_day")
        elif kind == "venture_debt":
            key = "venture_debt"
            if key not in g.loan_offers:
                amount = float(arg) * 0.3
                g.loan_offers[key] = LoanOffer(key, "Silicon Lending", "venture", round(amount, -3), 0.12, 30, warrants=0.0075)
                s.mail("Silicon Lending", "Venture debt offer", "Congratulations on your round. We lend to VC-backed startups.\n"
                       f"Details: finance/bank/{key}.txt\n")
                lines.append("A venture debt offer arrived: finance/bank/venture_debt.txt")
        elif kind == "offer_close":
            pass
    for key in make_loan_offers(s):
        offer = g.loan_offers[key]
        s.mail(offer.lender, f"Financing offer: {LOAN_NAMES[offer.kind]}",
               f"We'd like to offer {g.company} financing. Details: finance/bank/{key}.txt\n")
        lines.append(f"A bank offer arrived: finance/bank/{key}.txt")
        s.learn("debt")
    for ts in open_termsheets(g):
        if g.week > ts.expires:
            ts.status = "expired"
            g.investors[ts.investor].status = "passed"
            lines.append(f"[warn]Term sheet {ts.id} expired.[/warn] Offers don't wait forever.")
            g.bump("ts_expired")
    offer = current_offer(g)
    if offer and offer.status == "diligence" and g.week >= offer.close_week:
        lines += close_offer(s, offer)
    elif offer and offer.status == "open" and g.week - offer.week > 6:
        offer.status = "dead"
        lines.append(f"{sc.bigcorp}'s acquisition offer lapsed.")
    return lines
