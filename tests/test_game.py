"""Game logic: the economy, agents, funding maths and whole-run outcomes."""
import pytest

from founders_sim import save as savefile
from founders_sim.vfs import COMPANY
from founders_sim.learn.profile import Profile
from founders_sim.learn import missions
from founders_sim.game import engine, agents, funding, events, debrief, customers
from founders_sim.game.state import TermSheet, Safe, Loan, Deal, Offer, Holder, FOUNDER_SHARES
from founders_sim.game.scenarios import SCENARIOS, new_game, scenario_of
from tests.helpers import make_session, run, Bot, GOOD_SPEC


def ship(s, key, quality=1.0):
    f = s.game.features[key]
    f.known, f.progress, f.quality = True, 1.0, quality


# ------------------------------------------------------------------ economy
def test_metric_formulas():
    s = make_session()
    g = s.game
    g.idea = 0
    ship(s, "flashcards")
    g.customers, g.price, g.cash = 200, 8, 10_000
    m = engine.metrics(g)
    assert m["mrr"] == pytest.approx(1600)
    assert m["arr"] == pytest.approx(19200)
    assert m["arpu"] == pytest.approx(8)
    assert m["margin"] == pytest.approx(1 - 0.9 / 8)
    assert m["ltv"] == pytest.approx(8 * m["margin"] / m["churn"])
    assert m["profit_month"] == pytest.approx(1600 - m["costs_month"])
    assert m["burn"] == 0 and m["runway"] == float("inf")          # profitable: no burn, no clock
    g.customers = 50
    m = engine.metrics(g)
    assert m["burn"] == pytest.approx(m["costs_month"] - 400)
    assert m["runway"] == pytest.approx(10_000 / m["burn"])


def test_no_customers_before_a_product_is_live():
    s = make_session()
    s.game.idea = 0
    s.game.ad_budget = 500
    run(s, "next", "next")
    assert s.game.customers == 0 and s.game.cash < 20_000


def test_better_fit_lowers_churn_and_overpricing_hurts():
    s = make_session()
    g = s.game
    g.idea = 0
    ship(s, "flashcards")
    low = engine.monthly_churn(g)
    ship(s, "exam_planner"); ship(s, "offline")
    assert engine.monthly_churn(g) < low
    fair = engine.price_conversion(g)
    g.price = 40
    assert engine.price_conversion(g) < fair * 0.2
    assert engine.monthly_churn(g) > low


def test_wrong_idea_caps_fit():
    s = make_session()
    for f in s.game.features.values():
        ship(s, f.key)
    s.game.idea = 0
    right = engine.fit(s.game)
    s.game.idea = 1
    assert engine.fit(s.game) < right * 0.5


def test_week_advances_cash_and_history():
    s = make_session()
    g = s.game
    g.idea = 0
    ship(s, "flashcards")
    g.customers = 100
    cash = g.cash
    out = run(s, "next")
    assert g.week == 2 and len(g.history) == 1 and "Week 1 closed" in out
    w = g.history[0]
    assert g.cash == pytest.approx(cash + w.revenue - w.costs, abs=1)
    assert "week,cash,mrr" in s.fs.read(f"{COMPANY}/finance/metrics.csv")
    assert g.hours == g.hours_max


def test_lose_conditions():
    s = make_session()
    s.game.cash = 100
    run(s, "next")
    assert s.game.ended == "bankrupt"
    s = make_session()
    s.game.energy = 5
    run(s, "crunch")
    assert s.game.ended == "burnout"


# ------------------------------------------------------------------- agents
def test_spec_scoring_rewards_real_practice():
    s = make_session()
    g = s.game
    g.idea = 0
    run(s, "interview maria")
    template = agents.spec_template(g.features["flashcards"])
    assert agents.score_spec(s, template, "flashcards")["score"] == 0
    good = GOOD_SPEC.format(title="Auto-flashcards", key="flashcards", note="customers/notes/maria.md")
    info = agents.score_spec(s, good, "flashcards")
    assert info["score"] == 100 and info["tasks"] == 4 and info["context"]
    no_tests = good.split("## Acceptance tests")[0] + "## Out of scope\nNothing else at all.\n"
    assert agents.score_spec(s, no_tests, "flashcards")["score"] == 75


