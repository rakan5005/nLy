"""CLI entry point for By nLy - username generator and availability checker."""

import asyncio
import time

import click
from rich.console import Console
from rich.panel import Panel

from ..models.enums import Platform, SafeMode, Status
from ..models.results import Stats
from ..generator.engine import Generator
from ..validators import get_validator
from ..checker import get_checker
from ..rate_limiter.token_bucket import TokenBucket, AdaptiveController
from ..rate_limiter.platform_limits import get_limit
from ..cache.cache import Cache
from ..logger.logger import setup_logging, get_logger, log_result, log_stats
from ..exporters.csv_exporter import export_csv
from ..exporters.json_exporter import export_json
from ..exporters.txt_exporter import export_txt
from ..http_client import create_session
from ..proxy.manager import ProxyManager
from .dashboard import Dashboard
from .formatting import format_result_line


console = Console()
logger = None


def _show_safety_warning(platform: Platform) -> None:
    from rich.panel import Panel
    level = Platform.safety_level(platform)
    if level == "safe":
        console.print(Panel(
            f"[green]Platform:[/] [bold]{Platform.display_name(platform)}[/bold]\n"
            f"[green]Status:[/] SAFE - No IP risk, public API",
            title="[green]Security[/green]",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[yellow]Platform:[/] [bold]{Platform.display_name(platform)}[/bold]\n"
            f"[red]Risk:[/] {Platform.safety_warning(platform)}\n"
            f"[cyan]Tip:[/] Use --safe-mode on and --workers 2-5",
            title="[red]Security Warning[/red]",
            border_style="red",
        ))


PROXY_OPTIONS = [
    click.option("--tor", is_flag=True, default=False, help="Route through Tor (requires Tor service on 127.0.0.1:9050)"),
    click.option("--free-proxies", is_flag=True, default=False, help="Auto-fetch free proxies from proxyscrape"),
    click.option("--proxy", default=None, help="Single proxy (e.g. http://user:pass@host:port or socks5://host:port)"),
    click.option("--proxy-file", type=click.Path(exists=True), default=None, help="File with one proxy per line"),
    click.option("--no-health-check", is_flag=True, default=False, help="Skip proxy health check (use proxies as-is)"),
    click.option("--fast", is_flag=True, default=False, help="Disable rate limiting for maximum speed"),
    click.option("--verbose", "-v", is_flag=True, default=False, help="Show detailed response info for each check"),
]


def add_proxy_options(func):
    for option in reversed(PROXY_OPTIONS):
        func = option(func)
    return func


async def _setup_proxy_manager(tor: bool, free_proxies: bool, proxy: str | None, proxy_file: str | None, no_health_check: bool = False) -> ProxyManager:
    pm = ProxyManager()

    if tor:
        pm.add_tor()
        console.print("[cyan]Tor proxy added (socks5://127.0.0.1:9050)[/]")

    if proxy:
        pm.add(proxy)
        console.print(f"[cyan]Custom proxy added: {proxy}[/]")

    if proxy_file:
        count = pm.load_file(proxy_file)
        console.print(f"[cyan]Loaded {count} proxies from {proxy_file}[/]")
        if no_health_check and count > 0:
            console.print("[yellow]Skipping health check (--no-health-check)[/]")

    if free_proxies:
        console.print("[cyan]Fetching free proxies...[/]")
        count = await pm.fetch_free_proxies(limit=50, health_check=not no_health_check)
        if count > 0:
            if no_health_check:
                console.print(f"[cyan]Fetched {count} free proxies (no health check)[/]")
            else:
                console.print(f"[cyan]Fetched {count} free proxies, testing...[/]")
                await asyncio.sleep(0.5)
        else:
            console.print("[yellow]No free proxies fetched[/]")

    if pm.alive_count > 0:
        console.print(f"[green]Proxies ready: {pm.alive_count} alive / {pm.total_count} total[/]")
    elif pm.total_count > 0:
        if no_health_check:
            console.print(f"[green]Proxies loaded: {pm.total_count} total (health check skipped)[/]")
        else:
            console.print("[yellow]Proxies loaded but all failed health check[/]")

    return pm


