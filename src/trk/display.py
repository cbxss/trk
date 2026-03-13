from __future__ import annotations

from collections import defaultdict

from .state import Attempt, QueueItem, TrackingState

# ── symbols ──────────────────────────────────────────────────────────────────
ATTEMPT_SYMS = {"pass": "✓", "fail": "✗", "partial": "~"}
SEV_SHORT = {"critical": "CRIT", "high": "HIGH", "medium": "MED", "low": "LOW", "info": "INFO"}


def _tries_line(attempts: list[Attempt]) -> str:
    """Compact single-line tries grouped by tag: [tag]: pay✓  pay✗ | [tag2]: ..."""
    groups: dict[str, list[Attempt]] = defaultdict(list)
    for a in attempts:
        groups[a.tag or ""].append(a)
    parts = []
    for tag, group in groups.items():
        items = "  ".join(f"{a.payload}{ATTEMPT_SYMS.get(a.status, '?')}" for a in group)
        label = f"[{tag}]" if tag else "[untagged]"
        parts.append(f"{label}: {items}")
    return " | ".join(parts)


def show(state: TrackingState, show_closed: bool = False, show_confirmations: bool = False, limit: int | None = None) -> None:
    """
    Compact, AI-optimised output.

    Design goals:
    - Full fidelity on OPEN items (no truncation — agent needs full context)
    - Minimal footprint on CLOSED/resolved items (summary only by default)
    - One logical item per line where possible
    - show_closed=True adds closed hypothesis details + notes
    - limit=N shows only the N most recent open items
    """
    lines = []

    # ── header ────────────────────────────────────────────────────────────────
    lines.append(f"TARGET: {state.target}  UPDATED: {state.updated}")
    if state.blocked_on:
        lines.append(f"BLOCKED: {state.blocked_on}")

    # last_action — full text, critical session context for AI
    if state.last_action:
        lines.append(f"LAST: {state.last_action}")

    # ── notes ─────────────────────────────────────────────────────────────────
    if state.notes:
        lines.append("NOTES:")
        for n in state.notes:
            tag = f" [{n.hyp_id}]" if n.hyp_id else ""
            lines.append(f"  [{n.ts}]{tag} {n.text}")

    # ── confirmations (active findings) ───────────────────────────────────────
    active_confirmations = [c for c in state.confirmations if c.status not in ("closed", "false_positive")]
    closed_confirmations = [c for c in state.confirmations if c.status in ("closed", "false_positive")]

    if active_confirmations:
        if show_confirmations:
            lines.append("CONFIRMATIONS:")
            for c in active_confirmations:
                sev = SEV_SHORT.get(c.severity, c.severity.upper())
                line = f"  {c.id}[{sev}|{c.status}] {c.title}"
                if c.from_hypothesis:
                    line += f"  (from {c.from_hypothesis})"
                lines.append(line)
                # Notes inline — no truncation, agents need full notes
                if c.notes:
                    lines.append(f"    notes: {c.notes}")
        else:
            ids = "  ".join(
                f"{c.id}[{SEV_SHORT.get(c.severity, c.severity.upper())}]"
                for c in active_confirmations
            )
            lines.append(f"CONFIRMATIONS({len(active_confirmations)}): {ids}  (use --confirmations for details)")

    if closed_confirmations:
        ids = "  ".join(
            f"{c.id}[{SEV_SHORT.get(c.severity, c.severity)}|{c.status}]"
            for c in closed_confirmations
        )
        lines.append(f"CONFIRMATIONS(closed/fp): {ids}")

    # ── open hypotheses ────────────────────────────────────────────────────────
    all_open = [h for h in state.hypotheses if h.status == "open"]
    
    # Apply limit if specified (show most recent N items by ID)
    total_open = len(all_open)
    if limit and limit < total_open:
        # Sort by numeric ID descending to get most recent, take first N
        def id_num(h):
            return int(h.id[1:]) if h.id[1:].isdigit() else 0
        recent = sorted(all_open, key=id_num, reverse=True)[:limit]
        # Then sort by priority for display
        open_hyps = sorted(recent, key=lambda h: (h.priority or 999, h.id))
    else:
        # Normal priority-sorted view
        open_hyps = sorted(all_open, key=lambda h: (h.priority or 999, h.id))
        
    if open_hyps:
        header = "OPEN HYPOTHESES (by priority):"
        if limit and limit < total_open:
            header += f" [showing {limit} of {total_open}]"
        lines.append(header)
        for h in open_hyps:
            pri = f"P{h.priority}" if h.priority else "--"
            # Full desc — no truncation
            lines.append(f"  {h.id}[{pri}] {h.desc}")
            if h.next_action:
                lines.append(f"    next: {h.next_action}")
            if h.attempts:
                lines.append(f"    tries: {_tries_line(h.attempts)}")

    # ── closed summary ────────────────────────────────────────────────────────
    closed = [h for h in state.hypotheses if h.status in ("closed", "confirmed")]
    if closed:
        ids = " ".join(h.id for h in closed)
        lines.append(f"CLOSED({len(closed)}): {ids}   (run `trk show --closed` for details)")

    # ── closed details (opt-in) ───────────────────────────────────────────────
    if show_closed and closed:
        lines.append("CLOSED DETAILS:")
        for h in closed:
            lines.append(f"  {h.id}[{h.status}] {h.desc}")
            if h.conclusion:
                lines.append(f"    conclusion: {h.conclusion}")
            if h.attempts:
                lines.append(f"    tries: {_tries_line(h.attempts)}")

    # ── work queues ───────────────────────────────────────────────────────────
    if state.queues:
        for qname, items in state.queues.items():
            pending = [i for i in items if i.status == "pending"]
            if not pending:
                continue
            done = [i for i in items if i.status == "done"]
            skipped = [i for i in items if i.status == "skipped"]
            total = len(items)
            n_done = len(done) + len(skipped)
            lines.append(f"QUEUE: {qname} [{n_done}/{total} done, {len(pending)} pending]")
            lines.append(f"  next: {pending[0].id} {pending[0].desc}")
            if len(pending) > 1:
                lines.append(f"  +{len(pending) - 1} more pending — `hyp qshow -q {qname}`")

    print("\n".join(lines))


def show_queue(items: list[QueueItem], queue_name: str) -> None:
    """Show a single queue for `hyp qshow -q <name>`."""
    SYMS = {"pending": "[ ]", "done": "[x]", "skipped": "[-]"}
    pending = sum(1 for i in items if i.status == "pending")
    total = len(items)
    print(f"## {queue_name}  [{total - pending}/{total} done]")
    for item in items:
        sym = SYMS.get(item.status, "[ ]")
        hyp_str = f"  →{item.hyp_id}" if item.hyp_id else ""
        print(f"  {sym} {item.id}{hyp_str}  {item.desc}")


def show_all_queues(queues: dict[str, list[QueueItem]]) -> None:
    """Show all queues for `hyp qshow`."""
    SYMS = {"pending": "[ ]", "done": "[x]", "skipped": "[-]"}
    for qname, items in queues.items():
        pending = sum(1 for i in items if i.status == "pending")
        total = len(items)
        print(f"## {qname}  [{total - pending}/{total} done]")
        for item in items:
            sym = SYMS.get(item.status, "[ ]")
            hyp_str = f"  →{item.hyp_id}" if item.hyp_id else ""
            print(f"  {sym} {item.id}{hyp_str}  {item.desc}")
        print()
