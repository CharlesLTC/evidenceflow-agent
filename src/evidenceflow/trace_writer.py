import json
import re
from datetime import UTC, datetime
from pathlib import Path


def utc_now():
    return datetime.now(UTC).isoformat()


SECRET_PATTERN = re.compile(
    r"(?:sk-[a-zA-Z0-9_-]{16,}|gh[pousr]_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,})"
)


def redact(value):
    if isinstance(value, dict):
        return {
            k: (
                "[REDACTED]"
                if k.lower() in ("api_key", "authorization", "access_token")
                else redact(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return SECRET_PATTERN.sub("[REDACTED]", value) if isinstance(value, str) else value


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact(value), ensure_ascii=False, indent=2), encoding="utf-8")


class TraceWriter:
    def __init__(self, root, trace_id, mode, model_name):
        self.root, self.trace_id, self.mode, self.model_name = root, trace_id, mode, model_name
        self.events = []

    def event(self, kind, **values):
        self.events.append(
            redact(
                {
                    "kind": kind,
                    "step": len(self.events) + 1,
                    "trace_id": self.trace_id,
                    "mode": self.mode,
                    "model_name": self.model_name,
                    "timestamp": utc_now(),
                    **values,
                }
            )
        )

    def finish(self, result):
        payload = {
            "trace_id": self.trace_id,
            "mode": self.mode,
            "model_name": self.model_name,
            "events": self.events,
            "result": result.model_dump(),
        }
        write_json(self.root / f"examples/traces/{self.mode}/{self.trace_id}.json", payload)
        write_json(
            self.root / f"examples/outputs/{self.mode}/{self.trace_id}.json", result.model_dump()
        )
