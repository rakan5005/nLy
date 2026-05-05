"""Interactive TUI menu for By nLy using arrow-key navigation."""

import asyncio
import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..models.enums import Platform, SafeMode, Status
from ..generator.engine import Generator
from ..checker import get_checker
from ..rate_limiter.token_bucket import TokenBucket, AdaptiveController
from ..rate_limiter.platform_limits import get_limit
from ..cache.cache import Cache
from ..logger.logger import setup_logging, get_logger, log_result
from ..http_client import create_session
from ..proxy.manager import ProxyManager
from .dashboard import Dashboard
from .formatting import format_result_line
from .arrow_menu import arrow_select, arrow_confirm, arrow_text, arrow_number


console = Console()

def _print_line():
    console.print("[dim]-" * 60 + "[/dim]")


def _result_box(color: str, title: str, message: str):
    console.print(Panel(
        Text.assemble((title, f"bold {color}"), "\n\n", message),
        border_style=color,
        padding=(1, 2),
    ))


async def interactive_mode():
    # Header is printed by arrow_menu in every screen
    # Step 1: Platform
    platform_key = arrow_select(
        "Select platform:",
        [
            ("telegram", "Telegram"),
            ("discord", "Discord"),
            ("tellonym", "Tellonym"),
            ("snapchat", "Snapchat"),
            ("tiktok", "TikTok"),
            ("twitter", "X / Twitter"),
        ],
    )
    if platform_key is None:
        console.print("[yellow]Cancelled.[/yellow]")
        return
    platform = Platform(platform_key)

    if Platform.safety_level(platform) == "safe":
        _result_box("green", "SAFE", "No IP risk. Public API/pages.\nYou can run without proxies.")
    else:
        _result_box("red", "IP AT RISK", f"{Platform.safety_warning(platform)}\n\nTips:\n  - Use Safe Mode\n  - Use 2-5 workers\n  - Consider Tor proxy")

    # Step 2: Proxy
    use_proxy = arrow_confirm("Use proxies?", default=False)
    proxy_manager = None
    if use_proxy:
        proxy_type = arrow_select(
            "Proxy type:",
            [
                ("tor", "Tor (127.0.0.1:9050)"),
                ("free", "Free proxies (unstable)"),
                ("file", "Load from file"),
                ("single", "Single proxy URL"),
            ],
        )
        proxy_manager = ProxyManager()
        if proxy_type == "tor":
            proxy_manager.add_tor()
            console.print("[green]Tor added: socks5://127.0.0.1:9050[/green]")
        elif proxy_type == "free":
            console.print("[dim]Fetching free proxies...[/dim]")
            count = await proxy_manager.fetch_free_proxies(limit=50)
            console.print(f"[green]Fetched {count} free proxies[/green]")
        elif proxy_type == "file":
            path = arrow_text("Proxy file path:")
            count = proxy_manager.load_file(path)
            console.print(f"[green]Loaded {count} proxies[/green]")
        elif proxy_type == "single":
            url = arrow_text("Proxy URL:")
            proxy_manager.add(url)
            console.print(f"[green]Proxy added: {url}[/green]")
    else:
        console.print("[dim]Direct connection (no proxy)[/dim]\n")

    # Step 3: Pattern
    pattern = arrow_select(
        "Select pattern:",
        [
            ("semi2",  "Semi-Binary  (2-3 chars)"),
            ("semi3",  "Semi-Ternary (3-4 chars)"),
            ("quad",   "Quad         (4-5 chars)"),
            ("full",   "Full         (all)"),
            ("custom", "Custom       (your own)"),
        ],
    )
    if pattern is None:
        console.print("[yellow]Cancelled.[/yellow]")
        return

    if pattern == "custom":
        console.print("\n  Tokens: l=letter  d=digit  _=underscore  .=dot")
        console.print("  Example: lllll = 5 letters\n")
        custom = arrow_text("Enter pattern:")
        pattern = f"custom:{custom}"

    # Step 4-6: Settings
    limit_choice = arrow_select(
        "Check how many?",
        [
            ("50",   "50"),
            ("100",  "100"),
            ("500",  "500"),
            ("1000", "1,000"),
            ("5000", "5,000"),
            ("0",    "Unlimited (all templates)"),
        ],
    )
    if limit_choice is None:
        console.print("[yellow]Cancelled.[/yellow]")
        return
    limit = int(limit_choice) if int(limit_choice) > 0 else None
    workers = arrow_number("Workers?", default=20, min_val=1, max_val=50)
    safe_mode = arrow_confirm("Safe mode?", default=False)
    fast_mode = arrow_confirm("Fast mode? (no rate limit)", default=False)
    sm = SafeMode.SAFE_MODE if safe_mode else None

    # Summary
    console.print("")
    _print_line()
    limit_label = "Unlimited" if limit is None else f"{limit:,}"
    console.print(f"  Platform : {Platform.display_name(platform)}")
    console.print(f"  Pattern  : {pattern}")
    console.print(f"  Limit    : {limit_label}")
    console.print(f"  Workers  : {workers}")
    console.print(f"  Safe     : {'Yes' if safe_mode else 'No'}")
    console.print(f"  Fast     : {'Yes' if fast_mode else 'No'}")
    console.print(f"  Proxy    : {'Yes' if proxy_manager else 'No'}")
    _print_line()
    console.print("")

    if not arrow_confirm("Start checking?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    await _run_check(platform, pattern, limit, workers, sm, proxy_manager, fast_mode)


async def _create_session_with_proxy(proxy_manager: ProxyManager | None = None):
    if proxy_manager and proxy_manager.alive_count > 0:
        p = await proxy_manager.get_next()
        if p:
            return create_session(proxy=p.url)
    return create_session()


async def _run_check(platform, pattern, limit, workers, sm, proxy_manager, fast_mode: bool = False):
    setup_logging()
    logger = get_logger()

    gen = Generator(platform, pattern, limit)
    usernames = gen.generate()

    if len(usernames) == 0 and gen.stats.invalid > 0:
        min_chars = 2
        if platform in (Platform.TELEGRAM,):
            min_chars = 5
        _result_box(
            "red",
            "NO VALID USERNAMES",
            f"All {gen.stats.invalid:,} filtered out.\n\n"
            f"{Platform.display_name(platform)} requires minimum {min_chars} chars.\n"
            f"Your pattern '{pattern}' is too short.\n\n"
            f"Try: custom:{'l' * min_chars} or quad",
        )
        return

    console.print("")
    console.print(f"[green]Generated {len(usernames):,} usernames[/green]")
    limit_display = "None" if limit is None else f"{limit:,}"
    console.print(f"[dim]Platform: {Platform.display_name(platform)} | Workers: {workers} | Pattern: {pattern} | Fast: {fast_mode} | Limit: {limit_display}[/dim]")
    console.print("")

    dashboard = Dashboard(console)
    dashboard.stats = gen.stats
    cache = Cache(max_size=100000)
    
    if fast_mode:
        console.print("[bold yellow]FAST MODE: Rate limiting DISABLED[/]")
        rate_limiter = None
        adaptive = AdaptiveController(workers, workers * 4, 1.0)
    else:
        rate, burst = get_limit(platform, sm)
        rate_limiter = TokenBucket(rate, burst, 0.5 if sm else 1.0)
        adaptive = AdaptiveController(workers, workers * 2, 0.5 if sm else 1.0)

    gen.stats.start_time = time.time()
    all_results: list = []
    _unknown_streak = 0
    _warning_shown = False

    shared_session = await _create_session_with_proxy(proxy_manager)
    checker = get_checker(platform, shared_session)
    await checker.ensure_connected()

    async def worker(queue: asyncio.Queue, worker_id: int):
        nonlocal _unknown_streak, _warning_shown

        try:
            while True:
                try:
                    username = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return

                cached = cache.get(f"{platform.value}:{username}")
                if cached:
                    from ..models import results as res_mod
                    all_results.append(res_mod.CheckResult(
                        platform=platform, username=username,
                        status=Status(cached.split(":")[0]),
                        reason="cached", response_time_ms=0,
                    ))
                    queue.task_done()
                    continue

                if rate_limiter:
                    await rate_limiter.acquire()

                result = await checker.check(username)
                all_results.append(result)
                cache.set(f"{platform.value}:{username}", f"{result.status.value}:{result.reason}")

                gen.stats.checked += 1
                gen.stats.available += 1 if result.status == Status.AVAILABLE else 0
                gen.stats.taken += 1 if result.status == Status.TAKEN else 0
                gen.stats.unknown += 1 if result.status == Status.UNKNOWN else 0
                gen.stats.rate_limited += 1 if result.status == Status.RATE_LIMITED else 0

                if result.status == Status.UNKNOWN:
                    _unknown_streak += 1
                    checked = gen.stats.checked
                    if checked >= 20 and _unknown_streak >= checked * 0.5 and not _warning_shown:
                        _warning_shown = True
                        console.print("\n[bold red]WARNING: High error rate![/bold red]")
                        if proxy_manager:
                            console.print("[yellow]  Proxy may be rate-limited. Reduce workers or wait.[/yellow]")
                        else:
                            console.print("[yellow]  Platform may be blocking. Try --proxy.[/yellow]")
                        console.print("")
                else:
                    _unknown_streak = 0

                if result.status == Status.RATE_LIMITED:
                    adaptive.report_rate_limited()
                else:
                    adaptive.report_success()

                line = format_result_line(platform, username, result.status, result.reason, result.response_time_ms)
                dashboard.add_result(line, username, result.is_available, result.status.name)

                log_result(logger, platform.value, username, result.status.value, result.reason, result.response_time_ms)

                queue.task_done()
        finally:
            pass

    queue: asyncio.Queue = asyncio.Queue()
    for name in usernames:
        await queue.put(name)

    dashboard.start()

    tasks = []
    for i in range(adaptive.concurrency):
        t = asyncio.create_task(worker(queue, i))
        tasks.append(t)

    await queue.join()

    for t in tasks:
        t.cancel()

    await checker.disconnect()
    await shared_session.close()
    dashboard.stop()

    cache.save_to_disk()

    # Final results
    _print_line()
    console.print("[bold]RESULTS[/bold]")
    _print_line()
    console.print("")

    s = gen.stats
    console.print(f"  Generated : {s.total_generated:,}")
    console.print(f"  Valid     : {s.valid:,}  ({s.valid_pct():.1f}%)")
    console.print(f"  Invalid   : {s.invalid:,}  ({s.invalid_pct():.1f}%)")
    console.print(f"  Checked   : {s.checked:,}")
    console.print(f"  Available : {s.available:,}  ({s.available_pct():.1f}%)")
    console.print(f"  Taken     : {s.taken:,}  ({s.taken_pct():.1f}%)")
    console.print(f"  Unknown   : {s.unknown:,}")
    console.print(f"  Rate-Lim. : {s.rate_limited:,}")
    console.print(f"  Speed     : {s.checks_per_second:.1f}/s")
    console.print(f"  Time      : {s.elapsed_seconds:.1f}s")
    console.print("")

    avail = [r.username for r in all_results if r.is_available]
    taken = [r.username for r in all_results if r.is_taken]

    if avail:
        console.print(Panel(
            "\n".join(f"  [green]AVAILABLE: {u}[/green]" for u in avail[:50]),
            title=f"[green]AVAILABLE ({len(avail)})[/green]",
            border_style="green",
            padding=(1, 2),
        ))
    if taken:
        console.print(Panel(
            "\n".join(f"  [red]TAKEN: {u}[/red]" for u in taken[:50]),
            title=f"[red]TAKEN ({len(taken)})[/red]",
            border_style="red",
            padding=(1, 2),
        ))

    if arrow_confirm("\nSave results?", default=False):
        import json
        data = [
            {
                "platform": r.platform.value,
                "username": r.username,
                "status": r.status.value,
                "reason": r.reason,
                "timestamp": r.timestamp,
            }
            for r in all_results
        ]
        fname = f"nLy_results_{platform.value}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Saved: {fname}[/green]")

    if arrow_confirm("Run again?", default=False):
        console.print("")
        await interactive_mode()
    else:
        console.print("\n[cyan]Goodbye![/cyan]\n")
