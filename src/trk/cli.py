"""Main CLI application."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import storage, display, export
from .commands import hypotheses, queue, notes
from .commands.shared import handle_errors, get_state
from .exceptions import TargetAlreadyExists

app = typer.Typer(
    name="trk",
    help="Generic work tracker - adapt to any domain",
    no_args_is_help=True,
)


# ── Meta commands ──────────────────────────────────────────────────────────


@app.command()
def targets():
    """List all research targets."""
    ts = storage.list_targets()
    if not ts:
        typer.echo("No targets yet. Run: trk init <name>")
        return
    for t in ts:
        typer.echo(t)


@app.command()
@handle_errors
def init(
    name: str = typer.Argument(..., help="Target name"),
    link: bool = typer.Option(False, "--link", help="Symlink ./state.json to the global state file"),
):
    """Create a new research target."""
    from datetime import datetime
    from .state import TrackingState
    
    p = storage.state_path(name)
    if p.exists():
        raise TargetAlreadyExists(name, str(p))

    state = TrackingState(target=name, updated=datetime.now().isoformat(timespec='seconds'))
    storage.save(name, state)
    typer.echo(f"[trk] initialized: {name} → {p}", err=True)

    if link:
        local = Path("state.json")
        if local.exists() or local.is_symlink():
            local.unlink()
        local.symlink_to(p)
        typer.echo(f"[trk] linked: ./state.json → {p}", err=True)


@app.command()
@handle_errors
def show(
    target: Optional[str] = typer.Option(None, "-t", "--target", help="Target name"),
    closed: bool = typer.Option(False, "--closed", help="Show closed hypothesis conclusions"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    show_confirmations: bool = typer.Option(False, "--confirmations", help="Show full confirmation details"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Show only the N most recent open items"),
):
    """Show current research state."""
    state = get_state(target)
    if json_output:
        typer.echo(export.to_json(state), nl=False)
    else:
        display.show(state, show_closed=closed, show_confirmations=show_confirmations, limit=limit)


@app.command(name="export")
@handle_errors
def export_cmd(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    format: str = typer.Option("md", "--format", "-f", help="Output format: md or json"),
):
    """Export research state to stdout."""
    state = get_state(target)
    if format == "json":
        typer.echo(export.to_json(state), nl=False)
    else:
        typer.echo(export.to_markdown(state), nl=False)


@app.command()
@handle_errors
def grep(
    pattern: str = typer.Argument(..., help="Search pattern (case-insensitive)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Search across hypotheses, attempts, and notes."""
    state = get_state(target)
    pattern_lower = pattern.lower()
    
    hits = []
    
    # Search hypotheses
    for h in state.hypotheses:
        if pattern_lower in h.desc.lower():
            hits.append(f"{h.id}[{h.status}] {h.desc}")
        if h.next_action and pattern_lower in h.next_action.lower():
            hits.append(f"{h.id} next: {h.next_action}")
        if h.conclusion and pattern_lower in h.conclusion.lower():
            hits.append(f"{h.id} conclusion: {h.conclusion}")
        
        # Search attempts
        for a in h.attempts:
            if pattern_lower in a.payload.lower():
                tag_str = f"[{a.tag}] " if a.tag else ""
                result_str = f" → {a.result}" if a.result else ""
                hits.append(f"{h.id}/try {tag_str}{a.payload}{result_str}")
            elif a.result and pattern_lower in a.result.lower():
                hits.append(f"{h.id}/try result: {a.result}")
    
    # Search confirmations
    for c in state.confirmations:
        if pattern_lower in c.title.lower():
            hits.append(f"{c.id}[{c.severity}|{c.status}] {c.title}")
        if c.notes and pattern_lower in c.notes.lower():
            hits.append(f"{c.id} notes: {c.notes}")
    
    # Search notes
    for i, n in enumerate(state.notes, 1):
        if pattern_lower in n.text.lower():
            tag = f"[{n.hyp_id}] " if n.hyp_id else ""
            hits.append(f"note {tag}{n.text}")
    
    # Search queue items
    for qname, items in state.queues.items():
        for item in items:
            if pattern_lower in item.desc.lower():
                hits.append(f"{item.id}[{qname}] {item.desc}")
    
    if not hits:
        typer.echo(f"No matches for '{pattern}'")
        return
    
    typer.echo(f"Matches for '{pattern}':")
    for hit in hits:
        typer.echo(f"  {hit}")


# ── Hypothesis commands ────────────────────────────────────────────────────


