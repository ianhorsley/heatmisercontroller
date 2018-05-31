class hmError(RuntimeError):
    pass
    
class hmResponseError(hmError):
    pass
    
class hmResponseErrorCRC(hmResponseError):
    pass
    
class hmControllerTimeError(hmError):
    pass