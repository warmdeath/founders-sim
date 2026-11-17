"""`dash`: a full-screen company dashboard built with Textual.

It reads the same numbers as `metrics` and redraws every second.
Press q (or Escape) to return to the shell.
"""
from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Footer, Header, Sparkline, Static

from ..game import engine, funding
from ..game.scenarios import scenario_of
from ..game.session import money
from ..game.state import STAGES


def _kv(rows: list[tuple[str, str]]) -> Table:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column(justify="right")
    for key, value in rows:
        table.add_row(key, value)
    return table


class Dashboard(App):
    CSS = """
    Grid { grid-size: 3 3; grid-gutter: 1; padding: 1; grid-rows: 1fr 1fr 7; }
    .box { border: round $accent; padding: 0 1; }
    .chart { border: round $success; padding: 0 1; height: 7; }
    Sparkline { height: 3; }
    """
    BINDINGS = [("q", "quit", "Back to the shell"), ("escape", "quit", "Back")]

    def __init__(self, session):
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Grid():
            for name in ("money", "growth", "product", "pipeline", "captable", "todo"):
                yield Static(id=name, classes="box")
            for name in ("mrr", "cash", "customers"):
                box = Static(id=name + "_box", classes="chart")
                box.border_title = {"mrr": "MRR", "cash": "Cash", "customers": "Customers"}[name]
                yield box
        yield Footer()

    def on_mount(self) -> None:
        g = self.session.game
        self.title = f"{g.company} - week {g.week}/{g.max_weeks}"
        self.sub_title = scenario_of(g).tagline
        for name in ("mrr", "cash", "customers"):
            self.query_one(f"#{name}_box", Static).mount(Sparkline([0.0], id=name))
        self.refresh_data()
        self.set_interval(1.0, self.refresh_data)

    def panel(self, name: str, title: str, body) -> None:
        widget = self.query_one(f"#{name}", Static)
        widget.border_title = title
        widget.update(body)

    def refresh_data(self) -> None:
        g = self.session.game
        m = engine.metrics(g)
        pct = lambda x: f"{x * 100:.1f}%"
        self.panel("money", "Money", _kv([
            ("Cash", money(g.cash)), ("Net burn / month", money(m["burn"])), ("Runway", engine.fmt_runway(m)),
            ("Revenue / month", money(m["revenue_month"])), ("Costs / month", money(m["costs_month"])),
            ("Gross margin", pct(m["margin"])), ("Loans", money(m["loan_balance"]))]))
        self.panel("growth", "Growth & unit economics", _kv([
            ("MRR", money(m["mrr"])), ("ARR", money(m["arr"])), ("Growth (MoM)", f"{m['growth'] * 100:+.1f}%"),
            ("Customers", f"{m['customers']:.0f}"), ("Churn / month", pct(m["churn"])),
            ("CAC", money(m["cac"]) if m["cac"] else "n/a"), ("LTV", money(m["ltv"])),
            ("LTV:CAC", f"{m['ltv_cac']:.1f}" if m["cac"] else "n/a")]))
        shipped = [f.title for f in g.features.values() if f.shipped]
        self.panel("product", "Product & you", _kv([
            ("Fit", f"{m['fit']:.0f}/100"), ("Quality", f"{m['quality']:.0f}/100"), ("Bugs live", f"{g.prod_bugs:.0f}"),
            ("Tech debt", f"{g.debt:.0f}/100"), ("Moat", f"{m['moat'] * 100:.0f}/100"),
            ("Features live", str(len(shipped))), ("Energy", f"{g.energy:.0f}/100"),
            ("Hours left", f"{g.hours:g}/{g.hours_max:g}"), ("Reputation", f"{g.reputation:.0f}/100")]))
        deals = [(d.company[:22], f"{STAGES[d.stage]} · {money(d.mrr)}") for d in g.deals.values() if d.status == "open"]
        self.panel("pipeline", "Sales pipeline", _kv(deals[:8]) if deals else Text("no open deals - `outbound`", style="dim"))
        self.panel("captable", "Cap table", _kv([(h.name[:24], pct(share)) for h, share in funding.ownership(g)][:8]
                                               + [(f"SAFE {x.investor[:16]}", money(x.amount)) for x in g.safes]))
        todo = [f"review/merge {r.id}" for r in g.runs if not r.merged and not r.discarded]
        todo += [f"term sheet {t.id}" for t in funding.open_termsheets(g)]
        todo += [f"reply: {e.subject[:28]}" for e in g.emails if e.kind == "decision" and not e.done]
        todo += [f"challenge {c}" for c, v in g.challenges.items() if v == "open"]
        self.panel("todo", "Waiting for you", Text("\n".join(todo[:9]) or "nothing - `tutor` for ideas"))
        for name in ("mrr", "cash", "customers"):
            data = [float(getattr(w, name)) for w in g.history] or [0.0]
            self.query_one(f"#{name}", Sparkline).data = data


def run_dashboard(session) -> None:
    Dashboard(session).run()
