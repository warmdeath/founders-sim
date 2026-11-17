"""Starting scenarios: four different companies, each teaching a different
business model. `new_game()` turns one of them into a fresh Game.

Numbers are invented but chosen to be plausible for a tiny startup.
"""
from __future__ import annotations

from dataclasses import dataclass

from .state import (Game, Feature, Lead, Deal, Investor, Hire, Holder, FOUNDER_SHARES)


@dataclass
class Scenario:
    id: str
    company: str
    model: str                  # b2c | b2b | usage | marketplace
    tagline: str
    intro: str
    teaches: list[str]          # topics this scenario is good for
    ideas: list[tuple[str, str, float]]   # (name, pitch, HIDDEN pain 0..1)
    start_cash: float
    living: float               # founder's weekly living cost (your "salary")
    price0: float               # starting price
    price_unit: str             # what `price` means
    price_mult: float           # revenue per customer per month = price * price_mult
    wtp: float                  # typical willingness to pay (same unit as price)
    base_churn: float           # monthly churn with a mediocre product
    min_churn: float
    cac: float                  # baseline paid CAC
    organic: float              # baseline organic signups per week
    viral: float                # word-of-mouth strength
    cogs: float                 # cost to serve one customer for a month (at price0)
    infra: float                # fixed weekly infrastructure/tools cost
    tam: tuple[int, float]      # (number of potential customers, $ per year)
    sam: tuple[int, float]
    som: tuple[int, float]
    competitor: str
    bigcorp: str
    profit_mrr: float           # MRR needed (and profitable) for the "profitable company" win
    raise_target: float         # priced round size that counts as the "successful raise" win
    features: list[tuple]
    leads: list[tuple]
    deals: list[tuple]


F = Feature

SCENARIOS: dict[str, Scenario] = {}


def _add(s: Scenario):
    SCENARIOS[s.id] = s


_add(Scenario(
    id="focusly", company="Focusly", model="b2c",
    tagline="B2C subscription app for university students",
    intro=("You are 18, just out of school, with savings from summer jobs and a small gift from "
           "your grandparents. Students around you are drowning before exams. You think software "
           "can help - but you don't know yet WHICH problem is worth solving."),
    teaches=["b2c", "subscription", "churn", "virality", "angels"],
    ideas=[("Auto-flashcards", "Turn lecture notes into flashcards and a study plan automatically.", 1.0),
           ("StudyStreak", "A social network where students post study streaks.", 0.45),
           ("NoteMarket", "A campus marketplace to buy and sell lecture notes.", 0.65)],
    start_cash=16000, living=260, price0=5, price_unit="$/month per subscriber", price_mult=1.0,
    wtp=9, base_churn=0.16, min_churn=0.035, cac=22, organic=4, viral=0.012, cogs=0.9, infra=40,
    tam=(19_000_000, 1_700_000_000), sam=(2_400_000, 215_000_000), som=(60_000, 5_400_000),
    competitor="CramKing", bigcorp="EduGiant", profit_mrr=9000, raise_target=600_000,
    features=[
        ("flashcards", "Auto-flashcards from notes", 20, .28, True, "core",
         "I waste an hour every night turning my notes into flashcards by hand"),
        ("exam_planner", "Exam countdown planner", 16, .22, False, "core",
         "I never know what to study today - I need a plan that counts down to the exam"),
        ("offline", "Offline mode", 14, .16, False, "core",
         "the library wifi is terrible, an app that needs internet is useless to me"),
        ("mobile_sync", "Phone sync", 18, .14, True, "core",
         "I study on the bus, so it has to be on my phone too"),
        ("ai_tutor", "Ask-the-AI tutor chat", 26, .10, False, "ai",
         "when I don't understand a card I want to ask why, like with a tutor"),
        ("referral", "Invite-a-friend rewards", 12, .05, True, "growth",
         "I'd tell my study group if we all got something out of it"),
        ("dark_mode", "Dark mode and themes", 8, .02, True, "junk", "dark mode would be nice I guess"),
        ("social_feed", "Social study feed", 24, .03, True, "junk",
         "honestly I have enough social feeds already"),
        ("group_decks", "Shared group decks", 20, .0, False, "moat",
         "our whole course shares one deck - once it's there nobody would switch away"),
    ],
    leads=[
        ("maria", "Maria Conti", "2nd-year medicine student", ["flashcards", "exam_planner"], 0, 10, True),
        ("luca", "Luca Ferri", "1st-year engineering student", ["offline", "mobile_sync"], 0, 6, False),
        ("sofia", "Sofia Marino", "law student, commutes 2h a day", ["offline", "exam_planner"], 0, 9, True),
        ("tom", "Tom Becker", "exchange student", ["ai_tutor", "flashcards"], 0, 8, False),
        ("giulia", "Giulia Riva", "study-group organiser", ["group_decks", "referral"], 0, 7, True),
        ("ahmed", "Ahmed Said", "part-time working student", ["exam_planner", "mobile_sync"], 0, 12, True),
        ("elena", "Elena Greco", "sells her notes online", ["dark_mode"], 2, 4, False),
        ("marco", "Marco Villa", "posts study vlogs", ["social_feed"], 1, 3, False),
    ],
    deals=[("uni_torino", "Politecnico Student Union", "mid", 900, ""),
           ("prepschool", "Alpha Prep School", "smb", 350, ""),
           ("edugiant_pilot", "EduGiant Campus Program", "enterprise", 4200, "ai_tutor")],
))

