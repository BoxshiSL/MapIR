"""Background worker for local LLM drafting.

Generation can take 30-120s on a CPU model; we run it on a QThread so the UI
stays responsive. The worker is the only piece of MapIR's desktop that uses
threading in v0.4 — existing panels remain synchronous.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from ..llm.drafting import (
    DraftResult,
    draft_district_profile,
    draft_scene_from_brief,
    draft_world_from_brief,
)
from ..llm.providers import LocalLLMProvider
from ..llm.settings import LLMSettings


class LLMWorker(QObject):
    """QObject worker; lives on a QThread.

    Emits ``finished(DraftResult)`` exactly once per ``run_draft`` call. Any
    exception is converted into a failure result so the panel always gets a
    response.
    """

    finished = Signal(object)  # DraftResult — Qt erases the dataclass type

    def __init__(self) -> None:
        super().__init__()
        self._task: str = ""
        self._brief: str = ""
        self._provider: LocalLLMProvider | None = None
        self._settings: LLMSettings | None = None
        self._district_id: str = ""
        self._world_summary: str = ""

    def configure(
        self,
        *,
        task: str,
        brief: str,
        provider: LocalLLMProvider,
        settings: LLMSettings,
        district_id: str = "",
        world_summary: str = "",
    ) -> None:
        self._task = task
        self._brief = brief
        self._provider = provider
        self._settings = settings
        self._district_id = district_id
        self._world_summary = world_summary

    def run_draft(self) -> None:
        if self._provider is None or self._settings is None:
            self.finished.emit(
                DraftResult(
                    ok=False,
                    task=self._task,
                    errors=["Worker not configured"],
                )
            )
            return
        try:
            if self._task == "world":
                result = draft_world_from_brief(self._brief, self._provider, self._settings)
            elif self._task == "scene":
                result = draft_scene_from_brief(self._brief, self._provider, self._settings)
            elif self._task == "district":
                result = draft_district_profile(
                    self._world_summary,
                    self._district_id,
                    self._brief,
                    self._provider,
                    self._settings,
                )
            else:
                result = DraftResult(
                    ok=False,
                    task=self._task,
                    errors=[f"Unknown task {self._task!r}"],
                )
        except Exception as exc:  # noqa: BLE001 — worker must never raise
            result = DraftResult(
                ok=False,
                task=self._task,
                errors=[f"Worker exception: {exc}"],
            )
        self.finished.emit(result)


def make_worker_thread(parent: QObject | None = None) -> tuple[QThread, LLMWorker]:
    """Create a QThread + LLMWorker pair, with worker moved onto the thread."""
    thread = QThread(parent)
    worker = LLMWorker()
    worker.moveToThread(thread)
    return thread, worker
