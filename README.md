# By nLy

Fast username generator and availability checker for **Snapchat**, **Telegram**, **TikTok**, **X (Twitter)**, and **Tellonym**.

## Features

- Generate usernames from built-in patterns (semi2, semi3, quad, full)
- Custom pattern support (`custom:ll.l`, `custom:l_ld`, etc.)
- Check availability across 5 platforms simultaneously
- Local validation before network requests (fast filtering)
- Adaptive rate limiting with automatic backoff
- In-memory caching for duplicate checks
- Rich terminal dashboard with live stats
- Export results to CSV, JSON, TXT
- Structured logging to files
- Safe modes to avoid rate limits

## Installation

```bash
pip install .
```

Or for development:

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# Generate and check 100 semi2 usernames on Snapchat
by-nly generate --platform snapchat --pattern semi2 --limit 100

# Check usernames from a file on TikTok
by-nly check --platform tiktok --file usernames.txt

# Fast run with 20 workers on X (Twitter)
by-nly run --platform twitter --pattern quad --limit 1000 --workers 20

# Validate pattern locally without network
by-nly validate --platform telegram --pattern custom:l_ld

# Export results
by-nly export --format csv --input results.json
```

## Platforms

| Platform   | Command value  | Method                         | Rate (normal) |
|-----------|---------------|--------------------------------|---------------|
| Snapchat  | `snapchat`    | Profile page scraping          | 120/hr        |
| Telegram  | `telegram`    | MTProto API (or t.me fallback) | 30/min        |
| TikTok    | `tiktok`      | Profile page scraping          | 60/min        |
| X/Twitter | `twitter`     | Profile page + Nitter fallback | 20/min        |
| Tellonym  | `tellonym`    | Public API endpoint            | 60/min        |

## Commands

### `by-nly generate`

Generate usernames from a pattern and optionally check availability.

```bash
by-nly generate --platform tellonym --pattern semi3 --limit 500 --workers 15 --format csv
```

Options:
- `--platform, -p` - Target platform (required)
- `--pattern, -t` - Pattern type: `semi2`, `semi3`, `quad`, `full`, or `custom:ll.l`
- `--limit, -l` - Maximum usernames to generate
- `--output, -o` - Output file prefix
- `--workers, -w` - Concurrent workers (default: 10)
- `--safe-mode, -s` - Enable safe mode (`on`/`off`)
- `--check/--no-check` - Whether to check availability (default: check)
- `--format, -f` - Export format: `csv`, `json`, `txt`

### `by-nly check`

Check availability of existing usernames from a file or command line.

```bash
by-nly check --platform snapchat --file names.txt --output results --format json
by-nly check --platform telegram --usernames nlyx --usernames test_user
```

### `by-nly run`

Generate and check (same as `generate --check`).

```bash
by-nly run --platform twitter --pattern semi2 --limit 1000 --workers 20 --safe-mode on
```

### `by-nly validate`

Validate usernames locally without network requests.

```bash
by-nly validate --platform tiktok --usernames nlyx test_user n..ly
by-nly validate --platform tellonym --pattern custom:ll.l
```

### `by-nly export`

Export saved results.

```bash
by-nly export --format csv --input results.json --output final.csv
```

## Pattern System

### Built-in Patterns

| Pattern  | Templates |
|----------|-----------|
| `semi2`  | `ll`, `ld`, `dl`, `l_l`, `l.l`, `ll1`, `1ll` |
| `semi3`  | `lll`, `lld`, `ldl`, `dll`, `lll1`, `1lll`, `ll_l`, `ll.l`, `l_ll`, `l.ll`, `ll_d`, `ld_l`, `l1l`, `1l_l` |
| `quad`   | `llll`, `llld`, `ldll`, `dlll`, `ldld`, `lll1`, `1lll1`, `ll11`, `l1ll`, `lll.l`, `ll.ll`, `l.l.l.l` |
| `full`   | All of the above combined |

### Pattern Tokens

| Token | Meaning |
|-------|---------|
| `l`   | Lowercase letter (a-z) |
| `d` / `0-9` | Digit |
| `_`   | Literal underscore |
| `.`   | Literal dot |
| `-`   | Literal hyphen (Snapchat only) |

### Custom Patterns

```bash
by-nly generate --platform telegram --pattern custom:l_ld --limit 100
# Generates: a_0, a_1, ... z_9 (26 * 1 * 26 * 10 = 6760 combinations)

by-nly generate --platform tellonym --pattern custom:ll.l --limit 100
# Generates: aa.a, aa.b, ... zz.z
```

## Username Rules Per Platform

| Platform  | Allowed Chars        | Min | Max | Notes |
|-----------|---------------------|-----|-----|-------|
| Snapchat  | a-z, 0-9, `-`, `_`, `.` | 4 | 16 | Must start with letter |
| Telegram  | a-z, 0-9, `_`        | 5 | 32 | |
| TikTok    | a-z, 0-9, `_`, `.`   | 2 | 24 | No `.`/`_` at start or end |
| X/Twitter | a-z, 0-9, `_`        | 1 | 15 | |
| Tellonym  | a-z, 0-9, `_`, `.`   | 1 | 30 | |

## Configuration

Edit `config/default.yaml` for global settings.
Edit `config/platforms/<platform>.yaml` for per-platform rate limits.

### Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

- `TELEGRAM_API_ID` - Telegram API ID from my.telegram.org
- `TELEGRAM_API_HASH` - Telegram API hash from my.telegram.org

These enable faster MTProto-based checking for Telegram.

## Safety Notes

- All checkers use conservative rate limits by default
- `--safe-mode on` halves the speed for extra safety
- The tool respects 429 responses and backs off automatically
- No CAPTCHA solving, no bypassing, no claim automation
- Local validators filter invalid usernames before any network request
- Results are cached to avoid re-checking the same username

## License

MIT