async def _create_session(proxy_manager: ProxyManager | None = None):
    """Create a curl_cffi session with optional proxy."""
    if proxy_manager and proxy_manager.alive_count > 0:
        p = await proxy_manager.get_next()
        if p:
            return create_session(proxy=p.url)
    return create_session()


@click.group(invoke_without_command=True)
@click.version_option(version="1.0.0", prog_name="By nLy")
@click.pass_context
def main(ctx):
    """By nLy - Fast username generator & availability checker.

    Platforms: snapchat, telegram, tiktok, twitter, tellonym, discord
    """
    if ctx.invoked_subcommand is None:
        # No subcommand given - run interactive mode
        from .interactive import interactive_mode
        asyncio.run(interactive_mode())


@main.command()
@click.option("--platform", "-p", required=True, type=click.Choice([p.value for p in Platform]), help="Target platform")
@click.option("--pattern", "-t", required=True, help="Pattern type (semi2, semi3, quad, full, custom:ll.l, l_ld, etc.)")
@click.option("--limit", "-l", type=int, default=None, help="Max usernames to generate")
@click.option("--output", "-o", default=None, help="Output file prefix")
@click.option("--workers", "-w", type=int, default=10, help="Concurrent workers")
@click.option("--safe-mode", "-s", default="off", type=click.Choice(["on", "off"]), help="Enable safe mode (half speed)")
@click.option("--check/--no-check", default=True, help="Check availability after generation")
@click.option("--format", "-f", "fmt", default=None, type=click.Choice(["csv", "json", "txt"]), help="Export format")
@add_proxy_options
def generate(platform, pattern, limit, output, workers, safe_mode, check, fmt, tor, free_proxies, proxy, proxy_file, no_health_check, fast, verbose):
    """Generate usernames from a pattern and optionally check availability."""
    asyncio.run(_generate(platform, pattern, limit, output, workers, safe_mode, check, fmt, tor, free_proxies, proxy, proxy_file, no_health_check, fast, verbose))


@main.command()
@click.option("--platform", "-p", required=True, type=click.Choice([p.value for p in Platform]), help="Target platform")
@click.option("--file", "-f", "infile", type=click.Path(exists=True), default=None, help="Read usernames from file")
@click.option("--usernames", "-u", multiple=True, default=None, help="Usernames to check")
@click.option("--output", "-o", default=None, help="Export file prefix")
@click.option("--workers", "-w", type=int, default=10, help="Concurrent workers")
@click.option("--safe-mode", "-s", default="off", type=click.Choice(["on", "off"]), help="Enable safe mode")
@click.option("--format", "fmt", default=None, type=click.Choice(["csv", "json", "txt"]), help="Export format")
@add_proxy_options
def check(platform, infile, usernames, output, workers, safe_mode, fmt, tor, free_proxies, proxy, proxy_file, no_health_check, fast, verbose):
    """Check availability of existing usernames."""
    asyncio.run(_check(platform, infile, list(usernames) if usernames else None, output, workers, safe_mode, fmt, tor, free_proxies, proxy, proxy_file, no_health_check, fast, verbose))


