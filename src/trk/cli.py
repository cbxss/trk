from __future__ import annotations

import json
import re
import sys  # noqa: F401 (used by qbulk stdin)
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from . import storage, display, export
from .state import Attempt, Confirmation, Hypothesis, Note, QueueItem, TrackingState

app = typer.Typer(
    name="trk",
    help="Generic work tracker - adapt to any domain",
    no_args_is_help=True,
)


def _today() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _get(target: Optional[str]) -> TrackingState:
    t = storage.resolve_target(target)
    return storage.load(t)


def _save(state: TrackingState) -> None:
    storage.save(state.target, state)
    typer.echo(f"[trk] saved: {state.target}", err=True)


# ---------------------------------------------------------------------------
# targets
# ---------------------------------------------------------------------------

@app.command()
def targets():
    """List all research targets."""
    ts = storage.list_targets()
    if not ts:
        typer.echo("No targets yet. Run: trk init <name>")
        return
    for t in ts:
        typer.echo(t)


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@app.command()
def init(
    name: str = typer.Argument(..., help="Target name"),
    link: bool = typer.Option(False, "--link", help="Symlink ./state.json to the global state file"),
):
    """Create a new research target."""
    p = storage.state_path(name)
    if p.exists():
        typer.echo(f"Target '{name}' already exists at {p}", err=True)
        raise typer.Exit(1)

    state = TrackingState(target=name, updated=_today())
    storage.save(name, state)
    typer.echo(f"[trk] initialized: {name} → {p}", err=True)

    if link:
        local = Path("state.json")
        if local.exists() or local.is_symlink():
            local.unlink()
        local.symlink_to(p)
        typer.echo(f"[trk] linked: ./state.json → {p}", err=True)


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------

@app.command()
def show(
    target: Optional[str] = typer.Option(None, "-t", "--target", help="Target name"),
    closed: bool = typer.Option(False, "--closed", help="Show closed hypothesis conclusions"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    show_confirmations: bool = typer.Option(False, "--confirmations", help="Show full confirmation details"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Show only the N most recent open items"),
):
    """Show current research state."""
    state = _get(target)
    if json_output:
        typer.echo(export.to_json(state), nl=False)
    else:
        display.show(state, show_closed=closed, show_confirmations=show_confirmations, limit=limit)


# ---------------------------------------------------------------------------
# new
# ---------------------------------------------------------------------------

@app.command()
def new(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    desc: str = typer.Option(..., "--desc", help="Hypothesis description"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Priority 1/2/3"),
    next_action: Optional[str] = typer.Option(None, "--next", help="Next action to take"),
):
    """Add a new open hypothesis."""
    state = _get(target)
    hid = state.next_hypothesis_id()
    h = Hypothesis(
        id=hid,
        desc=desc,
        status="open",
        priority=priority,
        next_action=next_action,
        created=_today(),
    )
    state.hypotheses.append(h)
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] added {hid}: {desc}")


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

@app.command()
def close(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H3)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    conclusion: str = typer.Option(..., "--conclusion", "-c", help="What you found / why closed"),
):
    """Mark a hypothesis as closed (dead end)."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    h.status = "closed"
    h.conclusion = conclusion
    h.closed = _today()
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] closed {h.id}: {conclusion}")


# ---------------------------------------------------------------------------
# confirm
# ---------------------------------------------------------------------------

@app.command()
def confirm(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H3)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    conclusion: str = typer.Option(..., "--conclusion", "-c", help="What was confirmed"),
    title: Optional[str] = typer.Option(None, "--title", help="Create a confirmation with this title"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="Severity: info/low/medium/high/critical"),
    status_val: str = typer.Option("confirmed", "--status", help="Confirmation status"),
):
    """Mark a hypothesis as confirmed, optionally creating a confirmation."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    h.status = "confirmed"
    h.conclusion = conclusion
    h.closed = _today()
    state.updated = _today()

    if title:
        if not severity:
            typer.echo("--severity required when creating a confirmation", err=True)
            raise typer.Exit(1)
        cid = state.next_confirmation_id()
        c = Confirmation(
            id=cid,
            title=title,
            severity=severity,
            status=status_val,
            from_hypothesis=h.id,
        )
        state.confirmations.append(c)
        typer.echo(f"[trk] created {cid}: {title}")

    _save(state)
    typer.echo(f"[trk] confirmed {h.id}: {conclusion}")


# ---------------------------------------------------------------------------
# confirmation
# ---------------------------------------------------------------------------

@app.command()
def confirmation(
    cid: str = typer.Argument(..., help="Confirmation ID (e.g. C1)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    status: Optional[str] = typer.Option(None, "--status", help="New status"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Notes to set"),
):
    """Update a confirmation."""
    state = _get(target)
    c = state.get_confirmation(cid)
    if not c:
        typer.echo(f"Confirmation '{cid}' not found", err=True)
        raise typer.Exit(1)
    if status:
        c.status = status
    if notes:
        c.notes = notes
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] updated {c.id}")


