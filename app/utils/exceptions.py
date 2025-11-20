class AuthorizationError(Exception):
    def __init__(self, message, **kwargs):
        super().__init__(message)
        self.extra = kwargs

    def warn_admin(self):
        pass
