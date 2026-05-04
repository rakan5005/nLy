"""Simple scrolling dashboard - clean output."""

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
    """Prints results as scrolling colored lines."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.stats = Stats()
        self.available_usernames: list[str] = []

    def start(self) -> None:
        """Print header + checking banner."""
        self.console.print("")
        self.console.print(Text(HEADER, style="bold cyan"))
        self.console.print(Text("=" * 60, style="green"))
        self.console.print(Text("  CHECKING...", style="bold cyan"))
        self.console.print(Text("=" * 60, style="green"))
        self.console.print("")

    def stop(self) -> None:
        """Print footer."""
        self.console.print("")
        self.console.print(Text("=" * 60, style="green"))
        self.console.print("")

    def update_stats(self, stats: Stats) -> None:
        self.stats = stats

    def add_result(self, line: str, username: str, is_available: bool, status_name: str = "") -> None:
        """Print result as a scrolling line."""
        if is_available:
            self.console.print(f"  [bold green]AVAILABLE: {username}[/bold green]")
            self.available_usernames.append(username)
        elif status_name == "UNKNOWN":
            self.console.print(f"  [bold yellow]UNKNOWN: {username}[/bold yellow]")
        elif status_name == "RATE_LIMITED":
            self.console.print(f"  [bold magenta]BLOCKED: {username}[/bold magenta]")
        elif status_name == "INVALID":
            self.console.print(f"  [bold white]INVALID: {username}[/bold white]")
        else:
            self.console.print(f"  [bold red]TAKEN: {username}[/bold red]")

    def refresh_stats(self) -> None:
        pass
