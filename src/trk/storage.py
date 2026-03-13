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



