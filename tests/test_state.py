"""Tests for state.py dataclass models."""
import pytest
from trk.state import Hypothesis, Confirmation, TrackingState


def make_state() -> TrackingState:
    return TrackingState(target="test", updated="2026-02-17")


def test_next_hypothesis_id_empty():
    s = make_state()
    assert s.next_hypothesis_id() == "H1"


def test_next_hypothesis_id_sequential():
    s = make_state()
    s.hypotheses = [
        Hypothesis(id="H1", desc="first", status="open"),
        Hypothesis(id="H2", desc="second", status="closed"),
    ]
    assert s.next_hypothesis_id() == "H3"


def test_next_confirmation_id_empty():
    s = make_state()
    assert s.next_confirmation_id() == "C1"


def test_next_confirmation_id_sequential():
    s = make_state()
    s.confirmations = [Confirmation(id="C1", title="xss", severity="high", status="confirmed")]
    assert s.next_confirmation_id() == "C2"


def test_get_hypothesis_found():
    s = make_state()
    h = Hypothesis(id="H3", desc="test hyp", status="open")
    s.hypotheses.append(h)
    assert s.get_hypothesis("H3") is h
    assert s.get_hypothesis("h3") is h  # case-insensitive


def test_get_hypothesis_not_found():
    s = make_state()
    assert s.get_hypothesis("H99") is None


def test_get_confirmation_found():
    s = make_state()
    c = Confirmation(id="C2", title="xss", severity="high", status="confirmed")
    s.confirmations.append(c)
    assert s.get_confirmation("C2") is c
    assert s.get_confirmation("c2") is c


def test_roundtrip_serialization():
    s = TrackingState(
        target="doordash",
        updated="2026-02-17",
        last_action="Injected hook",
        blocked_on=None,
        confirmations=[Confirmation(id="C1", title="DOM XSS", severity="high", status="confirmed_needs_exfil", notes="alert works")],
        hypotheses=[
            Hypothesis(id="H1", desc="dead end", status="closed", conclusion="nothing", closed="2026-02-17"),
            Hypothesis(id="H2", desc="open hyp", status="open", priority=1, next_action="test this"),
        ],
    )
    d = s.to_dict()
    s2 = TrackingState.from_dict(d)
    assert s2.target == s.target
    assert s2.last_action == s.last_action
    assert len(s2.confirmations) == 1
    assert s2.confirmations[0].title == "DOM XSS"
    assert s2.confirmations[0].notes == "alert works"
    assert len(s2.hypotheses) == 2
    assert s2.hypotheses[1].priority == 1


def test_hypothesis_roundtrip():
    h = Hypothesis(
        id="H5",
        desc="test",
        status="open",
        priority=2,
        next_action="do something",
        conclusion=None,
        closed=None,
        created="2026-02-17",
    )
    h2 = Hypothesis.from_dict(h.to_dict())
    assert h2.id == "H5"
    assert h2.priority == 2
    assert h2.created == "2026-02-17"


def test_confirmation_roundtrip():
    c = Confirmation(id="C3", title="SQLi", severity="critical", status="reported", notes="blind sqli", from_hypothesis="H4")
    c2 = Confirmation.from_dict(c.to_dict())
    assert c2.from_hypothesis == "H4"
    assert c2.severity == "critical"


def test_notes_roundtrip():
    from trk.state import Note
    s = make_state()
    s.notes = [Note(text="API uses RS256 JWT", ts="2026-02-20")]
    s2 = TrackingState.from_dict(s.to_dict())
    assert len(s2.notes) == 1
    assert s2.notes[0].text == "API uses RS256 JWT"
    assert s2.notes[0].ts == "2026-02-20"


def test_notes_backward_compatible():
    """from_dict on old state without notes key returns empty list."""
    d = {"target": "test", "updated": "2026-02-17"}
    s = TrackingState.from_dict(d)
    assert s.notes == []
