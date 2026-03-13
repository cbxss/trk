"""Custom exceptions for trk."""
from __future__ import annotations


class TrkError(Exception):
    """Base exception for all trk errors."""


class ValidationError(TrkError):
    """Invalid data provided."""


class NotFoundError(TrkError):
    """Resource not found."""


class HypothesisNotFound(NotFoundError):
    """Hypothesis ID not found."""
    
    def __init__(self, hid: str):
        self.hid = hid
        super().__init__(f"Hypothesis '{hid}' not found")


class ConfirmationNotFound(NotFoundError):
    """Confirmation ID not found."""
    
    def __init__(self, cid: str):
        self.cid = cid
        super().__init__(f"Confirmation '{cid}' not found")


class QueueItemNotFound(NotFoundError):
    """Queue item ID not found."""
    
    def __init__(self, qid: str):
        self.qid = qid
        super().__init__(f"Queue item '{qid}' not found")


class TargetNotFound(NotFoundError):
    """Target state file not found."""
    
    def __init__(self, target: str):
        self.target = target
        super().__init__(f"No state file for target '{target}'. Run: trk init {target}")


class TargetAlreadyExists(TrkError):
    """Target already initialized."""
    
    def __init__(self, target: str, path: str):
        self.target = target
        self.path = path
        super().__init__(f"Target '{target}' already exists at {path}")


class NoTargetSpecified(TrkError):
    """No target specified and none could be inferred."""
    
    def __init__(self):
        super().__init__(
            "No target specified. Use -t/--target, set HYP_TARGET, or run from a directory with state.json"
        )


class InvalidStatus(ValidationError):
    """Invalid status transition."""
    
    def __init__(self, item_type: str, current: str, new: str):
        super().__init__(f"Cannot change {item_type} status from '{current}' to '{new}'")
