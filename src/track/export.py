from __future__ import annotations

import json
from collections import defaultdict

from .state import Attempt, QueueItem, TrackingState

ATTEMPT_SYMS = {"pass": "✓", "fail": "✗", "partial": "~"}


def _attempts_md(attempts: list[Attempt]) -> list[str]:
    lines = []
    if not attempts:
        return lines
    groups: dict[str, list[Attempt]] = defaultdict(list)
    for a in attempts:
        groups[a.tag or ""].append(a)
    for tag, group in groups.items():
        tag_label = f"[{tag}]" if tag else "[untagged]"
        parts = []
        for a in group:
            sym = ATTEMPT_SYMS.get(a.status, "?")
            entry = f"`{a.payload}`{sym}"
            if a.result:
                entry += f" ({a.result})"
            parts.append(entry)
        lines.append(f"  - Tries {tag_label}: " + "  ".join(parts))
    return lines


def to_markdown(state: TrackingState) -> str:
    lines = []
    lines.append(f"# Security Research: {state.target}")
    parts = [f"**Updated:** {state.updated}"]
    if state.last_action:
        parts.append(f"**Last Action:** {state.last_action}")
    lines.append(" | ".join(parts))

    if state.blocked_on:
        lines.append(f"\n> **BLOCKED:** {state.blocked_on}")

    # Notes
    if state.notes:
        lines.append("\n## Notes")
        for n in state.notes:
            lines.append(f"- [{n.ts}] {n.text}")

    # Confirmations
    if state.confirmations:
        lines.append("\n## Confirmations")
        for c in state.confirmations:
            lines.append(f"\n### {c.id} [{c.severity.upper()}] {c.title}")
            lines.append(f"- **Status:** {c.status}")
            if c.notes:
                lines.append(f"- **Notes:** {c.notes}")
            if c.from_hypothesis:
                lines.append(f"- **From:** {c.from_hypothesis}")

    # Open hypotheses
    open_hyps = [h for h in state.hypotheses if h.status == "open"]
    open_hyps.sort(key=lambda h: (h.priority or 999, h.id))
    if open_hyps:
        lines.append("\n## Open Hypotheses")
        for h in open_hyps:
            pri = f"[P{h.priority}] " if h.priority else ""
            lines.append(f"\n### {h.id} {pri}{h.desc}")
            if h.next_action:
                lines.append(f"- **Next:** {h.next_action}")
            if h.created:
                lines.append(f"- **Created:** {h.created}")
            lines.extend(_attempts_md(h.attempts))

    # Closed hypotheses
    closed_hyps = [h for h in state.hypotheses if h.status in ("closed", "confirmed")]
    if closed_hyps:
        lines.append("\n## Closed Hypotheses")
        for h in closed_hyps:
            lines.append(f"\n### {h.id} {h.desc}")
            lines.append(f"- **Status:** {h.status}")
            if h.conclusion:
                lines.append(f"- **Conclusion:** {h.conclusion}")
            if h.closed:
                lines.append(f"- **Closed:** {h.closed}")
            lines.extend(_attempts_md(h.attempts))

    # Work queues
    if state.queues:
        lines.append("\n## Work Queues")
        SYMS = {"pending": "[ ]", "done": "[x]", "skipped": "[-]"}
        for qname, items in state.queues.items():
            done_count = sum(1 for i in items if i.status != "pending")
            lines.append(f"\n### {qname}  [{done_count}/{len(items)} done]")
            for item in items:
                sym = SYMS.get(item.status, "[ ]")
                hyp_str = f" →{item.hyp_id}" if item.hyp_id else ""
                lines.append(f"- {sym} **{item.id}**{hyp_str}  {item.desc}")

    return "\n".join(lines) + "\n"


def to_json(state: TrackingState) -> str:
    return json.dumps(state.to_dict(), indent=2) + "\n"
