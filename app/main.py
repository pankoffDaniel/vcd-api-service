import logging.config

from fastapi import FastAPI

from app.core.settings.config import (
    AppConfig,
    DBConfig,
    VCDConfig,
    CeleryConfig,
    get_config
)
from app.providers.dependencies import DependenciesProvider
from app.providers.stubs import (
    VCDServiceStub,
    Jinja2TemplatesStub,
    VCDControllerStub,
    DBSessionStub,
    CeleryStub,
    VMRepositoryStub,
    SettingsRepositoryStub,
    TemplateCatalogRepositoryStub
)


def get_fastapi_application(
        *,
        app_config: AppConfig,
        db_config: DBConfig,
        vcd_config: VCDConfig,
        celery_config: CeleryConfig
) -> FastAPI:
    dependencies_provider = DependenciesProvider(
        app_config=app_config,
        db_config=db_config,
        vcd_config=vcd_config,
        celery_config=celery_config
    )
    application = dependencies_provider.provide_fastapi_application()
    application.dependency_overrides = {
        DBSessionStub: dependencies_provider.provide_db_session,
        Jinja2TemplatesStub: dependencies_provider.provide_jinja2_templates,
        CeleryStub: dependencies_provider.async_provide_celery_application,
        VMRepositoryStub: dependencies_provider.provide_vm_repository,
        TemplateCatalogRepositoryStub: dependencies_provider.provide_template_catalog_repository,
        SettingsRepositoryStub: dependencies_provider.provide_settings_repository,
        VCDServiceStub: dependencies_provider.provide_vcd_service,
        VCDControllerStub: dependencies_provider.provide_vcd_controller
    }
    return application


config = get_config()
logging.config.dictConfig(config['logger'])
app = get_fastapi_application(
    app_config=AppConfig(**config['app']),
    db_config=DBConfig(),
    celery_config=CeleryConfig(**config['celery']),
    vcd_config=VCDConfig(),
)