_add(Scenario(
    id="ledgerly", company="Ledgerly", model="b2b",
    tagline="B2B SaaS that gets small agencies paid on time",
    intro=("Your aunt runs a design agency and complains that clients pay invoices months late. "
           "You suspect thousands of small businesses have the same problem. Businesses pay more "
           "than consumers - but selling to them takes calls, demos and patience."),
    teaches=["b2b", "sales_cycle", "enterprise", "debt", "acquisition"],
    ideas=[("InvoiceChaser", "Automatically chase late invoices with polite, escalating reminders.", 1.0),
           ("BookBot", "AI bookkeeping for freelancers.", 0.6),
           ("ReceiptSnap", "Scan receipts into expense reports.", 0.5)],
    start_cash=20000, living=280, price0=49, price_unit="$/month per company", price_mult=1.0,
    wtp=110, base_churn=0.07, min_churn=0.012, cac=260, organic=0.8, viral=0.005, cogs=6, infra=60,
    tam=(5_500_000, 6_600_000_000), sam=(420_000, 500_000_000), som=(6_000, 7_200_000),
    competitor="PayPronto", bigcorp="Finaxis", profit_mrr=14000, raise_target=900_000,
    features=[
        ("reminders", "Smart payment reminders", 20, .26, True, "core",
         "I hate writing 'just checking in' emails - I want them sent for me, politely"),
        ("bank_sync", "Bank feed reconciliation", 24, .20, False, "core",
         "I only know someone paid when I log into the bank - it should match payments itself"),
        ("accounting_export", "Export to accounting software", 16, .16, False, "core",
         "if it doesn't sync with our accounting tool my accountant will veto it"),
        ("multi_user", "Team roles and approvals", 18, .12, True, "core",
         "my office manager sends invoices but I approve the big ones"),
        ("sso_audit", "SSO and audit log", 26, .08, False, "enterprise",
         "our IT department won't approve any vendor without single sign-on and an audit trail"),
        ("api", "Public API and integrations", 24, .07, False, "moat",
         "once it's wired into our project tools, ripping it out would be a nightmare"),
        ("forecast", "Cash-flow forecast", 16, .05, True, "core", "a forecast would be nice to have"),
        ("branding", "Custom invoice themes", 10, .03, True, "junk", "themes? not a priority honestly"),
        ("chatbot", "AI chatbot assistant", 22, .03, True, "junk", "I would never use a chatbot for money stuff"),
    ],
    leads=[
        ("zia_carla", "Carla Rossi", "owner, 8-person design agency", ["reminders", "bank_sync"], 0, 120, True),
        ("devshop", "Paolo Neri", "CTO, 15-person dev shop", ["accounting_export", "api"], 0, 150, True),
        ("studio_m", "Marta Bruno", "architect, studio of 5", ["reminders", "multi_user"], 0, 90, False),
        ("freelance_j", "Jonas Weber", "freelance copywriter", ["forecast"], 1, 25, True),
        ("acct_firm", "Dott. Galli", "accountant with 60 small-business clients", ["accounting_export", "bank_sync"], 0, 140, True),
        ("bigagency", "Irene Costa", "finance lead, 200-person agency group", ["sso_audit", "multi_user"], 0, 900, True),
        ("cafe", "Rocco Sala", "cafe owner", ["branding"], 2, 15, False),
        ("consult", "Nadia Fontana", "solo consultant", ["reminders", "chatbot"], 0, 60, False),
    ],
    deals=[("neri_dev", "Neri DevShop", "smb", 220, ""),
           ("bruno_arch", "Studio Bruno", "smb", 150, ""),
           ("galli_partners", "Galli & Partners (60 clients)", "mid", 1400, "accounting_export"),
           ("costa_group", "Costa Agency Group", "enterprise", 5200, "sso_audit"),
           ("finaxis_resell", "Finaxis Partner Program", "enterprise", 7500, "api")],
))

