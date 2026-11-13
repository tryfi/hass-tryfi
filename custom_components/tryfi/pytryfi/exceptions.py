class Error(Exception):
    """base exception class"""


class TryFiError(Exception):
    """Generic error for TryFi"""


class RemoteApiError(TryFiError):
    """tryfi.com returned an unexpected result"""


class ApiNotAuthorizedError(TryFiError):
    """tryfi.com reports not authorized"""

    def __init__(self, message: str = "tryfi.com reports not authorized"):
        """Always carry a message; str() of this error is never empty.

        Callers interpolate the error into log lines, so a bare raise leaves
        the line ending at its colon.
        """
        super().__init__(message)
