"""Hypothesis lifecycle commands."""
from __future__ import annotations

from typing import Optional

import typer

from ..service import TrackingService
from .shared import handle_errors, get_state, save_state


@handle_errors
def new(
    target: Optional[str],
    desc: str,
    priority: Optional[int],
    next_action: Optional[str],
):
    """Add a new open hypothesis."""
    state = get_state(target)
    service = TrackingService(state)
    h = service.add_hypothesis(desc, priority, next_action)
    save_state(state)
    typer.echo(f"[trk] added {h.id}: {h.desc}")


@handle_errors
def close(hid: str, target: Optional[str], conclusion: str):
    """Mark a hypothesis as closed (dead end)."""
    state = get_state(target)
    service = TrackingService(state)
    h = service.close_hypothesis(hid, conclusion)
    save_state(state)
    typer.echo(f"[trk] closed {h.id}: {conclusion}")


@handle_errors
def confirm(
    hid: str,
    target: Optional[str],
    conclusion: str,
    title: Optional[str],
    severity: Optional[str],
    status_val: str,
):
    """Mark a hypothesis as confirmed, optionally creating a confirmation."""
    state = get_state(target)
    service = TrackingService(state)
    h, c = service.confirm_hypothesis(hid, conclusion, title, severity, status_val)
    save_state(state)
    
    if c:
        typer.echo(f"[trk] created {c.id}: {c.title}")
    typer.echo(f"[trk] confirmed {h.id}: {conclusion}")


@handle_errors
def update(
    hid: str,
    target: Optional[str],
    next_action: Optional[str],
    priority: Optional[int],
    desc: Optional[str],
):
    """Update fields on an existing hypothesis."""
    if next_action is None and priority is None and desc is None:
        typer.echo("Nothing to update. Use --next, --priority, or --desc.", err=True)
        raise typer.Exit(1)
    
    state = get_state(target)
    service = TrackingService(state)
    h = service.update_hypothesis(hid, desc, priority, next_action)
    save_state(state)
    typer.echo(f"[trk] updated {h.id}")


@handle_errors
def reopen(
    hid: str,
    target: Optional[str],
    priority: int,
    next_action: Optional[str],
):
    """Reopen a closed or confirmed hypothesis."""
    state = get_state(target)
    service = TrackingService(state)
    h = service.reopen_hypothesis(hid, priority, next_action)
    save_state(state)
    typer.echo(f"[trk] reopened {hid} (priority {priority})")


@handle_errors
def rm(item_id: str, target: Optional[str]):
    """Remove a hypothesis or confirmation."""
    state = get_state(target)
    service = TrackingService(state)
    item_id_upper = item_id.upper()
    
    if item_id_upper.startswith("H"):
        service.remove_hypothesis(item_id)
        save_state(state)
        typer.echo(f"[trk] removed {item_id}")
    elif item_id_upper.startswith("C"):
        service.remove_confirmation(item_id)
        save_state(state)
        typer.echo(f"[trk] removed {item_id}")
    else:
        typer.echo(f"Invalid ID '{item_id}' — must start with H or C", err=True)
        raise typer.Exit(1)


@handle_errors
def try_cmd(
    hid: str,
    payload: str,
    target: Optional[str],
    result: Optional[str],
    tag: Optional[str],
    passed: bool,
    partial: bool,
):
    """Record a test attempt under a hypothesis."""
    state = get_state(target)
    service = TrackingService(state)
    status = "pass" if passed else ("partial" if partial else "fail")
    a = service.add_attempt(hid, payload, result, tag, status)
    save_state(state)
    
    sym = {"pass": "✓", "fail": "✗", "partial": "~"}[status]
    tag_str = f"[{tag}] " if tag else ""
    h = state.get_hypothesis(hid)
    typer.echo(f"[trk] {h.id} {tag_str}{payload} {sym}" + (f" → {result}" if result else ""))


@handle_errors
def tries(hid: str, target: Optional[str], tag: Optional[str]):
    """List all attempts recorded under a hypothesis."""
    state = get_state(target)
    h = state.get_hypothesis(hid)
    if not h:
        from ..exceptions import HypothesisNotFound
        raise HypothesisNotFound(hid)
    
    attempts = [a for a in h.attempts if (tag is None or a.tag == tag)]
    if not attempts:
        typer.echo(f"No attempts recorded for {hid}" + (f" [tag={tag}]" if tag else ""))
        return
    
    syms = {"pass": "✓", "fail": "✗", "partial": "~"}
    for a in attempts:
        tag_str = f"[{a.tag}] " if a.tag else ""
        result_str = f" → {a.result}" if a.result else ""
        typer.echo(f"  {syms.get(a.status, '?')} {tag_str}{a.payload}{result_str}")


@handle_errors
def confirmation(
    cid: str,
    target: Optional[str],
    status: Optional[str],
    notes: Optional[str],
):
    """Update a confirmation."""
    state = get_state(target)
    service = TrackingService(state)
    c = service.update_confirmation(cid, status, notes)
    save_state(state)
    typer.echo(f"[trk] updated {c.id}")
