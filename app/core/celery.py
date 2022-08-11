import logging.config
from typing import Callable

from celery import Celery

from app.core.settings.config import (
    AppConfig,
    DBConfig,
    CeleryConfig,
    VCDConfig,
    get_config
)
from app.providers.dependencies import DependenciesProvider
from app.tasks import create_all_vm_statistics


def _create_task(
        application: Celery,
        *,
        function: Callable,
        decorator_data: dict,
        dependencies: dict
) -> None:
    """Создаёт Celery задачу."""
    filled_function = _inject_dependencies_in_function(function, **dependencies)
    application.task(**decorator_data)(filled_function)


def _inject_dependencies_in_function(
        function: Callable,
        **dependencies
) -> Callable:
    """Создаёт заполняющую функцию зависимостями."""

    def fill_function(*args, **kwargs) -> Callable:
        """Заполняет функцию зависимостями."""
        return function(*args, **kwargs, **dependencies)

    return fill_function


def get_celery_application(
        *,
        app_config: AppConfig,
        db_config: DBConfig,
        vcd_config: VCDConfig,
        celery_config: CeleryConfig
) -> Celery:
    """Создаёт приложение Celery."""
    dependencies_provider = DependenciesProvider(
        app_config=app_config,
        db_config=db_config,
        vcd_config=vcd_config,
        celery_config=celery_config
    )
    application = dependencies_provider.sync_provide_celery_application()
    vcd_service_provider = dependencies_provider.provide_vcd_service
    settings_repository_provider = dependencies_provider.provide_settings_repository
    template_catalog_repository_provider = dependencies_provider.provide_template_catalog_repository
    vm_repository_provider = dependencies_provider.provide_vm_repository
    session_provider = dependencies_provider.async_sessionmaker
    _create_task(
        application,
        function=create_all_vm_statistics,
        decorator_data={
            'name': 'create_all_vm_statistics',
        },
        dependencies={
            'session_provider': session_provider,
            'vm_repository_provider': vm_repository_provider,
            'template_catalog_repository_provider': template_catalog_repository_provider,
            'settings_repository_provider': settings_repository_provider,
            'vcd_service_provider': vcd_service_provider,
        }
    )
    return application


config = get_config()
logging.config.dictConfig(config['logger'])
celery = get_celery_application(
    app_config=AppConfig(**config['app']),
    db_config=DBConfig(),
    celery_config=CeleryConfig(**config['celery']),
    vcd_config=VCDConfig(),
)
