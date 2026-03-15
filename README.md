# trk

Generic work tracker - adapt to any domain via skills.

## Install

```bash
# Install CLI
uv tool install ~/Code/trk

# Symlink trk-create skill (global)
ln -sf ~/Code/trk/.agents/skills/trk-create ~/.agents/skills/trk-create
```

## Usage

### 1. Generate domain-specific skill

```bash
/skill:trk-create
```

The skill asks questions (domain, target, terminology) and generates `.agents/skills/<domain>/SKILL.md` in your project. Pi loads it automatically.

### 2. Agent uses domain vocabulary

```bash
# For security research:
Agent: "Creating hypothesis H1"  # (not "work item")
Agent: "Recording payload"        # (not "attempt")
Agent: "Confirmed vulnerability"  # (not "confirmation")

# For data migration:
Agent: "Creating migration M1"
Agent: "Recording validation run"
Agent: "Marked as applied to production"
```

## Commands

```bash
# Core workflow
trk init <target>                          # Initialize tracking
trk show [--limit N]                       # View state (optionally limit to N recent items)
trk new --desc "..." [--priority N]        # Create work item
trk try <ID> "attempt" --result "..."      # Record attempt
trk close <ID> --conclusion "..."          # Close (didn't work)
trk confirm <ID> --conclusion "..." [--title "..."]  # Confirm success

# Search & navigate
trk grep "pattern"                         # Search everything
trk update <ID> --next "..." [--priority N]  # Update item
trk reopen <ID>                            # Reopen closed item

# Queue (enumerate before drilling)
trk qadd --desc "..." [--queue <name>]     # Add to queue
trk qbulk --queue <name>                   # Bulk-add from stdin
trk qdone <QID> [--hyp <ID>]               # Mark done
trk qshow [--queue <name>]                 # View queues

# Notes & state
trk note "observation"                     # Record timestamped note
trk last "action"                          # Update last action
trk block "reason" / trk unblock           # Mark blocked/unblock
```

## Storage

State: `~/.local/share/trk/<target>.json`

Use `--link` to symlink `./state.json` in your project:
```bash
trk init <target> --link

# Add to your .gitignore:
echo "state.json" >> .gitignore
```

## Example Workflow

```bash
# Security research
cd ~/projects/doordash-bounty
/skill:trk-create  # Generates .agents/skills/security-research/SKILL.md

trk init doordash --link
trk show
trk new --desc "XSS via postMessage" --priority 1
trk qadd --queue listeners --desc "chunk_abc.js L123 navigate handler"
trk try H1 "<script>alert(1)</script>" --result "blocked by CSP"
trk close H1 --conclusion "CSP blocks inline scripts"
```

## How It Works

```
┌─────────────────────────────┐
│  trk CLI (generic)          │
│  - Commands work same       │
│  - for any domain           │
└─────────────────────────────┘
              ↓
┌─────────────────────────────┐
│  trk-create skill (global)  │
│  - Asks domain questions    │
│  - Generates project skill  │
└─────────────────────────────┘
              ↓
┌─────────────────────────────┐
│  .agents/skills/<domain>/   │
│  - Domain vocabulary        │
│  - Pi loads automatically   │
└─────────────────────────────┘
```

One tool, unlimited domains.
