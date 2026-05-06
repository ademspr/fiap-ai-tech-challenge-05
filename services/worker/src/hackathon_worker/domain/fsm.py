from enum import StrEnum

from hackathon_worker.domain.exceptions import InvalidStateTransitionError


class WorkerJobPhase(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobStateMachine:
    """Simplified state machine for worker-side processing."""

    def __init__(self) -> None:
        self.phase = WorkerJobPhase.PENDING

    def start_processing(self) -> None:
        if self.phase != WorkerJobPhase.PENDING:
            raise InvalidStateTransitionError
        self.phase = WorkerJobPhase.PROCESSING

    def complete(self) -> None:
        if self.phase != WorkerJobPhase.PROCESSING:
            raise InvalidStateTransitionError
        self.phase = WorkerJobPhase.COMPLETED

    def fail(self) -> None:
        if self.phase == WorkerJobPhase.COMPLETED:
            raise InvalidStateTransitionError
        self.phase = WorkerJobPhase.FAILED