def write_spec(s, key, good=True):
    g = s.game
    run(s, f"spec new {key}")
    if good:
        s.fs.write(f"{COMPANY}/product/specs/{key}.md",
                   GOOD_SPEC.format(title=g.features[key].title, key=key, note="customers/notes/maria.md"))


def test_good_specs_get_more_done_with_fewer_bugs():
    done, bugs = {}, {}
    for good in (True, False):
        total_work = total_bugs = 0
        for seed in range(12):
            s = make_session(seed=seed)
            s.game.idea = 0
            run(s, "interview maria")
            write_spec(s, "flashcards", good)
            run(s, "agent run product/specs/flashcards.md")
            r = s.game.runs[0]
            total_work += r.work_done
            total_bugs += len(r.bugs)
        done[good], bugs[good] = total_work, total_bugs
    assert done[True] > done[False] * 1.5
    assert bugs[True] < bugs[False]


def test_agent_run_review_merge_cycle():
    s = make_session(seed=4, answers=[1])
    g = s.game
    g.idea = 0
    run(s, "interview maria")
    write_spec(s, "flashcards")
    cash = g.cash
    out = run(s, "agent run product/specs/flashcards.md --model smart --agents 2")
    r = g.runs[0]
    assert g.cash == cash - 280 and r.agents == 2 and r.model == "smart"
    assert "run_001" in out
    for name in ("report.md", "tests.log", "diff.patch"):
        assert s.fs.is_file(f"{COMPANY}/agents/runs/run_001/{name}")
    r.bugs = [agents.Bug("logic", "edge case: empty input crashes the importer", True),
              agents.Bug("hallucination", "calls an API method that does not exist in the library", False)]
    run(s, "review run_001 --deep", "review run_001 --deep", "review run_001 --deep")
    assert all(b.found for b in r.bugs)
    assert "0 failed" in s.fs.read(f"{COMPANY}/agents/runs/run_001/tests.log")
    run(s, "merge run_001")
    assert r.merged and g.features["flashcards"].progress > 0 and g.prod_bugs == 0


def test_skipping_review_ships_bugs_and_ci_blocks_red_merges():
    s = make_session(seed=4)
    g = s.game
    g.idea = 0
    write_spec(s, "flashcards", good=False)
    run(s, "agent run product/specs/flashcards.md")
    r = g.runs[0]
    r.bugs = [agents.Bug("logic", "off-by-one in pagination", True), agents.Bug("security", "secret key written into the code", False)]
    g.upgrades.append("ci")
    out = run(s, "merge run_001")
    assert not r.merged and "CI blocked the merge" in out
    g.upgrades.remove("ci")
    run(s, "merge run_001")
    assert r.merged and g.prod_bugs == 3 and g.flag("merged_unreviewed") == 1 and g.debt > 0


def test_parallel_agents_conflict_without_separate_tasks():
    conflicts = {}
    for tasks_ok in (True, False):
        count = 0
        for seed in range(15):
            s = make_session(seed=seed)
            s.game.idea = 0
            write_spec(s, "flashcards", good=tasks_ok)
            run(s, "agent run product/specs/flashcards.md --agents 4")
            count += sum(b.kind == "conflict" for b in s.game.runs[0].bugs)
        conflicts[tasks_ok] = count
    assert conflicts[False] > conflicts[True] * 1.5


def test_upgrades_have_prerequisites_and_cost_hours():
    s = make_session()
    out = run(s, "upgrade ci")
    assert "builds on" in out and not s.game.has("ci")
    hours = s.game.hours
    run(s, "upgrade tests", "upgrade ci")
    assert s.game.has("tests") and s.game.has("ci") and s.game.hours == hours - 12
    assert "INSTALLED" in s.fs.read(f"{COMPANY}/agents/upgrades.txt")


