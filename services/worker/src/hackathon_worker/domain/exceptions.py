"""Worker-side domain errors."""


class StateMachineError(Exception):
    """Base for the worker job FSM."""


class InvalidStateTransitionError(StateMachineError):
    """Raised when a transition is not allowed in the current phase."""


class WorkerJobError(Exception):
    """Base for job payload and processing preconditions."""


class MissingDiagramPathError(WorkerJobError):
    """The analyze message had no diagram path."""


__all__ = [
    "InvalidStateTransitionError",
    "MissingDiagramPathError",
    "StateMachineError",
    "WorkerJobError",
]
