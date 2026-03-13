"""Business logic layer for trk operations."""
from __future__ import annotations

from datetime import datetime

from .exceptions import (
    ConfirmationNotFound,
    HypothesisNotFound,
    InvalidStatus,
    QueueItemNotFound,
)
from .state import (
    Attempt,
    Confirmation,
    Hypothesis,
    Note,
    QueueItem,
    TrackingState,
)


def _today() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat(timespec='seconds')


class TrackingService:
    """Service layer for tracking operations.
    
    Encapsulates all business logic. CLI commands should be thin wrappers
    around this service.
    """
    
    def __init__(self, state: TrackingState):
        self.state = state
    
    def _mark_updated(self) -> None:
        """Mark state as updated with current timestamp."""
        self.state.updated = _today()
    
    # ── Hypothesis operations ──────────────────────────────────────────────
    
    def add_hypothesis(
        self,
        desc: str,
        priority: int | None = None,
        next_action: str | None = None,
    ) -> Hypothesis:
        """Add a new open hypothesis."""
        hid = self.state.next_hypothesis_id()
        h = Hypothesis(
            id=hid,
            desc=desc,
            status="open",
            priority=priority,
            next_action=next_action,
            created=_today(),
        )
        self.state.hypotheses.append(h)
        self._mark_updated()
        return h
    
    def close_hypothesis(self, hid: str, conclusion: str) -> Hypothesis:
        """Mark a hypothesis as closed (dead end)."""
        h = self.state.get_hypothesis(hid)
        if not h:
            raise HypothesisNotFound(hid)
        h.status = "closed"
        h.conclusion = conclusion
        h.closed = _today()
        self._mark_updated()
        return h
    
    def confirm_hypothesis(
        self,
        hid: str,
        conclusion: str,
        title: str | None = None,
        severity: str | None = None,
        status_val: str = "confirmed",
    ) -> tuple[Hypothesis, Confirmation | None]:
        """Mark a hypothesis as confirmed, optionally creating a confirmation."""
        h = self.state.get_hypothesis(hid)
        if not h:
            raise HypothesisNotFound(hid)
        
        h.status = "confirmed"
        h.conclusion = conclusion
        h.closed = _today()
        self._mark_updated()
        
        confirmation = None
        if title:
            if not severity:
                raise ValueError("severity required when creating a confirmation")
            cid = self.state.next_confirmation_id()
            confirmation = Confirmation(
                id=cid,
                title=title,
                severity=severity,
                status=status_val,
                from_hypothesis=h.id,
            )
            self.state.confirmations.append(confirmation)
        
        return h, confirmation
    
    def reopen_hypothesis(
        self,
        hid: str,
        priority: int = 2,
        next_action: str | None = None,
    ) -> Hypothesis:
        """Reopen a closed or confirmed hypothesis."""
        h = self.state.get_hypothesis(hid)
        if not h:
            raise HypothesisNotFound(hid)
        
        if h.status == "open":
            raise InvalidStatus("hypothesis", h.status, "open")
        
        h.status = "open"
        h.priority = priority
        h.closed = None
        if next_action:
            h.next_action = next_action
        self._mark_updated()
        return h
    
    def update_hypothesis(
        self,
        hid: str,
        desc: str | None = None,
        priority: int | None = None,
        next_action: str | None = None,
    ) -> Hypothesis:
        """Update fields on an existing hypothesis."""
        h = self.state.get_hypothesis(hid)
        if not h:
            raise HypothesisNotFound(hid)
        
        if desc is not None:
            h.desc = desc
        if priority is not None:
            h.priority = priority
        if next_action is not None:
            h.next_action = next_action
        
        self._mark_updated()
        return h
    
    def remove_hypothesis(self, hid: str) -> Hypothesis:
        """Remove a hypothesis."""
        h = self.state.get_hypothesis(hid)
        if not h:
            raise HypothesisNotFound(hid)
        self.state.hypotheses.remove(h)
        self._mark_updated()
        return h
    
    # ── Attempt operations ─────────────────────────────────────────────────
    
    def add_attempt(
        self,
        hid: str,
        payload: str,
        result: str | None = None,
        tag: str | None = None,
        status: str = "fail",
    ) -> Attempt:
        """Record a test attempt under a hypothesis."""
        h = self.state.get_hypothesis(hid)
        if not h:
            raise HypothesisNotFound(hid)
        
        attempt = Attempt(
            payload=payload,
            result=result,
            tag=tag,
            status=status,
            ts=_today(),
        )
        h.attempts.append(attempt)
        self._mark_updated()
        return attempt
    
    # ── Confirmation operations ────────────────────────────────────────────
    
    def update_confirmation(
        self,
        cid: str,
        status: str | None = None,
        notes: str | None = None,
    ) -> Confirmation:
        """Update a confirmation."""
        c = self.state.get_confirmation(cid)
        if not c:
            raise ConfirmationNotFound(cid)
        
        if status:
            c.status = status
        if notes:
            c.notes = notes
        
        self._mark_updated()
        return c
    
    def remove_confirmation(self, cid: str) -> Confirmation:
        """Remove a confirmation."""
        c = self.state.get_confirmation(cid)
        if not c:
            raise ConfirmationNotFound(cid)
        self.state.confirmations.remove(c)
        self._mark_updated()
        return c
    
    # ── Queue operations ───────────────────────────────────────────────────
    
    def add_queue_item(self, queue: str, desc: str) -> QueueItem:
        """Add an item to a work queue."""
        qid = self.state.next_queue_item_id()
        item = QueueItem(
            id=qid,
            queue=queue,
            desc=desc,
            created=_today(),
        )
        if queue not in self.state.queues:
            self.state.queues[queue] = []
        self.state.queues[queue].append(item)
        self._mark_updated()
        return item
    
    def bulk_add_queue_items(self, queue: str, descriptions: list[str]) -> list[QueueItem]:
        """Bulk-add queue items from a list of descriptions."""
        if queue not in self.state.queues:
            self.state.queues[queue] = []
        
        items = []
        for desc in descriptions:
            qid = self.state.next_queue_item_id()
            item = QueueItem(
                id=qid,
                queue=queue,
                desc=desc,
                created=_today(),
            )
            self.state.queues[queue].append(item)
            items.append(item)
        
        self._mark_updated()
        return items
    
    def mark_queue_item_done(
        self,
        qid: str,
        hyp_id: str | None = None,
    ) -> QueueItem:
        """Mark a queue item as done."""
        item = self.state.get_queue_item(qid)
        if not item:
            raise QueueItemNotFound(qid)
        
        item.status = "done"
        item.hyp_id = hyp_id
        item.done_ts = _today()
        self._mark_updated()
        return item
    
    def skip_queue_item(self, qid: str) -> QueueItem:
        """Mark a queue item as skipped."""
        item = self.state.get_queue_item(qid)
        if not item:
            raise QueueItemNotFound(qid)
        
        item.status = "skipped"
        item.done_ts = _today()
        self._mark_updated()
        return item
    
    # ── Note operations ────────────────────────────────────────────────────
    
    def add_note(self, text: str, hyp_id: str | None = None) -> Note:
        """Add a free-form note."""
        note = Note(text=text, ts=_today(), hyp_id=hyp_id)
        self.state.notes.append(note)
        self._mark_updated()
        return note
    
    def remove_note(self, index: int) -> Note:
        """Remove a note by 1-based index."""
        if index < 1 or index > len(self.state.notes):
            raise IndexError(f"Note index {index} out of range (1–{len(self.state.notes)})")
        removed = self.state.notes.pop(index - 1)
        self._mark_updated()
        return removed
    
    # ── State operations ───────────────────────────────────────────────────
    
    def set_last_action(self, action: str) -> None:
        """Record the last action taken."""
        self.state.last_action = action
        self._mark_updated()
    
    def set_blocked(self, reason: str) -> None:
        """Mark research as blocked."""
        self.state.blocked_on = reason
        self._mark_updated()
    
    def clear_blocked(self) -> None:
        """Clear blocked status."""
        self.state.blocked_on = None
        self._mark_updated()
