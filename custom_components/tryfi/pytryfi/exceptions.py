class Error(Exception):
    """base exception class"""

class TryFiError(Exception):
    """Generic error for TryFi"""

class RemoteApiError(TryFiError):
    """tryfi.com returned an unexpected result"""

class ApiNotAuthorizedError(TryFiError):
    """tryfi.com reports not authorized"""