_add(Scenario(
    id="parsefy", company="Parsefy", model="usage",
    tagline="Usage-based AI API that turns messy PDFs into clean data",
    intro=("You built a script that reads ugly PDF invoices with an AI model. Developers on a forum "
           "begged for access. An API business can grow with little sales effort - but every call "
           "costs YOU compute, so margins are thin unless you engineer them up."),
    teaches=["usage_pricing", "gross_margin", "bootstrapping", "developer_gtm", "revenue_financing"],
    ideas=[("PDF-to-JSON API", "An API that extracts structured data from any PDF.", 1.0),
           ("NoCodeScrape", "A no-code web scraping tool.", 0.5),
           ("ReviewBot", "An AI bot that reviews pull requests.", 0.6)],
    start_cash=14000, living=250, price0=60, price_unit="$/month average usage bill per customer",
    price_mult=1.0, wtp=120, base_churn=0.10, min_churn=0.02, cac=140, organic=2.0, viral=0.008,
    cogs=34, infra=50,
    tam=(1_200_000, 2_900_000_000), sam=(150_000, 360_000_000), som=(5_000, 7_000_000),
    competitor="DocuMind", bigcorp="CloudCore", profit_mrr=12000, raise_target=800_000,
    features=[
        ("accuracy", "Table extraction accuracy", 22, .26, True, "ai",
         "if it gets one number wrong in a table I can't trust any of it"),
        ("sdk", "Python and JS SDKs", 16, .18, False, "core",
         "I don't want to read API docs, I want to pip install and go"),
        ("batch", "Batch and async jobs", 20, .16, False, "core",
         "we need to push 10,000 documents overnight, not one at a time"),
        ("usage_alerts", "Usage dashboard and billing alerts", 14, .12, False, "core",
         "I got a surprise bill once from another API - never again, I need alerts"),
        ("playground", "Web playground", 14, .10, True, "core", "let me try it in the browser before I code"),
        ("caching", "Caching and cheap-model routing", 22, .0, True, "margin",
         "(internal) half of our compute bill is re-processing identical pages"),
        ("onprem", "Private cloud deployment", 28, .08, False, "enterprise",
         "legal says documents can't leave our cloud account"),
        ("formats", "50 more file formats", 18, .03, True, "junk", "we only have PDFs really"),
        ("fancy_ui", "Animated landing dashboard", 10, .02, True, "junk", "I never look at dashboards, I use the API"),
        ("finetune", "Customer-tuned models", 26, .05, False, "moat",
         "after it learned OUR document layouts, switching would mean retraining everything"),
    ],
    leads=[
        ("dev_anna", "Anna Kowalski", "backend dev at a logistics startup", ["accuracy", "sdk"], 0, 150, True),
        ("dev_raj", "Raj Patel", "indie hacker", ["sdk", "playground"], 0, 40, True),
        ("ops_lena", "Lena Fischer", "ops lead at an insurer", ["batch", "onprem"], 0, 600, True),
        ("cto_ben", "Ben Okafor", "CTO, fintech startup", ["usage_alerts", "accuracy"], 0, 220, True),
        ("data_mia", "Mia Tanaka", "data engineer", ["batch", "finetune"], 0, 180, False),
        ("nocode_sam", "Sam Lee", "no-code agency owner", ["fancy_ui"], 1, 30, False),
        ("eng_olga", "Olga Petrova", "engineering manager", ["formats"], 2, 50, False),
        ("stud_dev", "Nico Bassi", "CS student", ["playground"], 0, 10, True),
    ],
    deals=[("logistiq", "LogistiQ", "smb", 400, ""),
           ("finbright", "FinBright", "mid", 1600, "usage_alerts"),
           ("insura", "Insura Group", "enterprise", 6500, "onprem"),
           ("cloudcore_mkt", "CloudCore Marketplace listing", "enterprise", 5000, "batch")],
))

