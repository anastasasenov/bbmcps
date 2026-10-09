# BBMCPS

class BlackboardError(Exception):
    """
    Base exception for application-level errors.
    """


class NotFoundError(BlackboardError):
    """
    Requested entity does not exist.
    """


class ValidationError(BlackboardError):
    """
    Invalid user/MCP input.
    """


class CycleError(BlackboardError):
    """
    Hierarchy cycle would be created.
    """


class ConflictError(BlackboardError):
    """
    Requested operation conflicts with current state.
    """
