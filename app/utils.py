import logging
import re

logger = logging.getLogger(__name__)


def get_vm_console_query_params(query: str) -> tuple:
    """Извлекает параметры запроса для
    получения веб-консоли управления ВМ."""
    host, = re.findall(r'host=(.[^&]*)', query)
    port, = re.findall(r'port=(.[^&]*)', query)
    ticket, = re.findall(r'ticket=(.[^&]*)', query)
    return host, port, ticket


def get_vm_console_link(
        *,
        hostname: str,
        host: str,
        port: str,
        ticket: str
) -> str:
    """Формирует ссылку на консоль управления ВМ"""
    return f'{hostname}/console?host={host}&port={port}&ticket={ticket}'
