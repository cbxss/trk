from __future__ import annotations

import json
import os
from pathlib import Path

from .state import TrackingState


def data_dir() -> Path:
    d = Path.home() / ".local" / "share" / "trk"
    d.mkdir(parents=True, exist_ok=True)
    return d


def state_path(target: str) -> Path:
    return data_dir() / f"{target}.json"


def load(target: str) -> TrackingState:
    p = state_path(target)
    if not p.exists():
        raise FileNotFoundError(f"No state file for target '{target}'. Run: trk init {target}")
    with p.open() as f:
        return TrackingState.from_dict(json.load(f))


def save(target: str, state: TrackingState) -> None:
    p = state_path(target)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state.to_dict(), f, indent=2)
        f.write("\n")
    os.replace(tmp, p)


def list_targets() -> list[str]:
    return sorted(p.stem for p in data_dir().glob("*.json"))


def resolve_target(explicit: str | None) -> str:
    if explicit:
        return explicit

    # Check for local state.json symlink/file
    local = Path("state.json")
    if local.exists():
        try:
            with local.open() as f:
                d = json.load(f)
            t = d.get("target")
            if t:
                return t
        except (json.JSONDecodeError, OSError):
            pass

    # Check environment variable
    env = os.environ.get("HYP_TARGET")
    if env:
        return env

    raise ValueError(
        "No target specified. Use -t/--target, set HYP_TARGET, or run from a directory with state.json"
    )
