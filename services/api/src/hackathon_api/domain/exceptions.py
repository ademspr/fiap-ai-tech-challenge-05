"""Application-level exceptions for the job domain."""


class JobError(Exception):
    """Base for job-related business errors."""


class JobNotFoundError(JobError):
    """No row for the given job id."""


class ForbiddenJobError(JobError):
    """The job exists but is not visible to the current client."""


class JobServiceError(JobError):
    """
    Create/upload/queue business rule violation.

    These are mapped to HTTP in the public router; ``InsufficientTokensError`` is
    also used in internal completion and mapped there to 402.
    """


class UnsupportedMediaTypeError(JobServiceError):
    """File content type is not in the allow list."""


class PayloadTooLargeError(JobServiceError):
    """Upload exceeds configured byte limit."""


class InsufficientTokensError(JobServiceError):
    """Not enough token balance for the requested operation."""


class MessagingFailedError(JobServiceError):
    """Message broker could not accept the job publish."""


class UnmappedJobServiceError(RuntimeError):
    """
    A :class:`JobServiceError` reached the HTTP layer without a status mapping.

    Treat as a programming error: add the subtype to the router handler.
    """


__all__ = [
    "ForbiddenJobError",
    "InsufficientTokensError",
    "JobError",
    "JobNotFoundError",
    "JobServiceError",
    "MessagingFailedError",
    "PayloadTooLargeError",
    "UnsupportedMediaTypeError",
    "UnmappedJobServiceError",
]