# ---------------------------------------------------------------------------
# last
# ---------------------------------------------------------------------------

@app.command()
def last(
    action: str = typer.Argument(..., help="Description of last action taken"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Record the last action taken."""
    state = _get(target)
    state.last_action = action
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] last_action: {action}")


# ---------------------------------------------------------------------------
# block / unblock
# ---------------------------------------------------------------------------

@app.command()
def block(
    reason: str = typer.Argument(..., help="What is blocking progress"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Mark research as blocked."""
    state = _get(target)
    state.blocked_on = reason
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] blocked: {reason}")


@app.command()
def unblock(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Clear blocked status."""
    state = _get(target)
    state.blocked_on = None
    state.updated = _today()
    _save(state)
    typer.echo("[trk] unblocked")


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# try
# ---------------------------------------------------------------------------

@app.command(name="try")
def try_cmd(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H14)"),
    payload: str = typer.Argument(..., help="What was tried (e.g. 'state=%22' or 'redirect_uri=@@evil')"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    result: Optional[str] = typer.Option(None, "--result", "-r", help="What happened"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Technique category (e.g. state_injection, redir_bypass)"),
    passed: bool = typer.Option(False, "--pass", help="Mark as pass (found something)"),
    partial: bool = typer.Option(False, "--partial", help="Mark as partial (worth noting)"),
):
    """Record a test attempt under a hypothesis."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    status = "pass" if passed else ("partial" if partial else "fail")
    a = Attempt(payload=payload, result=result, tag=tag, status=status, ts=_today())
    h.attempts.append(a)
    state.updated = _today()
    _save(state)
    sym = {"pass": "✓", "fail": "✗", "partial": "~"}[status]
    tag_str = f"[{tag}] " if tag else ""
    typer.echo(f"[trk] {h.id} {tag_str}{payload} {sym}" + (f" → {result}" if result else ""))


# ---------------------------------------------------------------------------
# tries
# ---------------------------------------------------------------------------

@app.command()
def tries(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H14)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
):
    """List all attempts recorded under a hypothesis."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    attempts = [a for a in h.attempts if (tag is None or a.tag == tag)]
    if not attempts:
        typer.echo(f"No attempts recorded for {hid}" + (f" [tag={tag}]" if tag else ""))
        return
    syms = {"pass": "✓", "fail": "✗", "partial": "~"}
    for a in attempts:
        tag_str = f"[{a.tag}] " if a.tag else ""
        result_str = f" → {a.result}" if a.result else ""
        typer.echo(f"  {syms.get(a.status, '?')} {tag_str}{a.payload}{result_str}")


# ---------------------------------------------------------------------------
# queue commands: qadd, qdone, qskip, qshow
# ---------------------------------------------------------------------------

@app.command()
def qadd(
    desc: str = typer.Option(..., "--desc", help="Queue item description"),
    queue: str = typer.Option("default", "--queue", "-q", help="Queue name (e.g. store_listeners)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Add an item to a work queue (enumerate-all-before-drilling)."""
    state = _get(target)
    qid = state.next_queue_item_id()
    item = QueueItem(id=qid, queue=queue, desc=desc, created=_today())
    if queue not in state.queues:
        state.queues[queue] = []
    state.queues[queue].append(item)
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] queued {qid}[{queue}]: {desc}")


