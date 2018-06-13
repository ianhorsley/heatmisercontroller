# Catch all, not used directly in code
class hmError(RuntimeError):
    pass

# Raise this when response from a device is wrong
class hmResponseError(hmError):
    pass

# Specifically when CRC fails check. This is the most common response error.
class hmResponseErrorCRC(hmResponseError):
    pass

# Raise this when controller time is outside of boundarys
class hmControllerTimeError(hmError):
    pass
    
# Raise this when init fails.
class HeatmiserControllerSetupInitError(hmError):
    pass