# ---------------------------------------------------------------- customers
def test_interviews_reveal_hidden_needs_and_write_notes():
    s = make_session()
    g = s.game
    assert not g.features["exam_planner"].known
    out = run(s, "interview customers/leads/maria.txt", "grep -il pricing customers/notes/* | wc -l", "cat product/roadmap.md")
    assert g.features["exam_planner"].known and g.features["exam_planner"].revealed
    assert g.hours == 47 and "Hidden need uncovered" in out and "exam_planner" in out
    assert "\n1\n" in out


def test_b2b_deal_needs_feature_and_respects_sales_cycle():
    s = make_session("ledgerly", seed=3)
    g = s.game
    g.idea = 0
    for key in ("reminders", "bank_sync", "accounting_export", "multi_user"):
        ship(s, key)
    g.reputation = 60
    g.deals["costa_group"] = Deal("costa_group", "Costa Agency Group", "enterprise", 5200, "sso_audit", 4, 1, "open", 0, 1)
    g.week = 10
    out = run(s, "sales costa_group")
    assert "will not sign without" in out and g.deals["costa_group"].status == "open"
    ship(s, "sso_audit")
    g.rng.random = lambda: 0.0
    run(s, "sales costa_group")
    deal = g.deals["costa_group"]
    assert deal.status == "won" and deal.paying_from == 14
    assert engine.contract_mrr(g) == 5200


# ------------------------------------------------------------------ funding
def test_safe_then_priced_round_share_math():
    s = make_session()
    g = s.game
    g.safes.append(Safe("Angel", 100_000, 2_000_000, 0.2))
    ts = TermSheet("ts_x", "vc_seedline", "priced", 1_000_000, pre_money=4_000_000, pool_pct=0.10, board_seat=True)
    g.termsheets.append(ts)
    predicted = funding.founder_after(g, ts)
    funding.accept(s, ts)
    total = funding.total_shares(g)
    by = {h.name: h.shares / total for h in g.holders}
    pool_shares = FOUNDER_SHARES / 9                       # 10% of pre-round shares
    pps = 4_000_000 / (FOUNDER_SHARES + pool_shares)
    assert g.holders[-1].shares == pytest.approx(1_000_000 / pps)
    safe_holder = next(h for h in g.holders if "converted SAFE" in h.name)
    assert safe_holder.shares == pytest.approx(100_000 / (2_000_000 / FOUNDER_SHARES))   # cap price beats discount
    assert by["You (founder)"] == pytest.approx(predicted)
    assert 0.6 < by["You (founder)"] < 0.75
    assert not g.safes and g.cash > 1_000_000 and g.total_raised == 1_000_000
    assert "raised" in g.won_paths


def test_waterfall_orders_debt_preferences_then_common():
    s = make_session()
    g = s.game
    g.holders.append(Holder("VC", "investor", 2_000_000, 1_000_000, 1.0, False))   # 20%
    g.loans.append(Loan("x", "Bank", "term", 200_000, 200_000, 0.08, 50, 100))
    pay = dict(funding.waterfall(g, 2_200_000))
    assert pay["Lenders (loans repaid first)"] == 200_000
    assert pay["VC"] == 1_000_000 and pay["You (founder)"] == 1_000_000      # takes the 1x preference
    pay = dict(funding.waterfall(g, 10_200_000))
    assert pay["VC"] == pytest.approx(2_000_000)                             # converts: 20% of 10M
    g.holders[-1].participating = True
    pay = dict(funding.waterfall(g, 10_200_000))
    assert pay["VC"] == pytest.approx(1_000_000 + 0.2 * 9_000_000)           # double dip
    assert sum(pay.values()) == pytest.approx(10_200_000)


