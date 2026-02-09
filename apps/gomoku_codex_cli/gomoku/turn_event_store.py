from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TurnEventStore:
    def __init__(self, event_path: Path):
        self.event_path = Path(event_path)
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.event_path.exists():
            self.event_path.write_text("", encoding="utf-8")

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def clear(self) -> None:
        with self._lock:
            self.event_path.write_text("", encoding="utf-8")

    def append_turn_events(
        self,
        *,
        turn_id: int,
        player: str,
        seq: int | None,
        events: list[dict[str, Any]],
    ) -> None:
        if not events:
            return

        rows: list[str] = []
        for order, event in enumerate(events, start=1):
            payload = {
                "turn_id": turn_id,
                "player": player,
                "seq": seq,
                "order": order,
                "kind": str(event.get("kind", "log")),
                "text": str(event.get("text", "")),
                "ts": event.get("ts") or self._now(),
            }
            rows.append(json.dumps(payload, ensure_ascii=True) + "\n")

        with self._lock:
            with self.event_path.open("a", encoding="utf-8") as file:
                file.writelines(rows)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self.event_path.exists():
                return []
            lines = self.event_path.read_text(encoding="utf-8").splitlines()

        output: list[dict[str, Any]] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                output.append(event)
        return output
