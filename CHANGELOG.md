# Changelog

## 2026-03-13 - Initial Release

### 🎯 Generic Track CLI

Domain-agnostic work tracker with these core entities:
- **WorkItem** (H1, H2...) — thing being worked on
- **Confirmation** (C1, C2...) — successful completion
- **Attempt** — test/validation/try
- **Note** — timestamped observation
- **QueueItem** (Q1, Q2...) — work queue entry

Commands:
```bash
track init <target>
track new --desc "..."
track try <ID> "attempt" --result "..."
track close <ID> --conclusion "..."
track confirm <ID> --conclusion "..." [--title "..."]
track qadd --desc "..."
track note "observation"
track grep "pattern"
```

### 🎨 Domain Adaptation Pattern

Following the [pi-autoresearch](https://github.com/davebcn87/pi-autoresearch) pattern:

**Generic Infrastructure:**
- `track` CLI — 100% domain-agnostic
- Stores state at `~/.local/share/track/<target>.json`
- All commands work identically regardless of domain

**Domain Specialization:**
- `track-create` skill (install globally) — asks domain questions
- Generates `.agents/skills/<domain>/SKILL.md` (project-local)
- Teaches agent domain vocabulary and workflows

**Example Domains:**
- `security-research` — hypothesis → vulnerability, payload attempts
- `data-migration` — migration → applied-migration, validation runs
- `debugging` — bug-theory → root-cause, reproduction steps

### 📦 Installation

```bash
# Install track CLI globally
uv tool install ~/Code/track

# Install track-create skill globally
mkdir -p ~/.pi/agent/skills/track-create
cp .agents/skills/track-create/SKILL.md ~/.pi/agent/skills/track-create/
```

### 🔄 Workflow

```
1. User: "start tracking security research"
2. Agent (via /skill:track-create):
   - Asks domain questions
   - Writes .agents/skills/security-research/SKILL.md
   - Calls track init doordash
3. Agent uses domain vocabulary:
   - "Creating hypothesis H1" (not "work item")
   - "Recording payload attempt" (not "attempt")
   - "Confirmed vulnerability V1" (not "confirmation")
4. Pi loads project-local skill automatically
```

### 🏗️ Architecture

```
┌──────────────────────────────────┐
│  Skill: track-create (global)     │
│  Asks: domain, target, terms       │
│  Writes: .agents/skills/<d>/      │
└──────────────────────────────────┘
              ↓
   Generates domain skill
              ↓
┌──────────────────────────────────┐
│  Project-local skill               │
│  .agents/skills/<domain>/SKILL.md │
│  - Vocabulary mapping              │
│  - Workflow patterns               │
│  - Files in scope                  │
└──────────────────────────────────┘
              ↓
   Agent uses domain terms
              ↓
┌──────────────────────────────────┐
│  Track CLI (generic)               │
│  track new, track try, track...    │
│  ~/.local/share/track/<t>.json     │
└──────────────────────────────────┘
```

### 🔑 Key Differences from hyp

| Feature | hyp | track |
|---------|-----|-------|
| Domain | Security research (hardcoded) | Any domain (via skills) |
| Terminology | hypothesis, vulnerability, payload | Defined by generated skill |
| Installation | One tool, one use case | One tool, unlimited domains |
| Customization | Fork the code | Write/generate a skill |

Based on proven `hyp` architecture, but generalized via the skill pattern.
