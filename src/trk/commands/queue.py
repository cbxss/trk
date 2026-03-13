"""Queue management commands."""
from __future__ import annotations

import sys
from typing import Optional

import typer

from .. import display
from ..service import TrackingService
from .shared import handle_errors, get_state, save_state


@handle_errors
def qadd(desc: str, queue: str, target: Optional[str]):
    """Add an item to a work queue."""
    state = get_state(target)
    service = TrackingService(state)
    item = service.add_queue_item(queue, desc)
    save_state(state)
    typer.echo(f"[trk] queued {item.id}[{queue}]: {desc}")


@handle_errors
def qdone(
    qid: str,
    hyp_id: Optional[str],
    target: Optional[str],
    note: Optional[str],
):
    """Mark a queue item as done."""
    state = get_state(target)
    service = TrackingService(state)
    item = service.mark_queue_item_done(qid, hyp_id)
    if note:
        service.add_note(note)
    save_state(state)
    hyp_str = f" → {hyp_id}" if hyp_id else ""
    typer.echo(f"[trk] done {qid}{hyp_str}")


@handle_errors
def qskip(qid: str, target: Optional[str], note: Optional[str]):
    """Mark a queue item as skipped."""
    state = get_state(target)
    service = TrackingService(state)
    item = service.skip_queue_item(qid)
    if note:
        service.add_note(note)
    save_state(state)
    typer.echo(f"[trk] skipped {qid}")


@handle_errors
def qshow(queue: Optional[str], target: Optional[str]):
    """Show work queue status."""
    state = get_state(target)
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


@handle_errors
def qbulk(queue: str, target: Optional[str]):
    """Bulk-add queue items from stdin."""
    state = get_state(target)
    service = TrackingService(state)
    lines = [l.rstrip() for l in sys.stdin.read().splitlines() if l.strip()]
    if not lines:
        typer.echo("No input lines — pipe descriptions via stdin", err=True)
        raise typer.Exit(1)
    
    items = service.bulk_add_queue_items(queue, lines)
    save_state(state)
    added = [item.id for item in items]
    typer.echo(f"[trk] queued {', '.join(added)} → queue '{queue}'")
