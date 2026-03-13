"""trk CLI - simple work tracker."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from . import storage, display, export
from .state import (
    Attempt, Confirmation, Hypothesis, Note, QueueItem, TrackingState
)

app = typer.Typer(name="trk", help="Generic work tracker", no_args_is_help=True)


def _today() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _get(target: Optional[str]) -> TrackingState:
    """Load state."""
    t = target or os.environ.get("TRK_TARGET")
    if not t:
        # Try local state.json
        local = Path("state.json")
        if local.exists():
            import json
            with local.open() as f:
                t = json.load(f).get("target")
    if not t:
        typer.echo("No target. Use -t/--target or TRK_TARGET env var", err=True)
        raise typer.Exit(1)
    
    p = storage.state_path(t)
    if not p.exists():
        typer.echo(f"Target '{t}' not found. Run: trk init {t}", err=True)
        raise typer.Exit(1)
    
    return storage.load(t)


def _save(state: TrackingState) -> None:
    """Save state."""
    state.updated = _today()
    storage.save(state.target, state)
    typer.echo(f"[trk] saved: {state.target}", err=True)


# ── Commands ───────────────────────────────────────────────────────────────


@app.command()
def targets():
    """List all targets."""
    ts = storage.list_targets()
    if not ts:
        typer.echo("No targets. Run: trk init <name>")
        return
    for t in ts:
        typer.echo(t)


@app.command()
def init(
    name: str = typer.Argument(..., help="Target name"),
    link: bool = typer.Option(False, "--link", help="Symlink ./state.json"),
):
    """Create a new target."""
    p = storage.state_path(name)
    if p.exists():
        typer.echo(f"Target '{name}' already exists", err=True)
        raise typer.Exit(1)
    
    state = TrackingState(target=name, updated=_today())
    storage.save(name, state)
    typer.echo(f"[trk] initialized: {name}")
    
    if link:
        local = Path("state.json")
        if local.exists() or local.is_symlink():
            local.unlink()
        local.symlink_to(p)
        typer.echo(f"[trk] linked: ./state.json → {p}")


@app.command()
def show(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    closed: bool = typer.Option(False, "--closed"),
    json_output: bool = typer.Option(False, "--json"),
    show_confirmations: bool = typer.Option(False, "--confirmations"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n"),
):
    """Show state."""
    state = _get(target)
    if json_output:
        typer.echo(export.to_json(state), nl=False)
    else:
        display.show(state, show_closed=closed, show_confirmations=show_confirmations, limit=limit)


@app.command()
def new(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    desc: str = typer.Option(..., "--desc"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p"),
    next_action: Optional[str] = typer.Option(None, "--next"),
):
    """Add hypothesis."""
    state = _get(target)
    hid = state.next_hypothesis_id()
    h = Hypothesis(
        id=hid, desc=desc, status="open",
        priority=priority, next_action=next_action, created=_today()
    )
    state.hypotheses.append(h)
    _save(state)
    typer.echo(f"[trk] added {hid}: {desc}")


@app.command()
def close(
    hid: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    conclusion: str = typer.Option(..., "--conclusion", "-c"),
):
    """Close hypothesis."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    h.status = "closed"
    h.conclusion = conclusion
    h.closed = _today()
    _save(state)
    typer.echo(f"[trk] closed {h.id}")