@main.command()
@click.option("--platform", "-p", required=True, type=click.Choice([p.value for p in Platform]), help="Target platform")
@click.option("--pattern", "-t", required=True, help="Pattern type or custom:template")
@click.option("--limit", "-l", type=int, default=None, help="Max to generate")
@click.option("--workers", "-w", type=int, default=10, help="Concurrent workers")
@click.option("--safe-mode", "-s", default="off", type=click.Choice(["on", "off"]), help="Enable safe mode")
@click.option("--output", "-o", default=None, help="Output prefix")
@click.option("--format", "fmt", default=None, type=click.Choice(["csv", "json", "txt"]), help="Export format")
@add_proxy_options
def run(platform, pattern, limit, workers, safe_mode, output, fmt, tor, free_proxies, proxy, proxy_file, no_health_check, fast, verbose):
    """Generate and check (alias for generate --check)."""
    asyncio.run(_generate(platform, pattern, limit, output, workers, safe_mode, True, fmt, tor, free_proxies, proxy, proxy_file, no_health_check, fast, verbose))


@main.command()
@click.option("--platform", "-p", required=True, type=click.Choice([p.value for p in Platform]), help="Target platform")
@click.option("--pattern", "-t", default=None, help="Pattern to validate against")
@click.option("--usernames", "-u", multiple=True, default=None, help="Usernames to validate")
def validate(platform, pattern, usernames):
    """Validate usernames locally without network requests."""
    plat = Platform(platform)
    validator = get_validator(plat)

    names = list(usernames) if usernames else []
    if pattern:
        from ..generator.pattern_engine import custom_pattern_to_template, expand_pattern, get_charset, get_patterns
        try:
            templates = get_patterns(pattern)
        except ValueError:
            templates = [pattern]
        charset = get_charset(plat)
        for tmpl in templates:
            if tmpl.startswith("custom:"):
                tmpl = custom_pattern_to_template(tmpl)
            names.extend(expand_pattern(tmpl, charset)[:1000])

    if not names:
        console.print("[red]No usernames provided.[/]")
        return

    for name in names:
        result = validator.validate(name)
        if result.is_valid:
            console.print(f"[green][+] {name:<20}[/green]")
        else:
            reason_short = result.reason[:30] + "..." if len(result.reason) > 30 else result.reason
            console.print(f"[yellow][!] {name:<20}[/yellow] [dim]{reason_short}[/]")


@main.command()
def patterns():
    """List all built-in pattern types with examples."""
    from ..generator.pattern_engine import PATTERN_SETS, pattern_size, get_charset
    from rich.table import Table

    table = Table(title="[bold cyan]Built-in Patterns[/bold cyan]", border_style="cyan")
    table.add_column("Pattern", style="bold green", no_wrap=True)
    table.add_column("Examples", style="white")
    table.add_column("Est. Combos", style="dim", justify="right")

    charset = get_charset(Platform.TELEGRAM)  # use generic charset for estimates
    for name, tmpl_list in PATTERN_SETS.items():
        examples = tmpl_list[:4]
        total_combos = sum(pattern_size(t, charset) for t in examples[:4])
        table.add_row(
            name,
            ", ".join(examples),
            f"{total_combos:,}",
        )

    console.print(table)
    console.print("\n[dim]Tokens:[/] [green]l[/]=letter  [green]d[/]=digit  [green]_[/]=underscore  [green].[/]=dot")
    console.print("[dim]Custom:[/] [cyan]by-nly generate -p telegram -t custom:ll.l_l[/cyan]")


@main.command()
@click.option("--proxy", "-p", required=True, help="Proxy URL to test (e.g. http://user:pass@host:port)")
@click.option("--timeout", default=10, help="Request timeout in seconds")
def test_proxy(proxy, timeout):
    """Test if a proxy works and show your external IP."""
    asyncio.run(_test_proxy(proxy, timeout))


