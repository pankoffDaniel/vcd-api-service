import logging

from fastapi import APIRouter, Depends, Request
from fastapi import status
from fastapi.templating import Jinja2Templates

from app.core.settings import constants
from app.exceptions import QueryParamsException
from app.providers.stubs import (
    Jinja2TemplatesStub
)
from app.utils import get_vm_console_query_params

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/console')
async def vm_console(
        request: Request,
        templates: Jinja2Templates = Depends(Jinja2TemplatesStub)
) -> Jinja2Templates.TemplateResponse:
    """Обработчик рендера шаблона
    с веб-консолью управления ВМ."""
    try:
        host, port, ticket = get_vm_console_query_params(request.url.query)
    except ValueError:
        logger.error(
            'Неверные параметры запроса для извлечения host, port и ticket',
            {'query': request.url.query}
        )
        raise QueryParamsException(
            content=constants.INVALID_VM_CONSOLE_PARAMS_MESSAGE,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    return templates.TemplateResponse(
        'vm-console.html', {
            'request': request,
            'hostname': host,
            'port': port,
            'ticket': ticket
        })