@app.command()
def confirm(
    hid: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    conclusion: str = typer.Option(..., "--conclusion", "-c"),
    title: Optional[str] = typer.Option(None, "--title"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s"),
    status_val: str = typer.Option("confirmed", "--status"),
):
    """Confirm hypothesis."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    
    h.status = "confirmed"
    h.conclusion = conclusion
    h.closed = _today()
    
    if title:
        if not severity:
            typer.echo("--severity required with --title", err=True)
            raise typer.Exit(1)
        cid = state.next_confirmation_id()
        c = Confirmation(
            id=cid, title=title, severity=severity,
            status=status_val, from_hypothesis=h.id
        )
        state.confirmations.append(c)
        typer.echo(f"[trk] created {cid}: {title}")
    
    _save(state)
    typer.echo(f"[trk] confirmed {h.id}")


@app.command()
def update(
    hid: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    next_action: Optional[str] = typer.Option(None, "--next"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p"),
    desc: Optional[str] = typer.Option(None, "--desc"),
):
    """Update hypothesis."""
    if not any([next_action, priority, desc]):
        typer.echo("Provide --next, --priority, or --desc", err=True)
        raise typer.Exit(1)
    
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    
    if next_action:
        h.next_action = next_action
    if priority:
        h.priority = priority
    if desc:
        h.desc = desc
    
    _save(state)
    typer.echo(f"[trk] updated {h.id}")


@app.command()
def reopen(
    hid: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    priority: int = typer.Option(2, "--priority", "-p"),
    next_action: Optional[str] = typer.Option(None, "--next"),
):
    """Reopen hypothesis."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    
    if h.status == "open":
        typer.echo(f"Hypothesis '{hid}' already open", err=True)
        raise typer.Exit(1)
    
    h.status = "open"
    h.priority = priority
    h.closed = None
    if next_action:
        h.next_action = next_action
    
    _save(state)
    typer.echo(f"[trk] reopened {hid}")


@app.command()
def rm(
    item_id: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Remove hypothesis or confirmation."""
    state = _get(target)
    item_id = item_id.upper()
    
    if item_id.startswith("H"):
        h = state.get_hypothesis(item_id)
        if not h:
            typer.echo(f"Hypothesis '{item_id}' not found", err=True)
            raise typer.Exit(1)
        state.hypotheses.remove(h)
    elif item_id.startswith("C"):
        c = state.get_confirmation(item_id)
        if not c:
            typer.echo(f"Confirmation '{item_id}' not found", err=True)
            raise typer.Exit(1)
        state.confirmations.remove(c)
    else:
        typer.echo(f"Invalid ID '{item_id}'", err=True)
        raise typer.Exit(1)
    
    _save(state)
    typer.echo(f"[trk] removed {item_id}")


@app.command(name="try")
def try_cmd(
    hid: str = typer.Argument(...),
    payload: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    result: Optional[str] = typer.Option(None, "--result", "-r"),
    tag: Optional[str] = typer.Option(None, "--tag"),
    passed: bool = typer.Option(False, "--pass"),
    partial: bool = typer.Option(False, "--partial"),
):
    """Record attempt."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    
    status = "pass" if passed else ("partial" if partial else "fail")
    a = Attempt(payload=payload, result=result, tag=tag, status=status, ts=_today())
    h.attempts.append(a)
    _save(state)
    
    sym = {"pass": "✓", "fail": "✗", "partial": "~"}[status]
    tag_str = f"[{tag}] " if tag else ""
    typer.echo(f"[trk] {h.id} {tag_str}{payload} {sym}" + (f" → {result}" if result else ""))


@app.command()
def tries(
    hid: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    tag: Optional[str] = typer.Option(None, "--tag"),
):
    """List attempts."""
    state = _get(target)
    h = state.get_hypothesis(hid)
    if not h:
        typer.echo(f"Hypothesis '{hid}' not found", err=True)
        raise typer.Exit(1)
    
    attempts = [a for a in h.attempts if (tag is None or a.tag == tag)]
    if not attempts:
        typer.echo(f"No attempts for {hid}" + (f" [tag={tag}]" if tag else ""))
        return
    
    syms = {"pass": "✓", "fail": "✗", "partial": "~"}
    for a in attempts:
        tag_str = f"[{a.tag}] " if a.tag else ""
        result_str = f" → {a.result}" if a.result else ""
        typer.echo(f"  {syms.get(a.status, '?')} {tag_str}{a.payload}{result_str}")


@app.command()
def confirmation(
    cid: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    status: Optional[str] = typer.Option(None, "--status"),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    """Update confirmation."""
    state = _get(target)
    c = state.get_confirmation(cid)
    if not c:
        typer.echo(f"Confirmation '{cid}' not found", err=True)
        raise typer.Exit(1)
    
    if status:
        c.status = status
    if notes:
        c.notes = notes
    
    _save(state)
    typer.echo(f"[trk] updated {c.id}")


@app.command()
def qadd(
    desc: str = typer.Option(..., "--desc"),
    queue: str = typer.Option("default", "--queue", "-q"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Add queue item."""
    state = _get(target)
    qid = state.next_queue_item_id()
    item = QueueItem(id=qid, queue=queue, desc=desc, created=_today())
    if queue not in state.queues:
        state.queues[queue] = []
    state.queues[queue].append(item)
    _save(state)
    typer.echo(f"[trk] queued {qid}[{queue}]: {desc}")


@app.command()
def qdone(
    qid: str = typer.Argument(...),
    hyp_id: Optional[str] = typer.Option(None, "--hyp"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    note: Optional[str] = typer.Option(None, "--note"),
):
    """Mark queue item done."""
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
    
    _save(state)
    typer.echo(f"[trk] done {qid}" + (f" → {hyp_id}" if hyp_id else ""))


@app.command()
def qskip(
    qid: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    note: Optional[str] = typer.Option(None, "--note"),
):
    """Skip queue item."""
    state = _get(target)
    item = state.get_queue_item(qid)
    if not item:
        typer.echo(f"Queue item '{qid}' not found", err=True)
        raise typer.Exit(1)
    
    item.status = "skipped"
    item.done_ts = _today()
    
    if note:
        state.notes.append(Note(text=note, ts=_today()))
    
    _save(state)
    typer.echo(f"[trk] skipped {qid}")


@app.command()
def qshow(
    queue: Optional[str] = typer.Option(None, "--queue", "-q"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Show queues."""
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
    queue: str = typer.Option("default", "--queue", "-q"),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Bulk add from stdin."""
    state = _get(target)
    lines = [l.rstrip() for l in sys.stdin.read().splitlines() if l.strip()]
    if not lines:
        typer.echo("No input", err=True)
        raise typer.Exit(1)
    
    if queue not in state.queues:
        state.queues[queue] = []
    
    added = []
    for desc in lines:
        qid = state.next_queue_item_id()
        state.queues[queue].append(QueueItem(id=qid, queue=queue, desc=desc, created=_today()))
        added.append(qid)
    
    _save(state)
    typer.echo(f"[trk] queued {', '.join(added)} → {queue}")


@app.command()
def note(
    id_or_text: Optional[str] = typer.Argument(None),
    text: Optional[str] = typer.Argument(None),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    rm_index: Optional[int] = typer.Option(None, "--rm"),
):
    """Add/remove note."""
    state = _get(target)
    
    if rm_index is not None:
        if rm_index < 1 or rm_index > len(state.notes):
            typer.echo(f"Index {rm_index} out of range", err=True)
            raise typer.Exit(1)
        removed = state.notes.pop(rm_index - 1)
        _save(state)
        typer.echo(f"[trk] removed note: {removed.text}")
        return
    
    # Parse args
    if text is not None:
        hyp_id = id_or_text.upper() if id_or_text else None
        note_text = text
    else:
        hyp_id = None
        note_text = id_or_text
    
    if not note_text:
        typer.echo("Provide note text or --rm <index>", err=True)
        raise typer.Exit(1)
    
    state.notes.append(Note(text=note_text, ts=_today(), hyp_id=hyp_id))
    _save(state)
    typer.echo(f"[trk] note added" + (f" (→ {hyp_id})" if hyp_id else ""))


@app.command()
def notes(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Show notes."""
    state = _get(target)
    if not state.notes:
        typer.echo("No notes")
        return
    for i, n in enumerate(state.notes, 1):
        tag = f" [{n.hyp_id}]" if n.hyp_id else ""
        typer.echo(f"  {i}. [{n.ts}]{tag} {n.text}")


@app.command()
def last(
    action: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Set last action."""
    state = _get(target)
    state.last_action = action
    _save(state)
    typer.echo(f"[trk] last_action: {action}")


@app.command()
def block(
    reason: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Mark blocked."""
    state = _get(target)
    state.blocked_on = reason
    _save(state)
    typer.echo(f"[trk] blocked: {reason}")


@app.command()
def unblock(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Clear blocked."""
    state = _get(target)
    state.blocked_on = None
    _save(state)
    typer.echo("[trk] unblocked")


@app.command(name="export")
def export_cmd(
    target: Optional[str] = typer.Option(None, "-t", "--target"),
    format: str = typer.Option("md", "--format", "-f"),
):
    """Export state."""
    state = _get(target)
    if format == "json":
        typer.echo(export.to_json(state), nl=False)
    else:
        typer.echo(export.to_markdown(state), nl=False)


@app.command()
def grep(
    pattern: str = typer.Argument(...),
    target: Optional[str] = typer.Option(None, "-t", "--target"),
):
    """Search."""
    state = _get(target)
    p = pattern.lower()
    hits = []
    
    for h in state.hypotheses:
        if p in h.desc.lower():
            hits.append(f"{h.id}[{h.status}] {h.desc}")
        if h.next_action and p in h.next_action.lower():
            hits.append(f"{h.id} next: {h.next_action}")
        if h.conclusion and p in h.conclusion.lower():
            hits.append(f"{h.id} conclusion: {h.conclusion}")
        for a in h.attempts:
            if p in a.payload.lower():
                hits.append(f"{h.id}/try {a.payload}")
            elif a.result and p in a.result.lower():
                hits.append(f"{h.id}/try result: {a.result}")
    
    for c in state.confirmations:
        if p in c.title.lower():
            hits.append(f"{c.id} {c.title}")
        if c.notes and p in c.notes.lower():
            hits.append(f"{c.id} notes: {c.notes}")
    
    for n in state.notes:
        if p in n.text.lower():
            tag = f"[{n.hyp_id}] " if n.hyp_id else ""
            hits.append(f"note {tag}{n.text}")
    
    for qname, items in state.queues.items():
        for item in items:
            if p in item.desc.lower():
                hits.append(f"{item.id}[{qname}] {item.desc}")
    
    if not hits:
        typer.echo(f"No matches for '{pattern}'")
        return
    
    typer.echo(f"Matches for '{pattern}':")
    for hit in hits:
        typer.echo(f"  {hit}")


import os
