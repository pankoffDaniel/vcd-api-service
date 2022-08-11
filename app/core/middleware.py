import logging

from fastapi import Response, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.settings import constants

logger = logging.getLogger(__name__)


class BaseExceptionMiddleware(BaseHTTPMiddleware):
    """Обрабатывает и логирует неожиданные исключения."""

    async def dispatch(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ) -> Response:
        """Обработка любой необработанной ошибки."""
        try:
            return await call_next(request)
        except Exception:
            logger.error('Необработанная ошибка', exc_info=True)
            return Response(
                content=constants.INTERNAL_SERVER_ERROR_MESSAGE,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
