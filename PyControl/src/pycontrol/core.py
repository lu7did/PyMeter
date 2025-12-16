"""Core module for PyControl.

Provides a simple PyControl class following OOP principles with basic
error handling and docstrings compatible with PEP257.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class PyControlError(Exception):
    """Base exception for PyControl-related errors."""


@dataclass
class PyControl:
    """Main controller class for PyControl.

    Attributes:
        name: Friendly name for the controller.
        level: Operational level, integer between 0 and 10.
    """

    name: str = "PyControl"
    level: int = 0

    def __post_init__(self) -> None:
        """Validate initial state after dataclass initialization."""
        if not isinstance(self.name, str) or not self.name:
            raise PyControlError("name must be a non-empty string")
        if not isinstance(self.level, int) or not (0 <= self.level <= 10):
            raise PyControlError("level must be integer in [0,10]")

    def set_level(self, level: int) -> None:
        """Set the operational level.

        Raises:
            PyControlError: If level is out of bounds.
        """
        if not isinstance(level, int):
            raise PyControlError("level must be an integer")
        if level < 0 or level > 10:
            raise PyControlError("level must be between 0 and 10")
        self.level = level

    def status(self) -> dict:
        """Return a serializable status representation."""
        return {"name": self.name, "level": self.level}

    def increment(self, step: int = 1) -> int:
        """Increment level by step and return new level.

        Ensures level stays within bounds [0,10].
        """
        if not isinstance(step, int):
            raise PyControlError("step must be integer")
        new = min(10, self.level + step)
        self.level = new
        return self.level

    def reset(self) -> None:
        """Reset the controller to default level (0)."""
        self.level = 0