@app.command()
def new(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    desc: str = typer.Option(..., "--desc", help="Hypothesis description"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Priority 1/2/3"),
    next_action: Optional[str] = typer.Option(None, "--next", help="Next action to take"),
):
    """Add a new open hypothesis."""
    hypotheses.new(target, desc, priority, next_action)


@app.command()
def close(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H3)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    conclusion: str = typer.Option(..., "--conclusion", "-c", help="What you found / why closed"),
):
    """Mark a hypothesis as closed (dead end)."""
    hypotheses.close(hid, target, conclusion)


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
    hypotheses.confirm(hid, target, conclusion, title, severity, status_val)


@app.command()
def update(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H3)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    next_action: Optional[str] = typer.Option(None, "--next", help="New next action"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="New priority 1/2/3"),
    desc: Optional[str] = typer.Option(None, "--desc", help="New description"),
):
    """Update fields on an existing hypothesis."""
    hypotheses.update(hid, target, next_action, priority, desc)


@app.command()
def reopen(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H3)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    priority: int = typer.Option(2, "--priority", "-p", help="Priority for reopened hypothesis"),
    next_action: Optional[str] = typer.Option(None, "--next", help="Next action to take"),
):
    """Reopen a closed or confirmed hypothesis."""
    hypotheses.reopen(hid, target, priority, next_action)


@app.command()
def rm(
    item_id: str = typer.Argument(..., help="Hypothesis or Confirmation ID (e.g. H3, C1)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Remove a hypothesis or confirmation."""
    hypotheses.rm(item_id, target)


@app.command(name="try")
def try_cmd(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H14)"),
    payload: str = typer.Argument(..., help="What was tried"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    result: Optional[str] = typer.Option(None, "--result", "-r", help="What happened"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Technique category"),
    passed: bool = typer.Option(False, "--pass", help="Mark as pass (found something)"),
    partial: bool = typer.Option(False, "--partial", help="Mark as partial (worth noting)"),
):
    """Record a test attempt under a hypothesis."""
    hypotheses.try_cmd(hid, payload, target, result, tag, passed, partial)


@app.command()
def tries(
    hid: str = typer.Argument(..., help="Hypothesis ID (e.g. H14)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
):
    """List all attempts recorded under a hypothesis."""
    hypotheses.tries(hid, target, tag)


@app.command()
def confirmation(
    cid: str = typer.Argument(..., help="Confirmation ID (e.g. C1)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    status: Optional[str] = typer.Option(None, "--status", help="New status"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Notes to set"),
):
    """Update a confirmation."""
    hypotheses.confirmation(cid, target, status, notes)


# ── Queue commands ─────────────────────────────────────────────────────────


@app.command()
def qadd(
    desc: str = typer.Option(..., "--desc", help="Queue item description"),
    queue_name: str = typer.Option("default", "--queue", "-q", help="Queue name"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Add an item to a work queue."""
    queue.qadd(desc, queue_name, target)


@app.command()
def qdone(
    qid: str = typer.Argument(..., help="Queue item ID (e.g. Q3)"),
    hyp_id: Optional[str] = typer.Option(None, "--hyp", help="Link to hypothesis (e.g. H5)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    note: Optional[str] = typer.Option(None, "--note", help="Add a note to the state"),
):
    """Mark a queue item as done."""
    queue.qdone(qid, hyp_id, target, note)


@app.command()
def qskip(
    qid: str = typer.Argument(..., help="Queue item ID (e.g. Q3)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    note: Optional[str] = typer.Option(None, "--note", help="Add a note to the state"),
):
    """Mark a queue item as skipped."""
    queue.qskip(qid, target, note)


@app.command()
def qshow(
    queue_name: Optional[str] = typer.Option(None, "--queue", "-q", help="Filter by queue name"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Show work queue status."""
    queue.qshow(queue_name, target)


@app.command()
def qbulk(
    queue_name: str = typer.Option("default", "--queue", "-q", help="Queue name"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Bulk-add queue items from stdin."""
    queue.qbulk(queue_name, target)


# ── Note and utility commands ──────────────────────────────────────────────


@app.command()
def note(
    id_or_text: Optional[str] = typer.Argument(None, help="Hypothesis/vuln ID (e.g. H39) or note text"),
    text: Optional[str] = typer.Argument(None, help="Note text (when first arg is an ID)"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    rm_index: Optional[int] = typer.Option(None, "--rm", help="Remove note by 1-based index"),
):
    """Add a free-form note or remove one with --rm."""
    notes.note(id_or_text, text, target, rm_index)


@app.command(name="notes")
def notes_cmd(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Show all notes for the target."""
    notes.notes(target)


@app.command()
def last(
    action: str = typer.Argument(..., help="Description of last action taken"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Record the last action taken."""
    notes.last(action, target)


@app.command()
def block(
    reason: str = typer.Argument(..., help="What is blocking progress"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Mark research as blocked."""
    notes.block(reason, target)


@app.command()
def unblock(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Clear blocked status."""
    notes.unblock(target)
