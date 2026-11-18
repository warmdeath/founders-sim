"""All the data that describes one run of the game.

Everything here is a plain dataclass with simple fields (numbers, strings,
lists, dicts) so the whole game can be saved to a JSON file and loaded
back (see `to_plain` / `from_plain` at the bottom).
"""
from __future__ import annotations

import dataclasses
import random
import typing
from dataclasses import dataclass, field

WEEKS_PER_MONTH = 52 / 12      # 4.33 - used to convert weekly <-> monthly numbers
FOUNDER_SHARES = 8_000_000     # shares the founder owns on day one


@dataclass
class Feature:
    key: str
    title: str
    complexity: int             # work points an agent must produce
    weight: float               # HIDDEN: how much customers really need it (all weights sum to 1)
    known: bool                 # is it on the roadmap yet?
    kind: str = "core"          # core | junk | moat | enterprise | growth | margin | ai
    quote: str = ""             # what customers say about it in interviews
    revealed: bool = False      # has an interview confirmed it matters?
    progress: float = 0.0       # 0..1 built so far (merged work)
    quality: float = 0.0        # 0..1 quality of the shipped feature (0 = not shipped)

    @property
    def shipped(self) -> bool:
        return self.quality > 0


@dataclass
class Lead:
    """A potential customer you can interview."""
    key: str
    name: str
    role: str
    reveals: list[str]          # feature keys this person cares about
    likes_idea: int             # index of the idea whose problem they really have
    wtp: float                  # willingness to pay (per month)
    interviewed: bool = False


@dataclass
class Bug:
    kind: str                   # logic | hallucination | security | conflict
    text: str
    visible_in_tests: bool      # would show up as FAIL in tests.log
    found: bool = False


@dataclass
class AgentRun:
    id: str
    feature: str
    spec_path: str
    agents: int
    model: str
    week: int
    cost: float
    spec_score: int
    work_done: float            # share of the feature this run implemented (0..1)
    bugs: list[Bug] = field(default_factory=list)
    review: str = "none"        # none | quick | deep
    merged: bool = False
    discarded: bool = False


@dataclass
class Deal:
    """A B2B sales opportunity moving through the pipeline."""
    key: str
    company: str
    size: str                   # smb | mid | enterprise
    mrr: float
    needs: str = ""             # feature key procurement insists on ("" = none)
    stage: int = 0              # index into STAGES
    stage_week: int = 0         # week it entered this stage
    status: str = "open"        # open | won | lost
    paying_from: int = 0        # first week cash arrives (net-30 payment terms)
    touched: int = 0            # last week you worked on it


STAGES = ["lead", "discovery", "demo", "pilot", "procurement", "won"]


@dataclass
class Investor:
    key: str
    name: str
    kind: str                   # angel | accelerator | vc | corporate
    firm: str
    check_min: float
    check_max: float
    min_mrr: float              # traction they want before investing
    cares: str                  # what they focus on (shown in their file)
    tough: float = 1.0          # >1 = harder questions, harsher terms
    known: bool = False
    warm: bool = False          # do you have a warm intro?
    interest: int = 0
    last_pitch: int = -99
    last_mrr: float = 0.0
    status: str = "new"         # new | passed | watching | termsheet | invested


@dataclass
class TermSheet:
    id: str
    investor: str
    kind: str                   # safe | priced
    amount: float
    cap: float = 0.0            # SAFE: valuation cap
    discount: float = 0.0       # SAFE: discount (0.2 = 20%)
    pre_money: float = 0.0      # priced round
    liq_pref: float = 1.0       # 1.0 = "1x"
    participating: bool = False
    pool_pct: float = 0.0       # option pool created BEFORE the round (comes out of your share)
    board_seat: bool = False
    expires: int = 0
    status: str = "open"        # open | accepted | declined | expired | withdrawn
    pushes: int = 0             # how many times you negotiated


@dataclass
class Holder:
    """One line of the cap table."""
    name: str
    kind: str                   # founder | investor | pool | employee | advisor | lender
    shares: float
    invested: float = 0.0
    liq_pref: float = 0.0       # multiple of `invested` they get back first
    participating: bool = False
    vest_start: int = 0         # week vesting started (employees/advisors)


@dataclass
class Safe:
    investor: str
    amount: float
    cap: float
    discount: float


@dataclass
class Loan:
    key: str
    lender: str
    kind: str                   # startup | term | rbf | venture
    principal: float
    balance: float
    apr: float
    weeks_left: int
    weekly_payment: float = 0.0
    guarantee: bool = False     # personal guarantee
    rev_share: float = 0.0      # revenue-based financing: share of revenue paid each week
    interest_only: int = 0      # weeks of interest-only payments left


@dataclass
class LoanOffer:
    key: str
    lender: str
    kind: str
    amount: float
    apr: float
    months: int
    guarantee: bool = False
    rev_share: float = 0.0
    repay_multiple: float = 0.0
    warrants: float = 0.0
    status: str = "open"        # open | taken | declined


@dataclass
class Hire:
    key: str
    name: str
    role: str                   # engineer | marketer | sales | assistant | advisor
    weekly_cost: float
    equity: float               # fraction of company, e.g. 0.015
    blurb: str = ""
    hired_week: int = 0
    active: bool = False


@dataclass
class Email:
    id: int
    sender: str
    subject: str
    body: str
    week: int
    kind: str = "info"          # info | decision | challenge
    ref: str = ""               # what a decision/challenge refers to
    done: bool = False


