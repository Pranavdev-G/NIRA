"""
Injectable Time Provider and Virtual Clock for NIRA Live.
Amazon Developer Hackathon 2026.

Supports:
- Real-time production operation via SystemTimeProvider
- Fast deterministic unit and scenario testing via TestClock (Phase 67)
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Optional


class TimeProvider(ABC):
    """Abstract interface for querying current system or virtual simulation time."""

    @abstractmethod
    def now(self) -> datetime:
        """Returns current timezone-aware UTC datetime."""
        pass

    @abstractmethod
    def now_iso(self) -> str:
        """Returns ISO-8601 UTC formatted string."""
        pass

    @abstractmethod
    def time(self) -> float:
        """Returns current unix timestamp in epoch seconds."""
        pass

    @abstractmethod
    def sleep(self, seconds: float):
        """Sleeps or advances virtual clock."""
        pass


class SystemTimeProvider(TimeProvider):
    """Production time provider using host system clock."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def time(self) -> float:
        return time.time()

    def sleep(self, seconds: float):
        time.sleep(seconds)


class TestClock(TimeProvider):
    """
    Virtual time provider for deterministic tests (Phase 67).
    Allows advancing time instantly (e.g. clock.advance(seconds=900) for a 15-minute dwell test)
    without actual wall-clock sleeping.
    """
    __test__ = False

    def __init__(self, start_time: Optional[datetime] = None):
        if start_time is None:
            # Default to a fixed baseline UTC datetime (e.g., 10:00:00 UTC)
            self._current_time = datetime(2026, 10, 23, 10, 0, 0, tzinfo=timezone.utc)
        else:
            if start_time.tzinfo is None:
                self._current_time = start_time.replace(tzinfo=timezone.utc)
            else:
                self._current_time = start_time

    def now(self) -> datetime:
        return self._current_time

    def now_iso(self) -> str:
        return self._current_time.isoformat()

    def time(self) -> float:
        return self._current_time.timestamp()

    def advance(self, seconds: float) -> datetime:
        """Advances the virtual clock forward by the given number of seconds."""
        self._current_time += timedelta(seconds=seconds)
        return self._current_time

    def set_time(self, new_time: datetime):
        """Sets the virtual clock to a specific datetime."""
        if new_time.tzinfo is None:
            self._current_time = new_time.replace(tzinfo=timezone.utc)
        else:
            self._current_time = new_time

    def sleep(self, seconds: float):
        """Simulates sleep by immediately advancing virtual time."""
        self.advance(seconds)


# Global singleton time provider
_current_provider: TimeProvider = SystemTimeProvider()


def get_time_provider() -> TimeProvider:
    """Returns the currently active TimeProvider (SystemTimeProvider by default)."""
    global _current_provider
    return _current_provider


def set_time_provider(provider: TimeProvider):
    """Sets an alternative TimeProvider (e.g., TestClock for unit tests)."""
    global _current_provider
    _current_provider = provider


def reset_time_provider():
    """Resets to default SystemTimeProvider."""
    global _current_provider
    _current_provider = SystemTimeProvider()
