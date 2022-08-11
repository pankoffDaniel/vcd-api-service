import datetime

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.settings import SettingsModel
from app.db.models.template import TemplateCatalogModel
from app.db.models.vm import VMModel, VMStatisticsModel


class VMRepository:
    """Репозиторий взаимодействия с моделями ВМ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
            self,
            *,
            vm_id: str,
            title: str
    ) -> VMModel:
        """Получает либо создаёт модель ВМ при отсутствии."""
        query = select(VMModel).where(VMModel.vm_id == vm_id)
        result = await self._session.execute(query)
        vm_model = result.scalar_one_or_none()
        if vm_model is None:
            vm_model = VMModel(vm_id=vm_id, title=title)
            self._session.add(vm_model)
            await self._session.commit()
        return vm_model

    async def bulk_create_statistics(
            self,
            vm_statistics_to_create: dict
    ) -> None:
        """Создаёт одновременно множество записей статистики ВМ."""
        bulk_data = []
        created_at = datetime.datetime.now()
        for vm_model_id, statistics in vm_statistics_to_create.items():
            bulk_data.append({
                'vm_id': vm_model_id,
                'statistics': statistics,
                'created_at': created_at
            })
        query = insert(VMStatisticsModel).values(bulk_data)
        await self._session.execute(query)
        await self._session.commit()


class SettingsRepository:
    """Репозиторий взаимодействия с vCD."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> SettingsModel | None:
        """Получает либо создаёт модель настроек при отсутствии."""
        query = select(SettingsModel)
        result = await self._session.execute(query)
        settings_model = result.scalar_one_or_none()
        if settings_model is None:
            settings_model = SettingsModel()
            self._session.add(settings_model)
            await self._session.commit()
        return settings_model

    async def update_api_jwt(self, vcd_api_jwt: str) -> None:
        """Обновляет JWT либо создаёт при отсутствии."""
        settings_model = await self.get_or_create()
        settings_model.vcd_api_jwt = vcd_api_jwt
        await self._session.commit()


class TemplateCatalogRepository:
    """Репозиторий взаимодействия с каталогом шаблонов vApp ВМ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, template_id: id) -> TemplateCatalogModel | None:
        query = select(TemplateCatalogModel).where(
            TemplateCatalogModel.id == template_id
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
