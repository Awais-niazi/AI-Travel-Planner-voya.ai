from __future__ import annotations

from time import monotonic


class AIServiceUnavailable(Exception):
    pass


class AIProtectionService:
    def __init__(self) -> None:
        self._failure_count = 0
        self._open_until = 0.0

    def guard(self) -> None:
        if monotonic() < self._open_until:
            raise AIServiceUnavailable("AI service temporarily unavailable")

    def record_success(self) -> None:
        self._failure_count = 0
        self._open_until = 0.0

    def record_failure(self, threshold: int, cooldown_seconds: int) -> None:
        self._failure_count += 1
        if self._failure_count >= threshold:
            self._open_until = monotonic() + cooldown_seconds

    def reset(self) -> None:
        self._failure_count = 0
        self._open_until = 0.0


ai_protection = AIProtectionService()
