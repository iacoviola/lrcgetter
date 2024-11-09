class LrcException(Exception):
    pass

class NoMatchFoundException(LrcException):
    pass

class InstrumentalTrackException(LrcException):
    pass

class NoTokenException(LrcException):
    pass