_add(Scenario(
    id="tutorly", company="Tutorly", model="marketplace",
    tagline="Marketplace connecting parents with vetted local tutors",
    intro=("You tutored maths through school and saw both sides: parents can't find good tutors, "
           "tutors can't find students. A marketplace takes a cut of every lesson - but it only "
           "works if BOTH sides show up, and nothing stops them from paying each other in cash."),
    teaches=["marketplace", "take_rate", "gmv", "network_effects", "venture_scale"],
    ideas=[("Vetted tutors", "Instantly book a vetted local tutor.", 1.0),
           ("HomeworkLive", "On-demand video homework help.", 0.55),
           ("TutorCRM", "A scheduling tool for tutors.", 0.6)],
    start_cash=16000, living=260, price0=10, price_unit="% take rate on lessons booked",
    price_mult=1.7, wtp=17, base_churn=0.13, min_churn=0.03, cac=38, organic=2.5, viral=0.011,
    cogs=3.5, infra=45,
    tam=(9_000_000, 18_000_000_000), sam=(700_000, 1_400_000_000), som=(25_000, 8_500_000),
    competitor="TutorHive", bigcorp="LearnCorp", profit_mrr=11000, raise_target=1_000_000,
    features=[
        ("booking", "Instant booking", 20, .26, True, "core",
         "I gave up after three tutors didn't answer my messages - just let me book a slot"),
        ("vetting", "Tutor vetting and reviews", 18, .22, False, "core",
         "I'm letting a stranger teach my kid - I need to see checks and real reviews"),
        ("payments", "In-app payments and payouts", 22, .18, False, "core",
         "chasing parents for cash is awkward - if the app handled it I'd never go around it"),
        ("matching", "Smart tutor matching", 18, .12, True, "core",
         "I don't want to scroll 200 profiles, show me three good ones"),
        ("packages", "Prepaid lesson packages", 14, .08, False, "core",
         "I'd happily prepay ten lessons for a small discount"),
        ("chat", "In-app chat", 12, .08, True, "core", "messaging the tutor before the lesson helps"),
        ("video", "Built-in video classroom", 26, .04, True, "junk", "we meet in person, video isn't the point"),
        ("badges", "Gamified badges", 10, .02, True, "junk", "my kid doesn't need more badges"),
        ("tutor_tools", "Tutor calendar tools", 20, .0, False, "moat",
         "my whole week lives in this calendar now - I'd lose my schedule if I left"),
    ],
    leads=[
        ("parent_laura", "Laura Bianchi", "mother of two teenagers", ["vetting", "booking"], 0, 18, True),
        ("tutor_dario", "Dario Leone", "maths tutor, 12 students", ["payments", "tutor_tools"], 0, 15, True),
        ("parent_kim", "Kim Novak", "father, works shifts", ["booking", "packages"], 0, 20, True),
        ("tutor_eva", "Eva Sartori", "language tutor", ["payments", "chat"], 0, 14, False),
        ("parent_omar", "Omar Haddad", "new in town", ["matching", "vetting"], 0, 16, True),
        ("teen_zoe", "Zoe Martini", "student, 16", ["badges"], 1, 5, False),
        ("tutor_ugo", "Ugo Pace", "retired teacher", ["tutor_tools"], 2, 8, False),
        ("school_head", "Prof. Valli", "head of a private school", ["vetting", "packages"], 0, 25, True),
    ],
    deals=[("valli_school", "Istituto Valli", "mid", 1100, "vetting"),
           ("afterschool", "BrightKids After-School", "smb", 450, ""),
           ("learncorp_b2b", "LearnCorp Employee Benefit", "enterprise", 6000, "payments")],
))


# ---------------------------------------------------------------- investors
# (key, name, kind, firm, check_min, check_max, min_mrr, cares, tough)
INVESTORS = [
    ("angel_rossi", "Giovanni Rossi", "angel", "ex-founder, sold his company in 2019", 15_000, 40_000, 0,
     "the founder and proof you talk to customers", 0.8),
    ("angel_chen", "Wei Chen", "angel", "operator angel, VP Product at a scale-up", 20_000, 60_000, 1_000,
     "product-market fit signals: retention and churn", 1.0),
    ("angel_dubois", "Claire Dubois", "angel", "angel syndicate lead", 40_000, 120_000, 3_000,
     "unit economics: CAC, LTV and payback", 1.1),
    ("accel_launchpad", "LaunchPad", "accelerator", "3-month accelerator program", 50_000, 50_000, 500,
     "speed of learning: interviews done, features shipped, week-over-week growth", 0.9),
    ("vc_seedline", "Seedline Ventures", "vc", "pre-seed / seed fund", 300_000, 900_000, 5_000,
     "growth rate and the size of the market (TAM)", 1.0),
    ("vc_northstar", "Northstar Capital", "vc", "seed fund", 600_000, 1_800_000, 9_000,
     "efficient growth: burn multiple and LTV:CAC above 3", 1.15),
    ("vc_atlas", "Atlas Partners", "vc", "Series A fund", 2_000_000, 6_000_000, 40_000,
     "a repeatable go-to-market machine and a moat", 1.3),
    ("cvc_bigcorp", "Corporate Ventures", "corporate", "strategic investor (venture arm of a corporation)",
     400_000, 1_500_000, 6_000, "strategic fit with the parent corporation", 1.1),
]

