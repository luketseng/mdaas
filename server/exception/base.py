class BaseError(Exception):
    pass


class FileNotExistError(BaseError):
    pass


class ItemNotExistError(BaseError):
    pass


class FileTypeError(BaseError):
    pass


class DataTypeError(BaseError):
    pass


class ObjectAttributeError(BaseError):
    pass


class InvalidDataError(BaseError):
    pass


class UnauthorizedError(BaseError):
    pass


class DataDeletedError(BaseError):
    pass


class KeyError(BaseError):
    pass


class ValueError(BaseError):
    pass

