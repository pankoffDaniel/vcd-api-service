from fastapi import Response


class BaseRawException(Exception):
    """Базовый класс сырого исключения."""

    def __init__(self, *, content: str, status_code: int) -> None:
        self.content = content
        self.status_code = status_code


def handle_base_raw_exception(_, exception: BaseRawException) -> Response:
    """Обработчик сырого исключения."""
    return Response(
        content=exception.content,
        status_code=exception.status_code
    )


class JobTypeException(BaseRawException):
    pass


class QueryParamsException(BaseRawException):
    pass


class VMNotFoundException(BaseRawException):
    pass


class TemplateCatalogNotFoundException(BaseRawException):
    pass


class VMPowerStateException(BaseRawException):
    pass


class VCDAuthError(BaseRawException):
    pass


class VCDResourceNotFoundException(BaseRawException):
    pass


class VMCreatingException(BaseRawException):
    pass


class AnotherVMCreatingException(BaseRawException):
    pass


class VCDBadRequestException(BaseRawException):
    pass
