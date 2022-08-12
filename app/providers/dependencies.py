from pathlib import Path

from celery import Celery
from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession
)
from sqlalchemy.orm import sessionmaker

from app.api import api
from app.api.v1.routers import console, vcd
from app.core.middleware import BaseExceptionMiddleware
from app.core.settings.config import (
    AppConfig,
    DBConfig,
    CeleryConfig,
    VCDConfig
)
from app.exceptions import (
    BaseRawException,
    handle_base_raw_exception
)
from app.providers.stubs import (
    VCDServiceStub,
    DBSessionStub,
    VMRepositoryStub,
    SettingsRepositoryStub,
    TemplateCatalogRepositoryStub
)
from app.repositories import (
    VMRepository,
    SettingsRepository,
    TemplateCatalogRepository
)
from app.service import VCDService, VCDController


class DependenciesProvider:
    """Провайдер зависимостей."""

    def __init__(
            self,
            *,
            app_config: AppConfig,
            db_config: DBConfig,
            celery_config: CeleryConfig,
            vcd_config: VCDConfig
    ) -> None:
        self.app_config = app_config
        self.celery_config = celery_config
        self.vcd_config = vcd_config
        engine = create_async_engine(
            db_config.url,
            echo=self.app_config.debug
        )
        self.async_sessionmaker = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def provide_db_session(self) -> AsyncSession:
        """Создаёт асинхронную сессию БД."""
        async with self.async_sessionmaker() as session:
            yield session

    @staticmethod
    async def provide_vm_repository(
            session: AsyncSession = Depends(DBSessionStub)
    ) -> VMRepository:
        """Создаёт ВМ репозиторий."""
        return VMRepository(session)

    @staticmethod
    async def provide_settings_repository(
            session: AsyncSession = Depends(DBSessionStub)
    ) -> SettingsRepository:
        """Создаёт репозиторий настроек."""
        return SettingsRepository(session)

    @staticmethod
    async def provide_template_catalog_repository(
            session: AsyncSession = Depends(DBSessionStub)
    ) -> TemplateCatalogRepository:
        """Создаёт репозиторий каталога шаблонов."""
        return TemplateCatalogRepository(session)

    @staticmethod
    async def provide_jinja2_templates() -> Jinja2Templates:
        """Создаёт подключение к шаблонам Jinja2."""
        return Jinja2Templates(directory='app/templates/')

    def provide_fastapi_application(self) -> FastAPI:
        """Создаёт приложение FastAPI."""
        application = FastAPI(**self.app_config.fastapi_kwargs)
        application.add_middleware(BaseExceptionMiddleware)
        application.add_exception_handler(BaseRawException, handle_base_raw_exception)
        application.mount(
            path='/static',
            app=StaticFiles(directory=Path('app', 'static')),
            name='static'
        )
        # роутеры, доступные по корневому пути "/"
        application.include_router(vcd.router)
        application.include_router(console.router)
        # версионные роутеры
        application.include_router(
            api.api_router,
            prefix=self.app_config.api_prefix
        )
        return application

    async def async_provide_celery_application(self) -> Celery:
        """Асинхронно создаёт приложение Celery"""
        return Celery('tasks', **self.celery_config.dict())

    def sync_provide_celery_application(self) -> Celery:
        """Синхронно создаёт приложение Celery
        для синхронного потребителя Celery."""
        return Celery('tasks', **self.celery_config.dict())

    async def provide_vcd_service(
            self,
            *,
            settings_repository: SettingsRepository = Depends(SettingsRepositoryStub),
            template_catalog_repository: TemplateCatalogRepository = Depends(TemplateCatalogRepositoryStub),
            vm_repository: VMRepository = Depends(VMRepositoryStub),
    ) -> VCDService:
        """Создаёт сервис vCD."""
        return VCDService(
            app_config=self.app_config,
            vcd_config=self.vcd_config,
            settings_repository=settings_repository,
            template_catalog_repository=template_catalog_repository,
            vm_repository=vm_repository,
        )

    @staticmethod
    async def provide_vcd_controller(
            vcd_service: VCDService = Depends(VCDServiceStub),
    ) -> VCDController:
        """Создаёт контроллер vCD."""
        return VCDController(vcd_service=vcd_service)