def test_pitch_gives_term_sheet_only_with_traction_and_right_answers():
    s = make_session(seed=5)
    g = s.game
    out = run(s, "pitch investors/angel_rossi.txt")
    assert "no pitch deck" in out
    run(s, "deck")
    from founders_sim.game import quiz
    quiz.ask = lambda sess, q, speaker="": False
    run(s, "pitch investors/angel_rossi.txt")
    assert g.investors["angel_rossi"].status == "passed"
    s = make_session(seed=5)
    g = s.game
    g.idea = 0
    for l in g.leads.values():
        l.interviewed = True
    for key in ("flashcards", "exam_planner", "offline"):
        ship(s, key)
    g.customers = 150
    g.investors["angel_rossi"].warm = True
    quiz.ask = lambda sess, q, speaker="": True
    run(s, "deck", "pitch angel_rossi")
    assert g.investors["angel_rossi"].status == "termsheet"
    out = run(s, "next", "ts", "cat investors/termsheets/ts_01_angel_rossi.txt")
    ts = g.termsheets[0]
    assert ts.kind == "safe" and "Valuation cap" in out
    cash = g.cash
    run(s, f"ts accept {ts.id}", "captable")
    assert g.cash == cash + ts.amount and len(g.safes) == 1 and funding.founder_pct(g) == 1.0


def test_loan_amortizes_and_guarantee_can_be_refused():
    s = make_session(answers=[1])
    g = s.game
    run(s, *["next"] * 6)
    assert "startup_loan" in g.loan_offers and s.fs.is_file(f"{COMPANY}/finance/bank/startup_loan.txt")
    from founders_sim.game import quiz
    quiz.ask = lambda sess, q, speaker="": True
    run(s, "loan apply startup_loan")                     # answers "Walk away"
    assert not g.loans
    s.io.answers = [0]
    cash = g.cash
    run(s, "loan apply finance/bank/startup_loan.txt")
    assert len(g.loans) == 1 and g.cash == cash + 15000
    loan = g.loans[0]
    pay, interest = engine.loan_payment(g, loan)
    assert interest == pytest.approx(15000 * 0.105 / 52)
    run(s, "next")
    assert loan.balance == pytest.approx(15000 - (pay - interest))
    total = funding.weekly_payment(15000, 0.105, 36) * 156
    assert 17000 < total < 18000


def test_acquisition_due_diligence_punishes_tech_debt():
    for debt, expect_cut in ((5, False), (75, True)):
        s = make_session(answers=[0])
        g = s.game
        g.idea = 0
        for f in list(g.features.values())[:5]:
            ship(s, f.key)
        g.customers, g.reputation, g.debt, g.week, g.cash = 900, 50, debt, 30, 50_000
        run(s, "mna explore")
        offer = g.offers[0]
        price = offer.price
        run(s, "mna", "mna accept", "next", "next", "next")
        assert g.ended in ("acquired", "acquihired")
        assert (offer.price < price) == expect_cut
        assert g.flag("exit_payout") == pytest.approx(offer.price)


# ---------------------------------------------------------------- the world
def test_every_event_runs():
    s = make_session("ledgerly", run_number=3, seed=2)
    g = s.game
    g.idea = 0
    ship(s, "reminders")
    g.customers = 50
    g.deals["neri_dev"] = Deal("neri_dev", "Neri DevShop", "smb", 220, "", 5, 1, "won", 0, 1)
    for eid, _bad, _w, _cond, fn in events.EVENTS:
        assert isinstance(fn(s), str), eid
    assert len(g.emails) > 8
    s.io.answers = [1, 1]
    for email in [e for e in g.emails if e.kind == "decision" and e.ref != "offer"]:
        assert events.reply(s, email) and email.done


def test_tutorial_missions_advance():
    s = make_session(guided=True, quiet=False)
    out = run(s, "pwd", "ls", "cat inbox/001_welcome_read_me_first.txt")
    assert s.game.mission == 3 and "Mission complete" in out and "Shell skill" in out
    run(s, "cd product", "cd ..", "ls -l customers/leads", "interview maria luca sofia", "grep -i pricing customers/notes/*")
    assert s.game.mission == 7


