"""In-memory LIFO intent state machine for multi-turn interruptions.

A suspended intent keeps its context until the nested task completes. The
implementation is deterministic and does not perform classification or I/O.
"""
from copy import deepcopy
from typing import Any, Dict, List, Optional
from uuid import uuid4


class IntentStack:
    """Manage nested intents with explicit push, resume, and snapshot actions."""

    def __init__(self, max_depth: int = 64):
        if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 1:
            raise ValueError("max_depth must be a positive integer")
        self.max_depth = max_depth
        self._frames: List[Dict[str, Any]] = []

    @property
    def active(self) -> Optional[Dict[str, Any]]:
        return deepcopy(self._frames[-1]) if self._frames else None

    @property
    def depth(self) -> int:
        return len(self._frames)

    def push(self, intent: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not isinstance(intent, str) or not 0 < len(intent.strip()) <= 250:
            raise ValueError("intent must contain 1-250 characters")
        if context is None:
            context = {}
        if not isinstance(context, dict):
            raise ValueError("context must be a dictionary")
        if self.depth >= self.max_depth:
            raise OverflowError("intent stack is full")
        if self._frames:
            self._frames[-1]["state"] = "suspended"
        frame = {
            "id": uuid4().hex,
            "intent": intent.strip(),
            "context": deepcopy(context),
            "state": "active",
        }
        self._frames.append(frame)
        return deepcopy(frame)

    def pop(self) -> Dict[str, Any]:
        if not self._frames:
            raise IndexError("cannot resume an empty stack")
        finished = self._frames.pop()
        finished["state"] = "completed"
        if self._frames:
            self._frames[-1]["state"] = "active"
        return deepcopy(finished)

    def clear(self) -> None:
        self._frames.clear()

    def snapshot(self) -> Dict[str, Any]:
        return {"version": 1, "frames": deepcopy(self._frames)}

    def restore(self, snapshot: Dict[str, Any]) -> None:
        if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
            raise ValueError("unsupported snapshot")
        frames = snapshot.get("frames")
        if not isinstance(frames, list) or len(frames) > self.max_depth:
            raise ValueError("invalid snapshot depth")
        ids = set()
        for i, frame in enumerate(frames):
            if not isinstance(frame, dict) or set(frame) != {"id", "intent", "context", "state"}:
                raise ValueError("invalid intent frame")
            identity, intent = frame["id"], frame["intent"]
            if not isinstance(identity, str) or not identity or identity in ids:
                raise ValueError("invalid or duplicate frame id")
            ids.add(identity)
            if not isinstance(intent, str) or not 0 < len(intent.strip()) <= 250:
                raise ValueError("invalid frame intent")
            if not isinstance(frame["context"], dict):
                raise ValueError("invalid frame context")
            expected = "active" if i == len(frames) - 1 else "suspended"
            if frame["state"] != expected:
                raise ValueError("invalid intent state order")
        self._frames = deepcopy(frames)