# (key, name, role, weekly_cost, equity, blurb)
CANDIDATES = [
    ("va_pia", "Pia Longo", "assistant", 280, 0.0,
     "Virtual assistant, 10h/week. Takes admin off your plate: +8 founder hours per week."),
    ("mkt_theo", "Theo Marin", "marketer", 650, 0.0,
     "Freelance growth marketer. Lowers CAC by ~20% and keeps content going without your hours."),
    ("eng_sara", "Sara Lind", "engineer", 1700, 0.015,
     "Founding engineer. Reviews agent output with you: review costs half the hours, fewer bugs slip. "
     "Wants 1.5% equity vesting over 4 years with a 1-year cliff."),
    ("sales_ivo", "Ivo Kranz", "sales", 1300, 0.005,
     "First sales hire. Works the B2B pipeline for you: one free deal step per week. 0.5% equity."),
    ("adv_nora", "Nora Hale", "advisor", 0, 0.005,
     "Advisor, three-time founder. Warm intros to investors and pitch coaching. "
     "0.5% equity vesting over 2 years, no salary."),
]

# difficulty per level: start-cash multiplier, quiz tolerance, investor bar,
# chance of a random event per week, share of events that are bad, max weeks
LEVELS = {
    1: dict(cash=1.3, tol=0.20, bar=0.70, events=0.22, bad=0.35, weeks=60, questions=3),
    2: dict(cash=1.0, tol=0.15, bar=0.90, events=0.30, bad=0.50, weeks=64, questions=4),
    3: dict(cash=0.9, tol=0.10, bar=1.00, events=0.38, bad=0.60, weeks=68, questions=4),
    4: dict(cash=0.8, tol=0.10, bar=1.15, events=0.42, bad=0.65, weeks=72, questions=5),
    5: dict(cash=0.7, tol=0.07, bar=1.30, events=0.46, bad=0.70, weeks=72, questions=5),
}


def level_params(game: Game) -> dict:
    return LEVELS[max(1, min(5, game.level))]


def scenario_of(game: Game) -> Scenario:
    return SCENARIOS[game.scenario]


def new_game(scenario_id: str, run_number: int = 1, seed: int = 0, focus: list[str] | None = None,
             company: str | None = None) -> Game:
    """Create the starting state for a run."""
    sc = SCENARIOS[scenario_id]
    level = max(1, min(5, run_number))
    params = LEVELS[level]
    game = Game(scenario=sc.id, company=company or sc.company, level=level, run_number=run_number,
                guided=run_number == 1, seed=seed, max_weeks=params["weeks"],
                cash=round(sc.start_cash * params["cash"]), price=sc.price0, focus=list(focus or []))
    for key, title, cx, weight, known, kind, quote in sc.features:
        game.features[key] = Feature(key, title, cx * 2, weight, known, kind, quote)
    for key, name, role, reveals, likes, wtp, _pricing in sc.leads:
        game.leads[key] = Lead(key, name, role, list(reveals), likes, wtp)
    for key, name, kind, firm, lo, hi, min_mrr, cares, tough in INVESTORS:
        firm_name = f"{sc.bigcorp} Ventures" if kind == "corporate" else name
        game.investors[key] = Investor(key, firm_name if kind == "corporate" else name, kind, firm, lo, hi,
                                       min_mrr * params["bar"], cares, tough * (0.85 + 0.15 * level / 2))
    game.investors["angel_rossi"].known = True
    game.investors["accel_launchpad"].known = True
    for key, name, role, cost, equity, blurb in CANDIDATES:
        game.hires[key] = Hire(key, name, role, cost, equity, blurb)
    game.holders.append(Holder("You (founder)", "founder", FOUNDER_SHARES))
    game.competitor = 0.05 * level
    return game


def pricing_mentions(scenario_id: str) -> set[str]:
    """Lead keys whose interview notes talk about pricing (for a grep challenge)."""
    return {lead[0] for lead in SCENARIOS[scenario_id].leads if lead[6]}
