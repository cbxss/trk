"""Tests for export.py."""
import json
from track.state import TrackingState, Hypothesis, Confirmation
from track.export import to_markdown, to_json


def make_rich_state() -> TrackingState:
    return TrackingState(
        target="doordash",
        updated="2026-02-17",
        last_action="Tested postMessage injection",
        blocked_on=None,
        confirmations=[
            Confirmation(
                id="C1",
                title="DOM XSS via postMessage",
                severity="high",
                status="confirmed_needs_exfil",
                notes="alert() works. fetch loses race.",
                from_hypothesis="H2",
            )
        ],
        hypotheses=[
            Hypothesis(
                id="H1",
                desc="Arkose handlers contain sink",
                status="closed",
                conclusion="Only resize/challenge/token events. Dead end.",
                closed="2026-02-17",
            ),
            Hypothesis(
                id="H2",
                desc="postMessage listener is exploitable",
                status="confirmed",
                conclusion="Confirmed XSS",
                closed="2026-02-17",
            ),
            Hypothesis(
                id="H3",
                desc="Popup bypasses frame-buster",
                status="open",
                priority=1,
                next_action="window.open edit_profile, postMessage XSS",
            ),
        ],
    )


def test_markdown_has_header():
    md = to_markdown(make_rich_state())
    assert "# Security Research: doordash" in md
    assert "2026-02-17" in md


def test_markdown_has_confirmation():
    md = to_markdown(make_rich_state())
    assert "DOM XSS via postMessage" in md
    assert "confirmed_needs_exfil" in md
    assert "alert() works" in md


def test_markdown_has_open_hyp():
    md = to_markdown(make_rich_state())
    assert "Popup bypasses frame-buster" in md
    assert "window.open edit_profile" in md


def test_markdown_has_closed_hyps():
    md = to_markdown(make_rich_state())
    assert "Arkose handlers contain sink" in md
    assert "Dead end" in md


def test_json_export_roundtrip():
    state = make_rich_state()
    j = to_json(state)
    d = json.loads(j)
    s2 = TrackingState.from_dict(d)
    assert s2.target == state.target
    assert len(s2.confirmations) == 1
    assert s2.confirmations[0].severity == "high"
    assert len(s2.hypotheses) == 3


def test_json_export_open_filter():
    j = to_json(make_rich_state())
    d = json.loads(j)
    open_hyps = [h["id"] for h in d["hypotheses"] if h["status"] == "open"]
    assert open_hyps == ["H3"]


def test_markdown_blocked_on():
    state = make_rich_state()
    state.blocked_on = "Rate limited for 24h"
    md = to_markdown(state)
    assert "Rate limited for 24h" in md
