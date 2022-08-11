import asyncio
from typing import Awaitable, Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.repositories import (
    VMRepository,
    SettingsRepository,
    TemplateCatalogRepository
)
from app.service import VCDService


class SettingsRepositoryProtocol(Protocol):

    def __call__(
            self,
            session: AsyncSession
    ) -> Awaitable[SettingsRepository]:
        ...


class VMRepositoryProtocol(Protocol):

    def __call__(
            self,
            session: AsyncSession
    ) -> Awaitable[VMRepository]:
        ...


class TemplateCatalogRepositoryProtocol(Protocol):

    def __call__(
            self,
            session: AsyncSession
    ) -> Awaitable[TemplateCatalogRepository]:
        ...


class VCDServiceProtocol(Protocol):

    def __call__(
            self,
            *,
            settings_repository: SettingsRepository,
            template_catalog_repository: TemplateCatalogRepository,
            vm_repository: VMRepository
    ) -> Awaitable[VCDService]:
        ...


def create_all_vm_statistics(
        *,
        session_provider: sessionmaker,
        settings_repository_provider: SettingsRepositoryProtocol,
        template_catalog_repository_provider: TemplateCatalogRepositoryProtocol,
        vm_repository_provider: VMRepositoryProtocol,
        vcd_service_provider: VCDServiceProtocol,
) -> None:
    """Запускает скрипт для сбора статистики потребления ресурсов ВМ."""

    async def execute() -> None:
        async with session_provider() as session:
            vm_repository = await vm_repository_provider(session)
            template_catalog_repository = await template_catalog_repository_provider(session)
            settings_repository = await settings_repository_provider(session)
            vcd_service = await vcd_service_provider(
                settings_repository=settings_repository,
                template_catalog_repository=template_catalog_repository,
                vm_repository=vm_repository
            )
            await vcd_service.setup_client()
            await vcd_service.create_all_vm_statistics()

    loop = asyncio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(execute())
