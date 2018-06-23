"""Contains all exceptions used by package"""

class HeatmiserError(RuntimeError):
    """Catch all, not used directly in code."""
    pass

class HeatmiserResponseError(HeatmiserError):
    """Raise this when response from a device is wrong."""
    pass

class HeatmiserResponseErrorCRC(HeatmiserResponseError):
    """Specifically when CRC fails check. This is the most common response error."""
    pass

class HeatmiserControllerTimeError(HeatmiserError):
    """Raise this when controller time is outside of acceptable limits."""
    pass

class HeatmiserControllerSetupInitError(HeatmiserError):
    """Raise this when init fails."""
    pass
