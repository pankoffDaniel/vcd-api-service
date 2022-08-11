import os.path
from typing import Any, MutableMapping

import toml
from pydantic import (
    BaseSettings, PostgresDsn,
    AmqpDsn, HttpUrl
)

from app.core.settings import constants


class DBConfig(BaseSettings):
    """Конфигурация БД."""
    url: PostgresDsn

    class Config:
        env_prefix = 'postgres_'


class CeleryConfig(BaseSettings):
    """Конфигурация Celery."""
    broker_url: AmqpDsn
    beat_schedule: dict | None

    class Config:
        env_prefix = 'celery_'


class VCDConfig(BaseSettings):
    """Конфигурация vCD API."""
    hostname: HttpUrl
    api_version: str
    organization: str
    username: str
    password: str

    class Config:
        env_prefix = 'vcd_'


class AppConfig(BaseSettings):
    """Конфигурация приложения."""
    debug: bool
    hostname: HttpUrl
    title: str
    description: str
    version: str
    api_prefix: str

    @property
    def fastapi_kwargs(self) -> dict[str, Any]:
        return {
            'debug': self.debug,
            'title': self.title,
            'description': self.description,
            'version': self.version,
        }


def get_config() -> MutableMapping:
    """Сначала пробует прочитать дев-конфиг,
    но если его нет, то читает прод-конфиг."""
    if os.path.exists(constants.DEVELOPMENT_CONFIG_PATH):
        filepath = constants.DEVELOPMENT_CONFIG_PATH
    else:
        filepath = constants.PRODUCTION_CONFIG_PATH
    with open(filepath) as file:
        config = toml.load(file)
    return config
