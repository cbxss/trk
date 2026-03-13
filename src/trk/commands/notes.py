"""Note and utility commands."""
from __future__ import annotations

from typing import Optional

import typer

from ..service import TrackingService
from .shared import handle_errors, get_state, save_state


@handle_errors
def note(
    id_or_text: Optional[str],
    text: Optional[str],
    target: Optional[str],
    rm_index: Optional[int],
):
    """Add a free-form note or remove one with --rm."""
    state = get_state(target)
    service = TrackingService(state)
    
    if rm_index is not None:
        removed = service.remove_note(rm_index)
        save_state(state)
        typer.echo(f"[trk] removed note: {removed.text}")
        return
    
    # Resolve args: `trk note H39 "text"` or `trk note "text"`
    if text is not None:
        hyp_id = id_or_text.upper() if id_or_text else None
        note_text = text
    else:
        hyp_id = None
        note_text = id_or_text
    
    if not note_text:
        typer.echo("Provide note text or --rm <index>", err=True)
        raise typer.Exit(1)
    
    service.add_note(note_text, hyp_id)
    save_state(state)
    tag = f" (linked to {hyp_id})" if hyp_id else ""
    typer.echo(f"[trk] note added{tag}")


@handle_errors
def notes(target: Optional[str]):
    """Show all notes for the target."""
    state = get_state(target)
    if not state.notes:
        typer.echo("No notes.")
        return
    for i, n in enumerate(state.notes, 1):
        tag = f" [{n.hyp_id}]" if n.hyp_id else ""
        typer.echo(f"  {i}. [{n.ts}]{tag} {n.text}")


@handle_errors
def last(action: str, target: Optional[str]):
    """Record the last action taken."""
    state = get_state(target)
    service = TrackingService(state)
    service.set_last_action(action)
    save_state(state)
    typer.echo(f"[trk] last_action: {action}")


@handle_errors
def block(reason: str, target: Optional[str]):
    """Mark research as blocked."""
    state = get_state(target)
    service = TrackingService(state)
    service.set_blocked(reason)
    save_state(state)
    typer.echo(f"[trk] blocked: {reason}")


@handle_errors
def unblock(target: Optional[str]):
    """Clear blocked status."""
    state = get_state(target)
    service = TrackingService(state)
    service.clear_blocked()
    save_state(state)
    typer.echo("[trk] unblocked")