async def _test_proxy(proxy_url: str, timeout: int):
    console.print(f"\n[cyan]Testing proxy:[/] [bold]{proxy_url}[/bold]\n")
    
    try:
        session = create_session(proxy=proxy_url)
        start = time.monotonic()
        
        async with session.get("https://httpbin.org/ip", timeout=timeout) as resp:
            elapsed = (time.monotonic() - start) * 1000
            if resp.status == 200:
                data = await resp.json()
                origin = data.get("origin", "unknown")
                console.print(Panel(
                    f"[green]Proxy is WORKING![/]\n\n"
                    f"[cyan]External IP:[/] [bold]{origin}[/bold]\n"
                    f"[cyan]Response time:[/] {elapsed:.0f} ms\n"
                    f"[cyan]HTTP Status:[/] {resp.status}",
                    title="[green]Proxy Test Result[/green]",
                    border_style="green",
                ))
            else:
                console.print(Panel(
                    f"[yellow]Proxy responded but with status {resp.status}[/]\n"
                    f"Response time: {elapsed:.0f} ms",
                    title="[yellow]Proxy Warning[/yellow]",
                    border_style="yellow",
                ))
        await session.close()
    except Exception as e:
        console.print(Panel(
            f"[red]Proxy FAILED[/]\n\n"
            f"Error: {str(e)[:200]}\n\n"
            f"[dim]Common causes:\n"
            f"- Wrong proxy format (use: http://user:pass@host:port)\n"
            f"- Proxy is dead or blocked\n"
            f"- Firewall blocking the connection[/dim]",
            title="[red]Proxy Test Failed[/red]",
            border_style="red",
        ))


