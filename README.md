# By nLy

Username availability checker for **Telegram**, **Tellonym**, **Twitter (X)**, **Snapchat**, **Discord**, and **TikTok**.

## Setup (Client)

```bash
git clone <repo-url>
cd nLy
pip install -e .
```

## Update

```bash
nLy update
# or: python -m by_nly update
```

Pulls latest changes from GitHub and reinstalls automatically.

## Quick Start

```bash
# Interactive mode (arrow keys menu)
nLy

# Generate and check on Discord (no token needed)
nLy generate -p discord -t semi3 -l 100 --fast -w 20

# Generate and check on Tellonym (fast, safe)
nLy generate -p tellonym -t quad -l 500 --fast -w 15

# Check with proxy
nLy generate -p tiktok -t quad -l 50 --proxy "http://user:pass@host:port" --fast -w 10

# Test proxy
nLy test-proxy -p "http://user:pass@host:port"
```

## Platforms

| Platform   | TAKEN | AVAILABLE | Method |
|-----------|:-----:|:---------:|--------|
| Telegram  | ✅ | ✅ | `t.me/{user}` web scraping |
| Tellonym  | ✅ | ✅ | Public API + Safari impersonation |
| Twitter   | ✅ | ✅ | Bot UA scraping + Nitter fallback |
| Snapchat  | ✅ | ✅ | Profile page + Bitmoji API |
| Discord   | ✅ | ✅ | Registration endpoint |
| TikTok    | ⚠️ | ⚠️ | Needs proxy (Akamai blocks direct) |

## Discord

No `DISCORD_TOKEN` needed. Uses the registration API:
- Username taken → `TAKEN`
- Username valid → `AVAILABLE`
- Rate limited → returns `UNKNOWN`, wait and retry

TikTok requires a proxy (Akamai bot detection):
```bash
nLy generate -p tiktok -t quad -l 50 --proxy "http://..." --fast -w 10
```

## Commands

| Command | Description |
|---------|-------------|
| `nLy` | Interactive arrow-key menu |
| `nLy generate -p <platform> -t <pattern>` | Generate + check |
| `nLy check -p <platform> -u <user1> -u <user2>` | Check specific usernames |
| `nLy validate -p <platform> -u <user>` | Local validation only |
| `nLy test-proxy -p <url>` | Test proxy connection |
| `nLy export -f csv -i results.json` | Export results |
| `nLy patterns` | List all built-in patterns |
| `nLy update` | Pull latest updates from Git |
