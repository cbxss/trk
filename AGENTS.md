# trk — Agent Instructions

Generic work tracker. Short commands, domain-agnostic state, customizable via project-local skills.

## Quick Start

```bash
# Install locally
uv tool install --reinstall ~/Code/trk

# Install global skill
cp .agents/skills/trk-create/SKILL.md ~/.pi/agent/skills/trk-create/

# Run tests
uv run pytest tests/ -v

# Test CLI
trk init test
trk new -t test --desc "Test item"
trk show -t test
```

## Project Structure

```
src/trk/
  state.py    - Data model (WorkItem, Confirmation, Attempt, Note, QueueItem)
  cli.py      - All commands (new, try, confirm, qadd, etc.)
  storage.py  - Load/save at ~/.local/share/trk/<target>.json
  display.py  - Compact show output
  export.py   - Markdown/JSON export

.agents/skills/
  trk-create/ - Skill that generates domain-specific project-local skills

tests/
  test_*.py   - 68 tests covering CLI, state, export
```

## Build & Test

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_cli.py -v

# Install/reinstall CLI
uv tool install --reinstall ~/Code/trk

# Test the CLI directly
uv run trk --help
uv run trk init demo
uv run trk new -t demo --desc "Test"
```

## Code Patterns

### Timestamps, not dates
```python
# ✅ Good - full timestamp
from datetime import datetime
created = datetime.now().isoformat(timespec='seconds')  # "2026-03-13T14:10:08"

# ❌ Bad - just date
from datetime import date
created = date.today().isoformat()  # "2026-03-13" (can't sort by time)
```

### Type safety
```python
# Use type aliases and Literal types
type HypothesisID = str              # "H1", "H2"
type ISODate = str                   # "2026-03-13T14:10:08"
type HypothesisStatus = Literal["open", "closed", "confirmed"]
```

### State modifications
```python
# Always call _save() after modifying state
state = _get(target)
state.hypotheses.append(h)
state.updated = _today()
_save(state)  # ← Don't forget this!
```

### Storage location
```python
# State files: ~/.local/share/trk/<target>.json
# NOT in project directory (unless symlinked with --link)
```

## Domain Adaptation Pattern

trk follows the pi-autoresearch pattern:

1. **Generic CLI** - trk commands work identically for any domain
2. **trk-create skill** (global) - asks questions, generates project-local skill
3. **Project-local skill** - `.agents/skills/<domain>/SKILL.md` teaches agent vocabulary

**Example flow:**
```
User: "start tracking security research"
Agent (via /skill:trk-create):
  - Asks: domain, target, terminology
  - Writes: .agents/skills/security-research/SKILL.md
  - Runs: trk init doordash
Agent (reads generated skill):
  - Says "Creating hypothesis H1" (not "work item")
  - Uses domain vocabulary naturally
```

## Adding Commands

New commands go in `src/trk/cli.py`:

```python
@app.command()
def mycommand(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    # ... other params
):
    """Command description."""
    state = _get(target)
    # ... do work
    state.updated = _today()
    _save(state)
    typer.echo("[trk] done")
```

Always:
- Include `target` param with `-t` flag
- Call `_get(target)` to load state
- Update `state.updated = _today()`
- Call `_save(state)` before returning
- Echo `[trk]` prefix on output

## Testing

When adding features:

1. Add test to `tests/test_cli.py` or `tests/test_state.py`
2. Run tests: `uv run pytest tests/ -v`
3. Test manually with CLI
4. Reinstall globally: `uv tool install --reinstall ~/Code/trk`

Test isolation:
```python
@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    # Each test gets fresh ~/.local/share/trk/
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path
```

## Security Notes

- **No secrets in state files** - stored as plain JSON in `~/.local/share/trk/`
- **User data only** - doesn't phone home, no telemetry
- **Local execution** - all commands run locally

## Skill Generation

The `trk-create` skill generates `.agents/skills/<domain>/SKILL.md` in projects.

**After modifying trk-create skill:**
```bash
# Sync to global location
cp .agents/skills/trk-create/SKILL.md ~/.pi/agent/skills/trk-create/
```

**Testing skill generation:**
```bash
cd ~/projects/test-project
# Trigger via pi: /skill:trk-create
# OR manually create .agents/skills/security-research/SKILL.md
# Verify pi loads it (check with skill listing in pi)
```

## Common Issues

**Import errors after renaming:**
```bash
# If you see "No module named 'hyp'":
grep -r "from hyp" tests/  # Find old imports
sed -i '' 's/from hyp/from trk/g' tests/*.py
```

**Tests not finding pytest:**
```bash
uv pip install pytest  # Install in venv
```

**State file not found:**
```bash
# State location: ~/.local/share/trk/<target>.json
ls -la ~/.local/share/trk/
# If missing, run: trk init <target>
```

## Commit Messages

Use conventional commits:

```
feat: add --limit flag to show recent items
fix: use timestamps instead of dates for created field
docs: update AGENTS.md with testing instructions
test: fix import from hyp → trk
refactor: rename track → trk (shorter)
```

## Release Checklist

Before releasing:
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] CLI works: `uv run trk --help`
- [ ] Skill synced: `cp .agents/skills/trk-create/SKILL.md ~/.pi/agent/skills/trk-create/`
- [ ] Global install works: `uv tool install --reinstall ~/Code/trk`
- [ ] CHANGELOG.md updated
- [ ] Git tag: `git tag v0.x.0 && git push --tags`
