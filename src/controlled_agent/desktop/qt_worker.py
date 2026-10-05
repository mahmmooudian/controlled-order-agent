from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import (
    QThread,
    Signal,
)


class ApiCallThread(QThread):
    """
    Execute one blocking API operation outside
    the Qt GUI thread.

    Only the returned result or a safe error
    message is emitted back to the UI thread.
    """

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        operation: Callable[[], Any],
        *,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._operation = operation

    def run(self) -> None:
        """
        Run inside the worker thread.
        """

        try:
            result = self._operation()

        except Exception as exc:
            self.failed.emit(
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )
            )
            return

        self.succeeded.emit(
            result
        )