@dataclass
class Offer:
    """An acquisition offer (letter of intent)."""
    buyer: str
    price: float
    kind: str                   # acquisition | acquihire
    week: int
    status: str = "open"        # open | diligence | closed | dead
    close_week: int = 0
    pushes: int = 0


@dataclass
class Week:
    """One row of finance/metrics.csv."""
    week: int
    cash: float
    mrr: float
    customers: float
    new: float
    churned: float
    revenue: float
    costs: float
    ad_spend: float
    cogs: float
    fit: float
    quality: float
    reputation: float
    energy: float
    compute: float = 0.0        # agent compute spent that week


@dataclass
class Game:
    scenario: str
    company: str
    level: int = 1                      # difficulty 1..5 (run number, capped)
    run_number: int = 1
    guided: bool = True
    seed: int = 0
    week: int = 1
    max_weeks: int = 60
    cash: float = 0.0
    hours: float = 50.0
    hours_max: float = 50.0
    energy: float = 100.0
    reputation: float = 5.0
    price: float = 0.0
    customers: float = 0.0
    ad_budget: float = 0.0
    audience: float = 0.0               # content marketing "stock" (decays slowly)
    launched: bool = False
    idea: int = -1                      # which idea was picked (-1 = not yet)
    idea_order: list[int] = field(default_factory=list)   # order the ideas are SHOWN in (shuffled from run 2)
    prod_bugs: float = 0.0              # bugs live in production
    debt: float = 0.0                   # technical debt 0..100
    competitor: float = 0.0             # competitive pressure 0..1
    sentiment: float = 1.0              # funding market mood (1 = normal)
    cogs_mult: float = 1.0              # shocks to cost of serving a customer
    compute_week: float = 0.0           # agent spend this week
    compute_total: float = 0.0
    week_costs_extra: float = 0.0       # one-off costs booked this week
    crunched: bool = False
    total_raised: float = 0.0
    profitable_weeks: int = 0
    last_new: float = 0.0
    last_churned: float = 0.0
    ended: str = ""                     # "" while playing, else the ending id
    won_paths: list[str] = field(default_factory=list)
    features: dict[str, Feature] = field(default_factory=dict)
    leads: dict[str, Lead] = field(default_factory=dict)
    runs: list[AgentRun] = field(default_factory=list)
    deals: dict[str, Deal] = field(default_factory=dict)
    investors: dict[str, Investor] = field(default_factory=dict)
    termsheets: list[TermSheet] = field(default_factory=list)
    holders: list[Holder] = field(default_factory=list)
    safes: list[Safe] = field(default_factory=list)
    loans: list[Loan] = field(default_factory=list)
    loan_offers: dict[str, LoanOffer] = field(default_factory=dict)
    hires: dict[str, Hire] = field(default_factory=dict)
    emails: list[Email] = field(default_factory=list)
    offers: list[Offer] = field(default_factory=list)
    history: list[Week] = field(default_factory=list)
    upgrades: list[str] = field(default_factory=list)
    notebook: list[str] = field(default_factory=list)      # term ids unlocked this run, in order
    used: dict[str, int] = field(default_factory=dict)      # command/feature -> times used OK
    flags: dict[str, float] = field(default_factory=dict)   # misc counters for events & debrief
    scheduled: list[list] = field(default_factory=list)     # [week, event_name, argument]
    challenges: dict[str, str] = field(default_factory=dict)  # id -> "open" | "done" | "failed"
    mission: int = 0                                        # tutorial step index
    focus: list[str] = field(default_factory=list)          # topics this run steers toward
    mastered_start: list[str] = field(default_factory=list)  # terms already mastered when the run began
    rng_state: list = field(default_factory=list)

    # --- runtime only (not saved) ---
    def __post_init__(self):
        self.rng = random.Random(self.seed)

    def flag(self, name: str, default: float = 0) -> float:
        return self.flags.get(name, default)

    def bump(self, name: str, amount: float = 1) -> float:
        self.flags[name] = self.flags.get(name, 0) + amount
        return self.flags[name]

    def has(self, upgrade: str) -> bool:
        return upgrade in self.upgrades


# --------------------------------------------------------------- save/load
def to_plain(obj):
    """dataclass -> plain dicts/lists that json can store."""
    if dataclasses.is_dataclass(obj):
        return {f.name: to_plain(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [to_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_plain(v) for k, v in obj.items()}
    return obj


def from_plain(cls, data):
    """The reverse: rebuild `cls` (using its type hints) from plain data."""
    origin = typing.get_origin(cls)
    if origin is list:
        (inner,) = typing.get_args(cls) or (typing.Any,)
        return [from_plain(inner, x) for x in data]
    if origin is dict:
        args = typing.get_args(cls)
        inner = args[1] if args else typing.Any
        return {k: from_plain(inner, v) for k, v in data.items()}
    if dataclasses.is_dataclass(cls):
        hints = typing.get_type_hints(cls)
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: from_plain(hints[k], v) for k, v in data.items() if k in known})
    return data


def save_game_dict(game: Game) -> dict:
    state = game.rng.getstate()
    game.rng_state = [state[0], list(state[1]), state[2]]
    return to_plain(game)


def load_game_dict(data: dict) -> Game:
    game = from_plain(Game, data)
    if game.rng_state:
        version, internal, gauss = game.rng_state
        game.rng.setstate((version, tuple(internal), gauss))
    return game
