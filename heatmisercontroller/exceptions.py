"""Contains all exceptions used by package"""

class HeatmiserError(RuntimeError):
    """Catch all, not used directly in code."""

class HeatmiserResponseError(HeatmiserError):
    """Raise this when response from a device is wrong."""

class HeatmiserResponseErrorCRC(HeatmiserResponseError):
    """Specifically when CRC fails check. This is the most common response error."""

class HeatmiserControllerSensorError(HeatmiserResponseError):
    """Raise this when controller reports sensor error."""

class HeatmiserControllerTimeError(HeatmiserError):
    """Raise this when controller time is outside of acceptable limits."""

class HeatmiserControllerSetupInitError(HeatmiserError):
    """Raise this when init fails."""
