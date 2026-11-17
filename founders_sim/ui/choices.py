"""Arrow-key selection list (used for dialogue answers in pitches,
negotiations, events). Built on prompt_toolkit so it works in any terminal."""
from __future__ import annotations

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl


def arrow_select(options: list[str], default: int = 0) -> int:
    """Show `options`; ↑/↓ (or j/k) move, Enter confirms. Returns the index."""
    state = {"index": default}

    def render():
        lines = []
        for i, option in enumerate(options):
            if i == state["index"]:
                lines.append(("reverse bold", f" ❯ {option} \n"))
            else:
                lines.append(("", f"   {option}\n"))
        lines.append(("fg:gray", "   (↑/↓ to move, Enter to choose)"))
        return lines

    keys = KeyBindings()

    @keys.add("up")
    @keys.add("k")
    def _up(event):
        state["index"] = (state["index"] - 1) % len(options)

    @keys.add("down")
    @keys.add("j")
    @keys.add("tab")
    def _down(event):
        state["index"] = (state["index"] + 1) % len(options)

    @keys.add("enter")
    def _enter(event):
        event.app.exit(result=state["index"])

    @keys.add("c-c")
    def _cancel(event):
        event.app.exit(result=state["index"])

    for digit in range(1, min(9, len(options)) + 1):
        @keys.add(str(digit))
        def _jump(event, d=digit):
            state["index"] = d - 1

    app = Application(layout=Layout(Window(FormattedTextControl(render), height=len(options) + 1)),
                      key_bindings=keys, full_screen=False, erase_when_done=True)
    return app.run()
