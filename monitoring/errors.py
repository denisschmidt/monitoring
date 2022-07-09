class LogError(Exception):
    def __init__(self, message, errors=None) -> None:
        super().__init__(message)
        self.errors = errors


class LogWindowError(Exception):
    def __init__(self, message, errors=None) -> None:
        super().__init__(message)
        self.errors = errors


class TimeLineError(Exception):
    def __init__(self, message, errors=None) -> None:
        super().__init__(message)
        self.errors = errors
