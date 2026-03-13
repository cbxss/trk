from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Type aliases for clarity and consistency
type ISODate = str  # "2026-03-13"
type HypothesisID = str  # "H1", "H2", ...
type ConfirmationID = str  # "C1", "C2", ...
type QueueItemID = str  # "Q1", "Q2", ...

# Status types
type HypothesisStatus = Literal["open", "closed", "confirmed"]
type AttemptStatus = Literal["pass", "fail", "partial"]
type QueueStatus = Literal["pending", "done", "skipped"]
type ConfirmationStatus = Literal[
    "confirmed",
    "confirmed_needs_exfil",
    "confirmed_needs_poc",
    "confirmed_poc_ready",
    "submitted",
    "triaged",
    "bounty_paid",
    "closed",
    "false_positive",
]
type Severity = Literal["info", "low", "medium", "high", "critical"]


@dataclass
class QueueItem:
    id: QueueItemID
    queue: str                       # queue name e.g. "store_listeners"
    desc: str
    status: QueueStatus = "pending"
    hyp_id: HypothesisID | None = None  # linked hypothesis (set on qdone)
    created: ISODate | None = None
    done_ts: ISODate | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "queue": self.queue,
            "desc": self.desc,
            "status": self.status,
            "hyp_id": self.hyp_id,
            "created": self.created,
            "done_ts": self.done_ts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> QueueItem:
        return cls(
            id=d["id"],
            queue=d["queue"],
            desc=d["desc"],
            status=d.get("status", "pending"),
            hyp_id=d.get("hyp_id"),
            created=d.get("created"),
            done_ts=d.get("done_ts"),
        )


