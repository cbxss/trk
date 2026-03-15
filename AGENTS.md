# trk — Agent Instructions

Generic work tracker. Domain-agnostic CLI + project-local skills for vocabulary.

## Quick Start

```bash
uv run pytest tests/ -v                                             # Run 68 tests
uv tool install --reinstall ~/Code/trk                               # Install CLI globally
ln -sf ~/Code/trk/.agents/skills/trk-create ~/.agents/skills/        # Symlink skill globally
```

## Structure

```
src/trk/
  cli.py      - All commands (597 lines)
  state.py    - Data models (309 lines)
  storage.py  - Load/save JSON (39 lines)
  display.py  - Terminal output (153 lines)
  export.py   - Markdown/JSON export (105 lines)
```

**Total: 1,210 lines. Everything in one file. Dead simple.**

## Key Patterns

**Always use timestamps:**
```python
from datetime import datetime
created = datetime.now().isoformat(timespec='seconds')  # "2026-03-13T14:58:01"
```

**Always save after modifying state:**
```python
state = _get(target)
state.hypotheses.append(h)
_save(state)  # Updates timestamp + saves
```

**Type aliases for clarity:**
```python
type HypothesisID = str  # "H1", "H2"
type ISODate = str       # "2026-03-13T14:58:01"
```

## Domain Adaptation Pattern

1. **Generic CLI** - `trk` works same for all domains
2. **Global skill** - `~/.agents/skills/trk-create/` asks questions
3. **Generated skill** - `.agents/skills/<domain>/SKILL.md` teaches vocabulary

Agent reads generated skill → uses domain terms (hypothesis vs migration vs bug).

## After Changes

```bash
uv run pytest tests/ -v                                            # Tests pass?
uv tool install --reinstall ~/Code/trk                              # Reinstall CLI
```

## Common Issues

**State not found:** `ls ~/.local/share/trk/` - run `trk init <target>` if missing  
**Tests fail:** All in `tests/test_cli.py`, `tests/test_state.py`, `tests/test_export.py`
