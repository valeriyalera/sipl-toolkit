from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .ast_nodes import SourceSpan


@dataclass
class TraceEvent:
    event_type: str
    event_index: int
    span: Optional[Dict[str, int]] = None
    details: Optional[Dict[str, Any]] = None
    state: Optional[Dict[str, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_index": self.event_index,
            "span": self.span,
            "details": self.details or {},
            "state": self.state or {}
        }


class ExecutionTracer:
    """Збирає хронологію виконання програми для відлагодження та візуалізації."""

    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events: List[TraceEvent] = []
        self._event_counter = 0
        self.is_truncated = False

    def clear(self):
        self.events.clear()
        self._event_counter = 0
        self.is_truncated = False

    def _next_index(self) -> int:
        self._event_counter += 1
        return self._event_counter

    def _span_to_dict(self, span: Optional[SourceSpan]) -> Optional[Dict[str, int]]:
        if span is None:
            return None
        return {
            "line": span.line,
            "column": span.column,
            "end_line": span.end_line,
            "end_column": span.end_column
        }

    def _add_event(self, event: TraceEvent):
        if len(self.events) < self.max_events:
            self.events.append(event)
        else:
            self.is_truncated = True

    def emit_before_stmt(self, stmt_name: str, span: Optional[SourceSpan], current_state: Dict[str, int]):
        self._add_event(
            TraceEvent(
                event_type="BeforeStatement",
                event_index=self._next_index(),
                span=self._span_to_dict(span),
                details={"statement": stmt_name},
                state=dict(current_state)
            )
        )

    def emit_after_stmt(self, stmt_name: str, span: Optional[SourceSpan], current_state: Dict[str, int]):
        self._add_event(
            TraceEvent(
                event_type="AfterStatement",
                event_index=self._next_index(),
                span=self._span_to_dict(span),
                details={"statement": stmt_name},
                state=dict(current_state)
            )
        )

    def emit_var_change(
        self,
        var: str,
        old_val: Optional[int],
        new_val: int,
        current_state: Dict[str, int],
        span: Optional[SourceSpan]
    ):
        self._add_event(
            TraceEvent(
                event_type="VariableChange",
                event_index=self._next_index(),
                span=self._span_to_dict(span),
                details={"var": var, "old_value": old_val, "new_value": new_val},
                state=dict(current_state)
            )
        )

    def emit_condition_check(
        self,
        cond_repr: str,
        result: bool,
        origin: str,
        span: Optional[SourceSpan],
        current_state: Dict[str, int]
    ):
        self._add_event(
            TraceEvent(
                event_type="ConditionCheck",
                event_index=self._next_index(),
                span=self._span_to_dict(span),
                details={"condition": cond_repr, "result": result, "origin": origin},
                state=dict(current_state)
            )
        )

    def emit_error(self, error_type: str, message: str, current_state: Dict[str, int]):
        self._add_event(
            TraceEvent(
                event_type="ProgramError",
                event_index=self._next_index(),
                span=None,
                details={"error_type": error_type, "message": message},
                state=dict(current_state)
            )
        )

    def emit_finished(self, final_state: Dict[str, int], total_steps: int):
        self._add_event(
            TraceEvent(
                event_type="ProgramFinished",
                event_index=self._next_index(),
                span=None,
                details={"total_steps": total_steps, "total_events": self._event_counter},
                state=dict(final_state)
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "events": [e.to_dict() for e in self.events],
            "total_events": self._event_counter,
            "truncated": self.is_truncated
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