@dataclass
class Attempt:
    payload: str                     # what was tried
    result: str | None = None        # what happened
    tag: str | None = None           # grouping label e.g. "state_injection"
    status: AttemptStatus = "fail"
    ts: ISODate | None = None

    def to_dict(self) -> dict:
        return {
            "payload": self.payload,
            "result": self.result,
            "tag": self.tag,
            "status": self.status,
            "ts": self.ts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Attempt:
        return cls(
            payload=d["payload"],
            result=d.get("result"),
            tag=d.get("tag"),
            status=d.get("status", "fail"),
            ts=d.get("ts"),
        )


@dataclass
class Hypothesis:
    id: HypothesisID
    desc: str
    status: HypothesisStatus
    priority: int | None = None      # 1/2/3 for open items
    next_action: str | None = None
    conclusion: str | None = None
    closed: ISODate | None = None
    created: ISODate | None = None
    attempts: list[Attempt] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "desc": self.desc,
            "status": self.status,
            "priority": self.priority,
            "next_action": self.next_action,
            "conclusion": self.conclusion,
            "closed": self.closed,
            "created": self.created,
            "attempts": [a.to_dict() for a in self.attempts],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Hypothesis:
        return cls(
            id=d["id"],
            desc=d["desc"],
            status=d["status"],
            priority=d.get("priority"),
            next_action=d.get("next_action"),
            conclusion=d.get("conclusion"),
            closed=d.get("closed"),
            created=d.get("created"),
            attempts=[Attempt.from_dict(a) for a in d.get("attempts", [])],
        )


@dataclass
class Confirmation:
    id: ConfirmationID
    title: str
    severity: Severity
    status: ConfirmationStatus
    notes: str | None = None
    from_hypothesis: HypothesisID | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "status": self.status,
            "notes": self.notes,
            "from_hypothesis": self.from_hypothesis,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Confirmation:
        return cls(
            id=d["id"],
            title=d["title"],
            severity=d["severity"],
            status=d["status"],
            notes=d.get("notes"),
            from_hypothesis=d.get("from_hypothesis"),
        )


@dataclass
class Note:
    text: str
    ts: ISODate
    hyp_id: HypothesisID | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "ts": self.ts,
            "hyp_id": self.hyp_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Note:
        return cls(
            text=d["text"],
            ts=d["ts"],
            hyp_id=d.get("hyp_id"),
        )


@dataclass
class TrackingState:
    target: str
    updated: ISODate
    last_action: str | None = None
    blocked_on: str | None = None
    confirmations: list[Confirmation] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    queues: dict[str, list[QueueItem]] = field(default_factory=dict)
    notes: list[Note] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "updated": self.updated,
            "last_action": self.last_action,
            "blocked_on": self.blocked_on,
            "confirmations": [c.to_dict() for c in self.confirmations],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "queues": {name: [q.to_dict() for q in items] for name, items in self.queues.items()},
            "notes": [n.to_dict() for n in self.notes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> TrackingState:
        # Backward compatibility: migrate vulns -> confirmations (V# -> C#)
        confirmations_data = d.get("confirmations", [])
        if not confirmations_data and "vulns" in d:
            # Migrate old vulns to confirmations, change V# to C#
            confirmations_data = []
            for v in d.get("vulns", []):
                v_copy = v.copy()
                if v_copy["id"].startswith("V"):
                    v_copy["id"] = "C" + v_copy["id"][1:]
                confirmations_data.append(v_copy)
        
        # Backward compatibility: migrate queue_items -> queues
        queues_data = d.get("queues", {})
        if not queues_data and "queue_items" in d:
            # Group old queue_items by queue name
            from collections import defaultdict
            queues_grouped = defaultdict(list)
            for q in d.get("queue_items", []):
                queues_grouped[q.get("queue", "default")].append(q)
            queues_data = dict(queues_grouped)
        
        # Notes: convert from dict if needed (backward compat)
        notes_data = d.get("notes", [])
        notes = []
        for n in notes_data:
            if isinstance(n, dict):
                notes.append(Note.from_dict(n))
            else:
                # Should not happen, but handle gracefully
                notes.append(Note(text=str(n), ts="unknown"))
        
        return cls(
            target=d["target"],
            updated=d["updated"],
            last_action=d.get("last_action"),
            blocked_on=d.get("blocked_on"),
            confirmations=[Confirmation.from_dict(c) for c in confirmations_data],
            hypotheses=[Hypothesis.from_dict(h) for h in d.get("hypotheses", [])],
            queues={name: [QueueItem.from_dict(q) for q in items] for name, items in queues_data.items()},
            notes=notes,
        )

    def next_hypothesis_id(self) -> HypothesisID:
        if not self.hypotheses:
            return "H1"
        nums = []
        for h in self.hypotheses:
            if h.id.startswith("H") and h.id[1:].isdigit():
                nums.append(int(h.id[1:]))
        return f"H{max(nums) + 1}" if nums else "H1"

    def next_queue_item_id(self) -> QueueItemID:
        # Iterate through all queues to find highest Q# number
        nums = []
        for items in self.queues.values():
            for q in items:
                if q.id.startswith("Q") and q.id[1:].isdigit():
                    nums.append(int(q.id[1:]))
        return f"Q{max(nums) + 1}" if nums else "Q1"

    def get_queue_item(self, qid: QueueItemID | str) -> QueueItem | None:
        qid = qid.upper()
        for items in self.queues.values():
            for q in items:
                if q.id.upper() == qid:
                    return q
        return None

    def next_confirmation_id(self) -> ConfirmationID:
        if not self.confirmations:
            return "C1"
        nums = []
        for c in self.confirmations:
            if c.id.startswith("C") and c.id[1:].isdigit():
                nums.append(int(c.id[1:]))
        return f"C{max(nums) + 1}" if nums else "C1"

    def get_hypothesis(self, hid: HypothesisID | str) -> Hypothesis | None:
        hid = hid.upper()
        for h in self.hypotheses:
            if h.id.upper() == hid:
                return h
        return None

    def get_confirmation(self, cid: ConfirmationID | str) -> Confirmation | None:
        cid = cid.upper()
        for c in self.confirmations:
            if c.id.upper() == cid:
                return c
        return None
