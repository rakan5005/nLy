"""Live dashboard — shows only available usernames + periodic stats."""

import time
from rich.console import Console
from rich.text import Text
from ..models.results import Stats


HEADER = r"""
 _         _        _
| |       | |      | |
| |_      | |      | |
|  _|     | | _    | |
| |       | || |   | |
|_|        \_, |   |_|
           __/ |
          |___/
"""


class Dashboard:
    """Clean dashboard — only AVAILABLE usernames shown in real-time."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.stats = Stats()
        self.available_usernames: list[str] = []
        self._last_stats_time = time.monotonic()
        self._checked = 0
        self._avail = 0
        self._taken = 0
        self._unknown = 0
        self._blocked = 0

    def start(self) -> None:
        self.console.print("")
        self.console.print(Text(HEADER, style="bold cyan"))
        self.console.print(Text("=" * 60, style="green"))
        self.console.print(Text("  CHECKING...  (only AVAILABLE shown)", style="bold cyan"))
        self.console.print(Text("=" * 60, style="green"))
        self.console.print("")
        self._last_stats_time = time.monotonic()

    def stop(self) -> None:
        self.console.print("")
        self.console.print(Text("=" * 60, style="green"))
        self.console.print("")

    def add_result(self, line: str, username: str, is_available: bool, status_name: str = "") -> None:
        if is_available:
            self.console.print(f"  [bold green]AVAILABLE: {username}[/bold green]")
            self.available_usernames.append(username)
            self._avail += 1
        elif status_name in ("RATE_LIMITED",):
            self._blocked += 1
            self.console.print(f"  [bold magenta]BLOCKED:  {username}[/bold magenta]")
        else:
            if status_name in ("TAKEN", "taken"):
                self._taken += 1
            elif status_name in ("UNKNOWN", "unknown"):
                self._unknown += 1

        self._checked += 1
        now = time.monotonic()
        if now - self._last_stats_time >= 3:
            self._last_stats_time = now
            self.console.print(
                f"  [dim]--- Checked: {self._checked} | "
                f"[green]Avail: {self._avail}[/green] | "
                f"[red]Taken: {self._taken}[/red] | "
                f"[yellow]Unk: {self._unknown}[/yellow] | "
                f"[magenta]Blk: {self._blocked}[/magenta] ---[/dim]"
            )

    def refresh_stats(self) -> None:
        pass