@app.command()
def qdone(
    qid: str = typer.Argument(..., help="Queue item ID (e.g. Q3)"),
    hyp_id: Optional[str] = typer.Option(None, "--hyp", help="Link to hypothesis (e.g. H5)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    note: Optional[str] = typer.Option(None, "--note", help="Add a note to the state"),
):
    """Mark a queue item as done."""
    state = _get(target)
    item = state.get_queue_item(qid)
    if not item:
        typer.echo(f"Queue item '{qid}' not found", err=True)
        raise typer.Exit(1)
    item.status = "done"
    item.hyp_id = hyp_id
    item.done_ts = _today()
    if note:
        state.notes.append(Note(text=note, ts=_today()))
    state.updated = _today()
    _save(state)
    hyp_str = f" → {hyp_id}" if hyp_id else ""
    typer.echo(f"[trk] done {qid}{hyp_str}")


@app.command()
def qskip(
    qid: str = typer.Argument(..., help="Queue item ID (e.g. Q3)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    note: Optional[str] = typer.Option(None, "--note", help="Add a note to the state"),
):
    """Mark a queue item as skipped."""
    state = _get(target)
    item = state.get_queue_item(qid)
    if not item:
        typer.echo(f"Queue item '{qid}' not found", err=True)
        raise typer.Exit(1)
    item.status = "skipped"
    item.done_ts = _today()
    if note:
        state.notes.append(Note(text=note, ts=_today()))
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] skipped {qid}")


@app.command()
def qshow(
    queue: Optional[str] = typer.Option(None, "--queue", "-q", help="Filter by queue name"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Show work queue status."""
    state = _get(target)
    if queue:
        items = state.queues.get(queue, [])
        if not items:
            typer.echo(f"No items in queue '{queue}'")
            return
        display.show_queue(items, queue_name=queue)
    else:
        if not state.queues:
            typer.echo("No queue items")
            return
        display.show_all_queues(state.queues)


@app.command()
def qbulk(
    queue: str = typer.Option("default", "--queue", "-q", help="Queue name"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Bulk-add queue items from stdin — one description per line.

    Example:
        trk qbulk --queue listeners << 'EOF'
        chunk_abc.js L123 — if (e.data.type === 'navigate') location.href = e.data.url
        chunk_def.js L456 — el.innerHTML = event.data
        EOF
    """
    state = _get(target)
    lines = [l.rstrip() for l in sys.stdin.read().splitlines() if l.strip()]
    if not lines:
        typer.echo("No input lines — pipe descriptions via stdin", err=True)
        raise typer.Exit(1)
    if queue not in state.queues:
        state.queues[queue] = []
    added = []
    for desc in lines:
        qid = state.next_queue_item_id()
        state.queues[queue].append(QueueItem(id=qid, queue=queue, desc=desc, created=_today()))
        added.append(qid)
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] queued {', '.join(added)} → queue '{queue}'")


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

@app.command()
def update(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H3)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    next_action: Optional[str] = typer.Option(None, "--next", help="New next action"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="New priority 1/2/3"),
    desc: Optional[str] = typer.Option(None, "--desc", help="New description"),
):
    """Update fields on an existing hypothesis."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    if next_action is None and priority is None and desc is None:
        typer.echo("Nothing to update. Use --next, --priority, or --desc.", err=True)
        raise typer.Exit(1)
    if next_action is not None:
        h.next_action = next_action
    if priority is not None:
        h.priority = priority
    if desc is not None:
        h.desc = desc
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] updated {h.id}")


# ---------------------------------------------------------------------------
# grep
# ---------------------------------------------------------------------------

@app.command()
def grep(
    pattern: str = typer.Argument(..., help="Search pattern (case-insensitive regex)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Search across hypotheses, attempts, and notes."""
    state = _get(target)
    try:
        pat = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        typer.echo(f"Invalid pattern: {e}", err=True)
        raise typer.Exit(1)

    hits = []
    for h in state.hypotheses:
        if pat.search(h.desc) or pat.search(h.next_action or "") or pat.search(h.conclusion or ""):
            hits.append(f"  {h.id}[{h.status}] {h.desc}")
        for a in h.attempts:
            if pat.search(a.payload) or pat.search(a.result or ""):
                tag_str = f"[{a.tag}] " if a.tag else ""
                result_str = f" → {a.result}" if a.result else ""
                hits.append(f"  {h.id}/try {tag_str}{a.payload}{result_str}")
    for i, n in enumerate(state.notes, 1):
        if pat.search(n.text):
            hits.append(f"  note[{i}] [{n.ts}] {n.text}")
    for c in state.confirmations:
        if pat.search(c.title) or pat.search(c.notes or ""):
            notes_str = f" — {c.notes}" if c.notes else ""
            hits.append(f"  {c.id}[{c.severity}|{c.status}] {c.title}{notes_str}")

    if not hits:
        typer.echo(f"No matches for '{pattern}'")
        return
    typer.echo(f"Matches for '{pattern}':")
    for line in hits:
        typer.echo(line)


# ---------------------------------------------------------------------------
# rm
# ---------------------------------------------------------------------------

@app.command()
def reopen(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H3)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    priority: int = typer.Option(2, "--priority", "-p", help="Priority for reopened hypothesis"),
    next_action: Optional[str] = typer.Option(None, "--next", help="Next action to take"),
):
    """Reopen a closed or confirmed hypothesis."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    
    if h.status == "open":
        typer.echo(f"Hypothesis '{hid}' is already open", err=True)
        raise typer.Exit(1)
    
    h.status = "open"
    h.priority = priority
    h.closed = None
    if next_action:
        h.next_action = next_action
    state.updated = _today()
    _save(state)
    typer.echo(f"[trk] reopened {hid} (priority {priority})")


@app.command()
def rm(
    item_id: str = typer.Argument(..., help="Hypothesis or Confirmation ID (e.g. H3, C1)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Remove a hypothesis or confirmation."""
    state = _get(target)
    item_id_upper = item_id.upper()
    
    if item_id_upper.startswith("H"):
        h = state.get_hypothesis(item_id)
        if not h:
            typer.echo(f"Hypothesis '{item_id}' not found", err=True)
            raise typer.Exit(1)
        state.hypotheses.remove(h)
        state.updated = _today()
        _save(state)
        typer.echo(f"[trk] removed {item_id}")
    elif item_id_upper.startswith("C"):
        c = state.get_confirmation(item_id)
        if not c:
            typer.echo(f"Confirmation '{item_id}' not found", err=True)
            raise typer.Exit(1)
        state.confirmations.remove(c)
        state.updated = _today()
        _save(state)
        typer.echo(f"[trk] removed {item_id}")
    else:
        typer.echo(f"Invalid ID '{item_id}' — must start with H or C", err=True)
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# note / notes
# ---------------------------------------------------------------------------

