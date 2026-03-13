# trk — Agent Instructions

Generic work tracker. Domain-agnostic CLI + project-local skills for vocabulary.

## Quick Start

```bash
uv run pytest tests/ -v              # Run 68 tests
uv tool install --reinstall ~/Code/trk  # Install CLI globally
cp .agents/skills/trk-create/SKILL.md ~/.pi/agent/skills/trk-create/  # Sync skill
```

## Structure

```
src/trk/
  state.py    - Data model (WorkItem, Confirmation, Attempt, Note, Queue)
  cli.py      - Commands (new, try, confirm, qadd, show, grep...)
  storage.py  - Load/save at ~/.local/share/trk/<target>.json
  display.py  - Show output
  export.py   - Markdown/JSON export

.agents/skills/trk-create/  - Generates domain-specific skills in projects
tests/                       - 68 tests
```

## Key Patterns

**Always use timestamps:**
```python
from datetime import datetime
created = datetime.now().isoformat(timespec='seconds')  # "2026-03-13T14:10:08"
```

**Always save after modifying state:**
```python
state = _get(target)
state.hypotheses.append(h)
state.updated = _today()
_save(state)  # Don't forget!
```

**Type aliases for clarity:**
```python
type HypothesisID = str  # "H1", "H2"
type ISODate = str       # "2026-03-13T14:10:08"
```

## Adding Commands

```python
@app.command()
def mycommand(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Description."""
    state = _get(target)
    # do work
    state.updated = _today()
    _save(state)
    typer.echo("[trk] done")
```

## Domain Adaptation Pattern

1. **Generic CLI** - `trk` works same for all domains
2. **Global skill** - `~/.pi/agent/skills/trk-create/` asks questions
3. **Generated skill** - `.agents/skills/<domain>/SKILL.md` in project teaches vocabulary

Agent reads generated skill → uses domain terms (hypothesis vs migration vs bug).

## After Changes

```bash
uv run pytest tests/ -v                    # Tests pass?
uv tool install --reinstall ~/Code/trk     # Reinstall CLI
cp .agents/skills/trk-create/SKILL.md ~/.pi/agent/skills/trk-create/  # Sync skill
```

## Common Issues

**Import errors:** `grep -r "from hyp" tests/` then fix to `from trk`  
**Tests fail:** `uv pip install pytest` in venv  
**State not found:** `ls ~/.local/share/trk/` - run `trk init <target>` if missing