@main.command()
@click.option("--format", "-f", "fmt", required=True, type=click.Choice(["csv", "json", "txt"]), help="Export format")
@click.option("--input", "-i", "infile", type=click.Path(exists=True), required=True, help="Input results JSON file")
@click.option("--output", "-o", default=None, help="Output file/dir")
def export(fmt, infile, output):
    """Export results to CSV, JSON, or TXT."""
    import json
    from ..models.results import CheckResult

    with open(infile, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = [
        CheckResult(
            platform=Platform(r["platform"]),
            username=r["username"],
            status=Status(r["status"]),
            reason=r.get("reason", ""),
            response_time_ms=r.get("response_time_ms", 0),
            timestamp=r.get("timestamp", ""),
        )
        for r in data
    ]

    if fmt == "csv":
        out = output or "results.csv"
        export_csv(results, out)
    elif fmt == "json":
        out = output or "results.json"
        export_json(results, out)
    elif fmt == "txt":
        out = output or "results_txt"
        export_txt(results, out)

    console.print(f"[green]Exported to: {out}[/]")


async def _generate(
    platform_str, pattern, limit, output, workers, safe_mode, do_check, fmt,
    tor, free_proxies, proxy, proxy_file, no_health_check: bool = False,
    fast: bool = False, verbose: bool = False,
) -> None:
    global logger
    setup_logging()
    logger = get_logger()

    platform = Platform(platform_str)
    sm = SafeMode.SAFE_MODE if safe_mode == "on" else None

    _show_safety_warning(platform)

    proxy_manager = None
    if tor or free_proxies or proxy or proxy_file:
        proxy_manager = await _setup_proxy_manager(tor, free_proxies, proxy, proxy_file, no_health_check)

    gen = Generator(platform, pattern, limit)
    usernames = gen.generate()

    from rich.panel import Panel
    total_combos = gen.stats.total_generated
    valid_count = len(usernames)
    invalid_count = gen.stats.invalid

    if valid_count == 0 and invalid_count > 0:
        console.print(Panel(
            f"[cyan]Platform:[/] [bold]{Platform.display_name(platform)}[/bold]\n"
            f"[cyan]Pattern:[/] [bold]{pattern}[/bold]\n"
            f"[dim]Pattern combos:[/] {total_combos:,}\n"
            f"[red]All {invalid_count:,} filtered out[/] - too short for {Platform.display_name(platform)}\n"
            f"[yellow]Tip:[/] Use longer pattern (semi3, quad, custom:lllll)",
            title="[bold red]Nothing to Check[/bold red]",
            border_style="red",
        ))
        if not do_check:
            return
    else:
        console.print(Panel(
            f"[cyan]Platform:[/] [bold]{Platform.display_name(platform)}[/bold]\n"
            f"[cyan]Pattern:[/] [bold]{pattern}[/bold]\n"
            f"[dim]Pattern combos:[/] {total_combos:,}\n"
            f"[green]Valid usernames:[/] {valid_count:,}\n"
            f"[red]Filtered invalid:[/] {invalid_count:,}\n"
            f"[cyan]To Check:[/] {valid_count:,} usernames",
            title="[bold]Generation Complete[/bold]",
            border_style="cyan",
        ))

    if not do_check:
        for name in usernames:
            console.print(f"  {name}")
        return

    dashboard = Dashboard(console)
    dashboard.stats = gen.stats
    cache = Cache(max_size=100000)
    
    if fast:
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

    async def worker(queue: asyncio.Queue, worker_id: int):
        nonlocal _unknown_streak, _warning_shown
        session = await _create_session(proxy_manager)
        checker = get_checker(platform, session)
        await checker.ensure_connected()

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

                if verbose:
                    console.print(f"  [dim]{username:<15} -> {result.status.name:<12} ({result.reason[:40]}) {result.response_time_ms:.0f}ms[/dim]")

                line = format_result_line(platform, username, result.status, result.reason, result.response_time_ms)
                dashboard.add_result(line, username, result.is_available, result.status.name)

                log_result(logger, platform.value, username, result.status.value, result.reason, result.response_time_ms)

                queue.task_done()
        finally:
            await checker.disconnect()
            await session.close()

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

    dashboard.stop()

    cache.save_to_disk()

    s = gen.stats
    from .formatting import format_stats_table
    console.print(format_stats_table(
        s.total_generated, s.valid, s.invalid, s.checked,
        s.available, s.taken, s.unknown, s.rate_limited,
        s.checks_per_second, s.elapsed_seconds,
    ))
    console.print(f"  [dim]Cache: {cache.hits} hits, {cache.misses} misses[/]")

    if fmt or output:
        prefix = output or f"by_nly_{platform.value}"
        if fmt == "csv":
            export_csv(all_results, f"{prefix}.csv")
        elif fmt == "json":
            export_json(all_results, f"{prefix}.json")
        elif fmt == "txt":
            export_txt(all_results, f"{prefix}_txt")
        elif not fmt and output:
            export_json(all_results, f"{prefix}.json")
        console.print("\n[green]Exported results.[/]")

    avail = [r.username for r in all_results if r.is_available]
    if avail:
        console.print(f"\n[bold green]Available usernames ({len(avail)}):[/]")
        for u in avail[:100]:
            console.print(f"  {u}")
        if len(avail) > 100:
            console.print(f"  [dim]... and {len(avail) - 100} more[/]")

    log_stats(logger, f"Complete: {s.available} available out of {s.checked} checked")


async def _check(
    platform_str, infile, usernames, output, workers, safe_mode, fmt,
    tor, free_proxies, proxy, proxy_file, no_health_check: bool = False,
    fast: bool = False, verbose: bool = False,
) -> None:
    global logger
    setup_logging()
    logger = get_logger()

    platform = Platform(platform_str)
    sm = SafeMode.SAFE_MODE if safe_mode == "on" else None

    _show_safety_warning(platform)

    names: list[str] = []
    if infile:
        with open(infile, "r", encoding="utf-8") as f:
            names = [line.strip() for line in f if line.strip()]
    if usernames:
        names.extend(usernames)

    if not names:
        console.print("[red]No usernames provided.[/]")
        return

    proxy_manager = None
    if tor or free_proxies or proxy or proxy_file:
        proxy_manager = await _setup_proxy_manager(tor, free_proxies, proxy, proxy_file, no_health_check)

    validator = get_validator(platform)
    valid_names = []
    for name in names:
        vr = validator.validate(name)
        if vr.is_valid:
            valid_names.append(name)
        else:
            console.print(format_result_line(platform, name, Status.INVALID, vr.reason))

    console.print(f"\n[cyan]Valid for checking: {len(valid_names):,} / {len(names):,}[/]\n")

    dashboard = Dashboard(console)
    stats = Stats()
    stats.total_generated = len(names)
    stats.valid = len(valid_names)
    stats.invalid = len(names) - len(valid_names)
    stats.start_time = time.time()
    dashboard.stats = stats
    cache = Cache()
    
    if fast:
        console.print("[bold yellow]FAST MODE: Rate limiting DISABLED[/]")
        rate_limiter = None
        adaptive = AdaptiveController(workers, workers * 4, 1.0)
    else:
        rate, burst = get_limit(platform, sm)
        rate_limiter = TokenBucket(rate, burst, 0.5 if sm else 1.0)
        adaptive = AdaptiveController(workers, workers * 2, 0.5 if sm else 1.0)
    all_results: list = []
    _unknown_streak = 0
    _warning_shown = False

    async def worker(queue: asyncio.Queue, worker_id: int):
        nonlocal _unknown_streak, _warning_shown
        session = await _create_session(proxy_manager)
        checker = get_checker(platform, session)
        await checker.ensure_connected()

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
                        status=Status(cached.split(":")[0]), reason="cached",
                    ))
                    queue.task_done()
                    continue

                if rate_limiter:
                    await rate_limiter.acquire()
                result = await checker.check(username)
                all_results.append(result)
                cache.set(f"{platform.value}:{username}", f"{result.status.value}:{result.reason}")

                stats.checked += 1
                stats.available += 1 if result.status == Status.AVAILABLE else 0
                stats.taken += 1 if result.status == Status.TAKEN else 0
                stats.unknown += 1 if result.status == Status.UNKNOWN else 0
                stats.rate_limited += 1 if result.status == Status.RATE_LIMITED else 0

                if result.status == Status.UNKNOWN:
                    _unknown_streak += 1
                    checked = stats.checked
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

                if verbose:
                    console.print(f"  [dim]{username:<15} -> {result.status.name:<12} ({result.reason[:40]}) {result.response_time_ms:.0f}ms[/dim]")

                line = format_result_line(platform, username, result.status, result.reason, result.response_time_ms)
                dashboard.add_result(line, username, result.is_available, result.status.name)

                log_result(logger, platform.value, username, result.status.value, result.reason, result.response_time_ms)
                queue.task_done()
        finally:
            await checker.disconnect()
            await session.close()

    queue: asyncio.Queue = asyncio.Queue()
    for name in valid_names:
        await queue.put(name)

    dashboard.start()

    tasks = []
    for i in range(adaptive.concurrency):
        t = asyncio.create_task(worker(queue, i))
        tasks.append(t)

    await queue.join()

    for t in tasks:
        t.cancel()

    dashboard.stop()

    from .formatting import format_stats_table
    console.print(format_stats_table(
        stats.total_generated, stats.valid, stats.invalid, stats.checked,
        stats.available, stats.taken, stats.unknown, stats.rate_limited,
        stats.checks_per_second, stats.elapsed_seconds,
    ))

    if fmt or output:
        prefix = output or f"by_nly_{platform.value}"
        if fmt == "csv":
            export_csv(all_results, f"{prefix}.csv")
        elif fmt == "json":
            export_json(all_results, f"{prefix}.json")
        elif fmt == "txt":
            export_txt(all_results, f"{prefix}_txt")
        elif not fmt and output:
            export_json(all_results, f"{prefix}.json")
        console.print("\n[green]Exported results.[/]")

    avail = [r.username for r in all_results if r.is_available]
    if avail:
        console.print(f"\n[bold green]Available ({len(avail)}):[/]")
        for u in avail[:100]:
            console.print(f"  {u}")
        if len(avail) > 100:
            console.print(f"  [dim]... and {len(avail) - 100} more[/]")


if __name__ == "__main__":
    main()
