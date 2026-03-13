"""Shared utilities for commands."""
from __future__ import annotations

import sys
from functools import wraps
from typing import Callable, Optional, TypeVar

import typer

from .. import storage
from ..exceptions import TrkError
from ..state import TrackingState

T = TypeVar('T')


def handle_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to handle TrkError and validation exceptions cleanly."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except TrkError as e:
            typer.echo(f"[trk] error: {e}", err=True)
            raise typer.Exit(1)
        except ValueError as e:
            # Validation errors from dataclass __post_init__
            typer.echo(f"[trk] validation error: {e}", err=True)
            raise typer.Exit(1)
    return wrapper


def get_state(target: Optional[str]) -> TrackingState:
    """Load state for the specified or inferred target."""
    t = storage.resolve_target(target)
    return storage.load(t)


def save_state(state: TrackingState) -> None:
    """Save state and emit confirmation message."""
    storage.save(state.target, state)
    typer.echo(f"[trk] saved: {state.target}", err=True)
