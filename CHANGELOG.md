# Changelog

## 2026-03-13 - Initial Release

### 🎯 Generic Trk CLI

Domain-agnostic work trker with these core entities:
- **WorkItem** (H1, H2...) — thing being worked on
- **Confirmation** (C1, C2...) — successful completion
- **Attempt** — test/validation/try
- **Note** — timestamped observation
- **QueueItem** (Q1, Q2...) — work queue entry

Commands:
```bash
trk init <target>
trk new --desc "..."
trk try <ID> "attempt" --result "..."
trk close <ID> --conclusion "..."
trk confirm <ID> --conclusion "..." [--title "..."]
trk qadd --desc "..."
trk note "observation"
trk grep "pattern"
```

### 🎨 Domain Adaptation Pattern

Following the [pi-autoresearch](https://github.com/davebcn87/pi-autoresearch) pattern:

**Generic Infrastructure:**
- `trk` CLI — 100% domain-agnostic
- Stores state at `~/.local/share/trk/<target>.json`
- All commands work identically regardless of domain

**Domain Specialization:**
- `trk-create` skill (install globally) — asks domain questions
- Generates `.agents/skills/<domain>/SKILL.md` (project-local)
- Teaches agent domain vocabulary and workflows

**Example Domains:**
- `security-research` — hypothesis → vulnerability, payload attempts
- `data-migration` — migration → applied-migration, validation runs
- `debugging` — bug-theory → root-cause, reproduction steps

### 📦 Installation

```bash
# Install trk CLI globally
uv tool install ~/Code/trk

# Install trk-create skill globally
mkdir -p ~/.pi/agent/skills/trk-create
cp .agents/skills/trk-create/SKILL.md ~/.pi/agent/skills/trk-create/
```

### 🔄 Workflow

```
1. User: "start trking security research"
2. Agent (via /skill:trk-create):
   - Asks domain questions
   - Writes .agents/skills/security-research/SKILL.md
   - Calls trk init doordash
3. Agent uses domain vocabulary:
   - "Creating hypothesis H1" (not "work item")
   - "Recording payload attempt" (not "attempt")
   - "Confirmed vulnerability V1" (not "confirmation")
4. Pi loads project-local skill automatically
```

### 🏗️ Architecture

```
┌──────────────────────────────────┐
│  Skill: trk-create (global)     │
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
│  Trk CLI (generic)               │
│  trk new, trk try, trk...    │
│  ~/.local/share/trk/<t>.json     │
└──────────────────────────────────┘
```

### 🔑 Key Differences from hyp

| Feature | hyp | trk |
|---------|-----|-------|
| Domain | Security research (hardcoded) | Any domain (via skills) |
| Terminology | hypothesis, vulnerability, payload | Defined by generated skill |
| Installation | One tool, one use case | One tool, unlimited domains |
| Customization | Fork the code | Write/generate a skill |

Based on proven `hyp` architecture, but generalized via the skill pattern.