def test_challenges_check_real_shell_results():
    s = make_session(run_number=2)
    g = s.game
    run(s, "next", "next")
    assert g.challenges.get("c1") == "open"
    n = len(s.fs.listdir(f"{COMPANY}/inbox"))
    out = run(s, "answer c1 999")
    assert "Not yet" in out
    run(s, f"answer c1 {n}")
    assert g.challenges["c1"] == "done" and s.profile.bash["pipe"]["ok"] >= 2
    g.challenges["c10"] = "open"
    run(s, "echo 'tail -n 1 finance/metrics.csv' > reports/weekly.sh", "answer c10")
    assert g.challenges["c10"] == "open"
    run(s, "chmod +x reports/weekly.sh", "answer c10")
    assert g.challenges["c10"] == "done"


def test_save_and_load_roundtrip():
    s = make_session(seed=9)
    run(s, "interview maria", "idea pick 1", "echo hello > reports/mine.txt", "cd product", "export FOO=bar", "next")
    savefile.save(s)
    loaded, shell_state = savefile.load(s.io, Profile.load())
    g, h = s.game, loaded.game
    assert (h.week, h.cash, h.idea, h.leads["maria"].interviewed) == (g.week, g.cash, g.idea, True)
    assert loaded.fs.read(f"{COMPANY}/reports/mine.txt") == "hello\n"
    assert shell_state["cwd"].endswith("/product") and shell_state["env"]["FOO"] == "bar"
    assert h.rng.random() == g.rng.random()               # the dice continue identically


def test_all_scenarios_start_consistently():
    for key, sc in SCENARIOS.items():
        g = new_game(key, 1)
        assert sum(f.weight for f in g.features.values()) == pytest.approx(1.0), key
        assert max(i[2] for i in sc.ideas) == 1.0
        for lead in g.leads.values():
            assert all(r in g.features for r in lead.reveals)
        for deal in sc.deals:
            assert deal[4] == "" or deal[4] in g.features
        assert new_game(key, 5).cash < g.cash


# ------------------------------------------------------------ whole runs
def test_careless_player_fails_and_thoughtful_player_wins():
    careless = [Bot(make_session("focusly", 2, seed), skill=0.3).play() for seed in range(3)]
    assert all(end in ("bankrupt", "timeout", "burnout") for end in careless)
    thoughtful = [Bot(make_session("focusly", 1, seed), skill=1.0).play() for seed in range(3)]
    assert all(end in ("profitable", "raised", "acquired") for end in thoughtful)


@pytest.mark.parametrize("scenario", list(SCENARIOS))
def test_full_run_and_debrief_on_every_scenario(scenario):
    profile = Profile()
    s = make_session(scenario, 1, seed=1, profile=profile)
    bot = Bot(s, skill=0.75)
    assert bot.play() != ""
    debrief.finish_run(s)
    out = s.io.output()
    assert "What went well" in out and "Next run" in out and "Mistakes" in out
    assert profile.runs == 1 and profile.scenarios[scenario] == 1 and profile.endings[0]["scenario"] == scenario
    assert profile.counts()["seen"] + profile.counts()["practiced"] + profile.counts()["mastered"] > 40
    focus, nxt = debrief.plan_next_run(profile, scenario)
    assert nxt != scenario and nxt in SCENARIOS


def test_debrief_names_mistakes():
    s = make_session()
    g = s.game
    run(s, "idea pick 2")
    g.flags.update({"merged_unreviewed": 3, "bugs_shipped": 4})
    g.runs.append(agents.AgentRun("run_001", "flashcards", "x", 1, "fast", 1, 45, 20, 1.0, [], "none", True))
    g.ended = "bankrupt"
    debrief.finish_run(s)
    out = s.io.output()
    assert "before talking to customers" in out and "without review" in out and "Weak specs" in out
    assert "ran out of cash without ever asking" in out
