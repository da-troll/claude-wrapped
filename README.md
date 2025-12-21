# Claude Code Wrapped

```
  ░█████╗░██╗░░░░░░█████╗░██╗░░░██╗██████╗░███████╗
  ██╔══██╗██║░░░░░██╔══██╗██║░░░██║██╔══██╗██╔════╝
  ██║░░╚═╝██║░░░░░███████║██║░░░██║██║░░██║█████╗░░
  ██║░░██╗██║░░░░░██╔══██║██║░░░██║██║░░██║██╔══╝░░
  ╚█████╔╝███████╗██║░░██║╚██████╔╝██████╔╝███████╗
  ░╚════╝░╚══════╝╚═╝░░╚═╝░╚═════╝░╚═════╝░╚══════╝

            C O D E   W R A P P E D   2025
                    by Banker.so
```

Your year with Claude Code — Spotify Wrapped style.

## Quick Start

```bash
uvx claude-code-wrapped
```

That's it. Press `Enter` to advance through your personalized stats.

## What You'll See

**Dramatic stat reveals** — one at a time, like Spotify Wrapped:
- Total messages exchanged
- Coding sessions
- Tokens processed
- Your longest streak

**GitHub-style contribution graph** — see your coding patterns at a glance

**Your coding personality** — based on your habits:
- 🦉 Night Owl
- 🔥 Streak Master
- ⚡ Terminal Warrior
- 🎨 The Refactorer
- 🚀 Empire Builder
- 🌙 Weekend Warrior
- 🎯 Perfectionist
- 💻 Dedicated Dev

**Fun facts & bloopers** — like "You coded after midnight 47 times"

**Movie-style credits** — starring Claude Opus, featuring your top tools

## Options

```bash
claude-code-wrapped              # Full cinematic experience
claude-code-wrapped --no-animate # Skip to dashboard view
claude-code-wrapped --json       # Export stats as JSON
claude-code-wrapped 2024         # View a specific year
```

## Requirements

- Python 3.12+
- Claude Code installed (`~/.claude/` directory exists)

## How It Works

Reads your local Claude Code conversation history from `~/.claude/projects/` and aggregates:
- Message counts and timestamps
- Token usage (input, output, cache)
- Tool usage (Bash, Read, Edit, etc.)
- Model preferences (Opus, Sonnet, Haiku)
- Project activity

All data stays local. Nothing is sent anywhere.

## Author

Built by [Mert Deveci](https://x.com/gm_mertd) — Maker of [Banker.so](https://banker.so)

## License

MIT