@app.command()
def note(
    id_or_text: Optional[str] = typer.Argument(None, help="Hypothesis/vuln ID (e.g. H39) or note text"),
    text: Optional[str] = typer.Argument(None, help="Note text (when first arg is an ID)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    rm_index: Optional[int] = typer.Option(None, "--rm", help="Remove note by 1-based index"),
):
    """Add a free-form note to the target, or remove one with --rm <index>.

    Usage:
      trk note "text"          — global note
      trk note H39 "text"      — note linked to hypothesis H39
    """
    state = _get(target)
    if rm_index is not None:
        if rm_index < 1 or rm_index > len(state.notes):
            typer.echo(f"Note index {rm_index} out of range (1–{len(state.notes)})", err=True)
            raise typer.Exit(1)
        removed = state.notes.pop(rm_index - 1)
        state.updated = _today()
        _save(state)
        typer.echo(f"[trk] removed note: {removed.text}")
        return
    # Resolve args: `trk note H39 "text"` or `trk note "text"`
    if text is not None:
        # Two positional args: first is an ID, second is the text
        hyp_id = id_or_text.upper() if id_or_text else None
        note_text = text
    else:
        hyp_id = None
        note_text = id_or_text
    if not note_text:
        typer.echo("Provide note text or --rm <index>", err=True)
        raise typer.Exit(1)
    entry = Note(text=note_text, ts=_today(), hyp_id=hyp_id)
    state.notes.append(entry)
    state.updated = _today()
    _save(state)
    tag = f" (linked to {hyp_id})" if hyp_id else ""
    typer.echo(f"[trk] note added{tag}")


@app.command()
def notes(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Show all notes for the target."""
    state = _get(target)
    if not state.notes:
        typer.echo("No notes.")
        return
    for i, n in enumerate(state.notes, 1):
        tag = f" [{n.hyp_id}]" if n.hyp_id else ""
        typer.echo(f"  {i}. [{n.ts}]{tag} {n.text}")


@app.command(name="export")
def export_cmd(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    format: str = typer.Option("md", "--format", "-f", help="Output format: md or json"),
):
    """Export research state to stdout."""
    state = _get(target)
    if format == "json":
        typer.echo(export.to_json(state), nl=False)
    else:
        typer.echo(export.to_markdown(state), nl=False)
