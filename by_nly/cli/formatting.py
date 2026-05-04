"""Terminal output formatting with vivid color support."""

from ..models.enums import Platform, Status

STATUS_COLORS: dict[Status, str] = {
    Status.AVAILABLE: "bold green",
    Status.TAKEN: "bold red",
    Status.INVALID: "bold yellow",
    Status.UNKNOWN: "bold white",
    Status.RATE_LIMITED: "bold magenta",
}

STATUS_ICONS: dict[Status, str] = {
    Status.AVAILABLE: "[OK]",
    Status.TAKEN: "[XX]",
    Status.INVALID: "[!]",
    Status.UNKNOWN: "[?]",
    Status.RATE_LIMITED: "[RL]",
}

PLATFORM_LABELS: dict[Platform, str] = {
    Platform.SNAPCHAT: "SNAPCHAT",
    Platform.TELEGRAM: "TELEGRAM",
    Platform.TIKTOK: "TIKTOK",
    Platform.TWITTER: "TWITTER",
    Platform.TELLONYM: "TELLONYM",
    Platform.DISCORD: "DISCORD",
}


def format_result_line(
    platform: Platform,
    username: str,
    status: Status,
    reason: str = "",
    response_time_ms: float = 0.0,
) -> str:
    color = STATUS_COLORS.get(status, "white")
    icon = STATUS_ICONS.get(status, "❓")
    platform_name = PLATFORM_LABELS.get(platform, platform.value.upper())

    base = f"[{color}]{icon} {status.name.upper():<12}[/] [{color}]{platform_name:<10}[/] [{color}]{username:<20}[/]"
    if response_time_ms > 0:
        base += f" [dim]{response_time_ms:>5.0f}ms[/]"
    if reason:
        reason_short = reason[:25] + "..." if len(reason) > 25 else reason
        base += f" [dim]{reason_short}[/]"
    return base


def format_stats_table(
    total: int, valid: int, invalid: int, checked: int,
    available: int, taken: int, unknown: int, rate_limited: int,
    checks_per_sec: float, elapsed: float,
) -> str:
    lines = [
        "",
        "[bold cyan]+--------------------------------------------------+[/bold cyan]",
        "[bold cyan]|              FINAL STATISTICS                    |[/bold cyan]",
        "[bold cyan]+--------------------------------------------------+[/bold cyan]",
        "",
        f"  [cyan]Generated:[/cyan]  {total:>8,}",
        f"  [green]Valid:[/green]       {valid:>8,}  [dim]({valid / total * 100:5.1f}%)[/]" if total else f"  [green]Valid:[/green]       {valid:>8,}",
        f"  [red]Invalid:[/red]     {invalid:>8,}  [dim]({invalid / total * 100:5.1f}%)[/]" if total else f"  [red]Invalid:[/red]     {invalid:>8,}",
        f"  [cyan]Checked:[/cyan]     {checked:>8,}",
        f"  [bold green]Available:[/bold green]   {available:>8,}  [dim]({available / checked * 100:5.1f}%)[/]" if checked else f"  [bold green]Available:[/bold green]   {available:>8,}",
        f"  [bold red]Taken:[/bold red]       {taken:>8,}  [dim]({taken / checked * 100:5.1f}%)[/]" if checked else f"  [bold red]Taken:[/bold red]       {taken:>8,}",
        f"  [yellow]Unknown:[/yellow]     {unknown:>8,}",
        f"  [magenta]Rate-Limited:[/magenta] {rate_limited:>8,}",
        f"  [cyan]Speed:[/cyan]        {checks_per_sec:>8.1f} checks/sec",
        f"  [cyan]Elapsed:[/cyan]     {elapsed:>8.1f} seconds",
        "",
    ]
    return "\n".join(lines)
