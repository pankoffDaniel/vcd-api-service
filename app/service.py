import logging
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Callable, Iterable

import jwt
from fastapi import status
from jwt import DecodeError
from lxml.objectify import ObjectifiedElement
from pyvcloud.vcd.client import (
    BasicLoginCredentials,
    Client, NSMAP, EntityType
)
from pyvcloud.vcd.exceptions import (
    BadRequestException,
    AccessForbiddenException,
    OperationNotSupportedException,
    ConflictException,
    UnauthorizedException,
    InternalServerException,
    EntityNotFoundException
)
from pyvcloud.vcd.org import Org
from pyvcloud.vcd.utils import extract_id
from pyvcloud.vcd.vapp import VApp
from pyvcloud.vcd.vdc import VDC
from pyvcloud.vcd.vm import VM

from app.api.v1.schemas.vcd import (
    VCDQueryParamsSchema,
    JobTypeEnum
)
from app.core.settings import constants
from app.core.settings.config import VCDConfig, AppConfig
from app.exceptions import (
    VMNotFoundException,
    VMPowerStateException,
    VCDAuthError,
    VCDResourceNotFoundException,
    VMCreatingException,
    TemplateCatalogNotFoundException,
    VCDBadRequestException, AnotherVMCreatingException
)
from app.repositories import (
    VMRepository,
    SettingsRepository,
    TemplateCatalogRepository
)
from app.utils import get_vm_console_link

logger = logging.getLogger(__name__)


class VMPowerStatus(IntEnum):
    """Статусы ВМ."""
    SUSPENDED = 3
    POWERED_ON = 4
    POWERED_OFF = 8


class VCDService:
    """Сервис для работы с API vCloud Director."""

    def __init__(
            self,
            *,
            app_config: AppConfig,
            vcd_config: VCDConfig,
            settings_repository: SettingsRepository,
            template_catalog_repository: TemplateCatalogRepository,
            vm_repository: VMRepository,
    ) -> None:
        self._app_config = app_config
        self._vcd_config = vcd_config
        self._vm_repository = vm_repository
        self._template_catalog_repository = template_catalog_repository
        self._settings_repository = settings_repository
        self._client: Client | None = None

    async def setup_client(self) -> None:
        """Создание и настройка клиента для работы с API vCD."""
        logger.debug('Client creating')
        self._client = Client(
            uri=self._vcd_config.hostname,
            api_version=self._vcd_config.api_version,
        )
        await self._auth_client()
        logger.debug('Client created')

    async def _update_api_jwt(self) -> None:
        """Обновляет API JWT от сервиса текущим токеном."""
        logger.debug('Creating new token')
        vcd_api_jwt = self._client.get_access_token()
        await self._settings_repository.update_api_jwt(vcd_api_jwt)
        logger.debug('New token created', {
            'vcd_api_jwt': vcd_api_jwt
        })

    async def _auth_client_via_basic_auth(self) -> None:
        """Аутентификация клиента через BasicAuth."""
        logger.debug('Auth client via BasicAuth')
        try:
            self._client.set_credentials(
                BasicLoginCredentials(
                    org=self._vcd_config.organization,
                    user=self._vcd_config.username,
                    password=self._vcd_config.password
                ))
        except UnauthorizedException as exception:
            logger.error(str(exception), {
                'org': self._vcd_config.organization,
                'user': self._vcd_config.username,
                'password': self._vcd_config.password
            })
            raise VCDAuthError(
                content=str(exception),
                status_code=status.HTTP_401_UNAUTHORIZED
            )

    def _auth_client_via_vcloud_token(self, token: str) -> None:
        """Аутентификация клиента через vCloud Token."""
        logger.debug('Auth client via vCloud Token', {
            'vcd_api_vcloud_token': token
        })
        try:
            self._client.rehydrate_from_token(token)
        except UnauthorizedException as exception:
            logger.error(
                str(exception),
                {'vcd_api_vcloud_token': token}
            )
            raise VCDAuthError(
                content=str(exception),
                status_code=status.HTTP_401_UNAUTHORIZED
            )

    async def _auth_client(self) -> None:
        """Аутентификация клиента."""
        settings_model = await self._settings_repository.get_or_create()
        if settings_model.vcd_api_jwt is None:
            await self._auth_client_via_basic_auth()
            return await self._update_api_jwt()
        try:
            vcd_api_jwt_data = jwt.decode(
                jwt=settings_model.vcd_api_jwt,
                options={'verify_signature': False}
            )
        except DecodeError:
            logger.error(constants.INVALID_FORMAT_VCD_JWT_MESSAGE, {
                'vcd_api_jwt': settings_model.vcd_api_jwt
            })
            await self._auth_client_via_basic_auth()
            return await self._update_api_jwt()
        expires_at = datetime.fromtimestamp(vcd_api_jwt_data['exp'])
        current_datetime_with_extra_time = datetime.now() + timedelta(minutes=5)
        if current_datetime_with_extra_time < expires_at:
            return self._auth_client_via_vcloud_token(vcd_api_jwt_data['jti'])
        logger.warning(constants.VCD_JWT_EXPIRED_MESSAGE, {
            'vcd_api_jwt': settings_model.vcd_api_jwt,
        })
        await self._auth_client_via_basic_auth()
        await self._update_api_jwt()

    def _get_vapp_template_resource(
            self,
            *,
            catalog_template_title: str,
            vapp_template_title: str,
            org: Org
    ) -> ObjectifiedElement:
        """Получает ресурс шаблона vApp."""
        try:
            catalog_item = org.get_catalog_item(
                name=catalog_template_title,
                item_name=vapp_template_title
            )
        except EntityNotFoundException as exception:
            logger.error(str(exception), {
                'catalog_template_title': catalog_template_title,
                'vapp_template_title': vapp_template_title
            })
            raise VCDResourceNotFoundException(
                content=str(exception),
                status_code=status.HTTP_404_NOT_FOUND
            )
        return self._client.get_resource(catalog_item.Entity.get('href'))

    def _get_client_org(self) -> Org:
        """Получает организацию клиента."""
        resource = self._client.get_org()
        return Org(self._client, resource=resource)

    def _get_vdc(self, title: str, *, org: Org) -> VDC:
        """Получает vDC по названию и организации."""
        resource = org.get_vdc(title)
        if resource is None:
            logger.error(constants.VDC_RESOURCE_NOT_FOUND_MESSAGE, {
                'title': title
            })
            raise VCDResourceNotFoundException(
                content=constants.VDC_RESOURCE_NOT_FOUND_MESSAGE,
                status_code=status.HTTP_404_NOT_FOUND
            )
        return VDC(self._client, resource=resource)

    def _get_vapp(self, title: str, *, vdc: VDC) -> VApp:
        """Получает vApp по vDC и названию vApp"""
        try:
            resource = vdc.get_vapp(title)
        # TypeError - если `title` is None
        except (EntityNotFoundException, TypeError):
            logger.error(constants.VAPP_RESOURCE_NOT_FOUND_MESSAGE, {
                'title': title
            })
            raise VCDResourceNotFoundException(
                content=constants.VAPP_RESOURCE_NOT_FOUND_MESSAGE,
                status_code=status.HTTP_404_NOT_FOUND
            )
        return VApp(self._client, resource=resource)

    @staticmethod
    def _vm_create(*, vapp: VApp, specification: list) -> None:
        """Создаёт ВМ в vApp через спецификацию."""
        try:
            vapp.add_vms(specification, power_on=False)
        except EntityNotFoundException as exception:
            logger.error(str(exception), {
                'specification': specification
            })
            raise VCDResourceNotFoundException(
                content=str(exception),
                status_code=status.HTTP_404_NOT_FOUND
            )
        except OperationNotSupportedException as exception:
            logger.error(str(exception), {
                'specification': specification
            })
            raise AnotherVMCreatingException(
                content=constants.ANOTHER_VM_CREATING_MESSAGE,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except BadRequestException as exception:
            logger.error(str(exception), {
                'specification': specification
            })
            raise VMCreatingException(
                content=str(exception),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    async def vm_create(
            self,
            *,
            vdc_title: str | None,
            vapp_title: str | None,
            os_password: str,
            template_id: int,
            vm_title: str,
    ) -> None:
        """Создаёт ВМ."""
        settings_model = await self._settings_repository.get_or_create()
        vdc_title = vdc_title or settings_model.default_vdc
        vapp_title = vapp_title or settings_model.default_vapp
        org = self._get_client_org()
        vdc = self._get_vdc(vdc_title, org=org)
        vapp = self._get_vapp(vapp_title, vdc=vdc)
        template_catalog_model = await self._template_catalog_repository.get(template_id)
        if template_catalog_model is None:
            logger.error(constants.TEMPLATE_CATALOG_NOT_FOUND_MESSAGE, {
                'template_id': template_id
            })
            raise TemplateCatalogNotFoundException(
                content=constants.TEMPLATE_CATALOG_NOT_FOUND_MESSAGE,
                status_code=status.HTTP_404_NOT_FOUND
            )
        catalog_template_title = template_catalog_model.catalog_template.title
        vapp_template_title = template_catalog_model.vapp_template.title
        vm_template_title = template_catalog_model.vm_template.title
        vapp_template_resource = self._get_vapp_template_resource(
            catalog_template_title=catalog_template_title,
            vapp_template_title=vapp_template_title,
            org=org
        )
        specification = {
            'vapp': vapp_template_resource,
            'source_vm_name': vm_template_title,
            'target_vm_name': vm_title,
            'hostname': 'hostname',
            'password': os_password
        }
        self._vm_create(vapp=vapp, specification=[specification])

    def vm_power_off(self, *, vm_id: str) -> None:
        """Выключает ВМ."""
        vm = self._get_vm_by_id(vm_id)
        try:
            vm.power_off()
        except OperationNotSupportedException as exception:
            logger.error(str(exception), {
                'vm_id': vm_id,
                'power_state': vm.get_power_state()
            })
            raise VMPowerStateException(
                content=str(exception),
                status_code=status.HTTP_409_CONFLICT
            )

    def vm_power_on(self, *, vm_id: str) -> None:
        """Включает ВМ."""
        vm = self._get_vm_by_id(vm_id)
        try:
            vm.power_on()
        except OperationNotSupportedException as exception:
            logger.error(str(exception), {
                'vm_id': vm_id,
                'power_state': vm.get_power_state()
            })
            raise VMPowerStateException(
                content=str(exception),
                status_code=status.HTTP_409_CONFLICT
            )

    def vm_power_reset(self, *, vm_id: str) -> None:
        """Сброс ВМ по питанию."""
        vm = self._get_vm_by_id(vm_id)
        try:
            vm.power_reset()
        except OperationNotSupportedException as exception:
            logger.error(str(exception), {
                'vm_id': vm_id,
                'power_state': vm.get_power_state()
            })
            raise VMPowerStateException(
                content=str(exception),
                status_code=status.HTTP_409_CONFLICT
            )

    def vm_get_power_status(self, *, vm_id: str) -> str:
        """Получение статуса ВМ."""
        vm = self._get_vm_by_id(vm_id)
        vm_power_state = vm.get_power_state()
        return VMPowerStatus(vm_power_state).name

    def vm_get_console_url(self, *, vm_id: str) -> str:
        """Получение ссылки на консоль ВМ."""
        vm = self._get_vm_by_id(vm_id)
        try:
            screen_data = vm.list_mks_ticket()
        except ConflictException as exception:
            logger.error(str(exception), {
                'vm_id': vm_id,
                'power_state': vm.get_power_state()
            })
            raise VMPowerStateException(
                content=str(exception),
                status_code=status.HTTP_409_CONFLICT
            )
        else:
            host = str(screen_data['Host'])
            port = str(screen_data['Port'])
            ticket = str(screen_data['Ticket'])
            return get_vm_console_link(
                hostname=self._app_config.hostname,
                host=host,
                port=port,
                ticket=ticket
            )

    def vm_create_snapshot(self, *, vm_id: str) -> None:
        """Создаёт снэпшот ВМ."""
        vm = self._get_vm_by_id(vm_id)
        vm.snapshot_create(memory=True)

    def vm_get_current_usage(self, *, vm_id: str) -> list[dict[str, str]]:
        """Получает текущее использование ресурсов ВМ."""
        vm = self._get_vm_by_id(vm_id)
        try:
            return vm.list_all_current_metrics()
        except OperationNotSupportedException as exception:
            logger.error(str(exception), {
                'vm_id': vm_id,
                'power_state': vm.get_power_state()
            })
            raise VMPowerStateException(
                content=str(exception),
                status_code=status.HTTP_409_CONFLICT
            )

    def vm_set_hdd(
            self,
            *,
            vm_id: str,
            hdd: int,
            disk_number: int | None
    ) -> None:
        """Устанавливает значение vHDD ВМ в МБ."""
        virtual_quantity_key = '{' + NSMAP['rasd'] + '}VirtualQuantity'
        description_key = '{' + NSMAP['rasd'] + '}Description'
        element_name_key = '{' + NSMAP['rasd'] + '}ElementName'
        host_resource_key = '{' + NSMAP['rasd'] + '}HostResource'
        capacity_key = '{' + NSMAP['vcloud'] + '}capacity'
        vm = self._get_vm_by_id(vm_id)
        uri = vm.href + '/virtualHardwareSection/disks'
        disk_list = self._client.get_resource(uri)
        if disk_number is None:
            disk_number = 1
        for disk in disk_list.Item:
            condition1 = disk[description_key] == 'Hard disk'
            condition2 = disk[element_name_key] == f'Hard disk {disk_number}'
            if condition1 and condition2:
                disk[virtual_quantity_key] = hdd
                disk[host_resource_key].set(capacity_key, str(hdd))
                try:
                    self._client.put_resource(
                        uri, disk_list, EntityType.RASD_ITEMS_LIST.value
                    )
                    break
                except BadRequestException as exception:
                    logger.error(str(exception), {
                        'vm_id': vm_id,
                        'hdd': hdd,
                        'power_state': vm.get_power_state()
                    })
                    raise VCDBadRequestException(
                        content=str(exception),
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
        else:
            logger.error(constants.VM_DISK_NOT_FOUND_MESSAGE, {
                'vm_id': vm_id,
                'hdd': hdd,
                'power_state': vm.get_power_state()
            })
            raise VCDBadRequestException(
                content=constants.VM_DISK_NOT_FOUND_MESSAGE,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def vm_set_cpu(self, *, vm_id: str, cpu: int) -> None:
        """Устанавливает значение vCPU ВМ в количестве."""
        vm = self._get_vm_by_id(vm_id)
        try:
            vm.modify_cpu(cpu)
        except BadRequestException as exception:
            logger.error(str(exception), {
                'vm_id': vm_id,
                'cpu': cpu,
                'power_state': vm.get_power_state()
            })
            raise VCDBadRequestException(
                content=str(exception),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def vm_set_ram(self, *, vm_id: str, ram: int) -> None:
        """Устанавливает значение vRAM ВМ в МБ."""
        vm = self._get_vm_by_id(vm_id)
        try:
            vm.modify_memory(ram)
        except BadRequestException as exception:
            logger.error(str(exception), {
                'vm_id': vm_id,
                'ram': ram,
                'power_state': vm.get_power_state()
            })
            raise VCDBadRequestException(
                content=str(exception),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def _get_vm_href(self, *, vm_id: str) -> str:
        """Получает ссылку ВМ по ID."""
        return f'{self._client.get_api_uri()}/vApp/vm-{vm_id}'

    def _get_vm_by_id(self, vm_id: str) -> VM:
        """Получение ВМ по ID."""
        try:
            vm = VM(self._client, href=self._get_vm_href(vm_id=vm_id))
            vm.reload()
        except AccessForbiddenException as exception:
            logger.error(str(exception), {'vm_id': vm_id})
            raise VMNotFoundException(
                content=str(exception),
                status_code=status.HTTP_403_FORBIDDEN
            )
        except BadRequestException as exception:
            logger.error(str(exception), {'vm_id': vm_id})
            raise VMNotFoundException(
                content=str(exception),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except InternalServerException as exception:
            logger.error(str(exception), {'vm_id': vm_id})
            raise VMNotFoundException(
                content=str(exception),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return vm

    def _iterate_vdcs(self, org: Org) -> Iterable[VDC]:
        """Итерация по VDC."""
        for vdc_item in org.list_vdcs():
            yield VDC(self._client, href=vdc_item['href'])

    def _iterate_vapps(self, vdc: VDC) -> Iterable[VApp]:
        """Итерация по vApp."""
        for resource in vdc.list_resources():
            if resource['type'] == 'application/vnd.vmware.vcloud.vApp+xml':
                vapp_href = vdc.get_vapp_href(resource['name'])
                yield VApp(self._client, href=vapp_href)

    def _iterate_vms_resources(self) -> Iterable[ObjectifiedElement]:
        """Итерация по ресурсам ВМ."""
        org = self._get_client_org()
        for vdc in self._iterate_vdcs(org):
            for vapp in self._iterate_vapps(vdc):
                for vm_resource in vapp.get_all_vms():
                    yield vm_resource

    async def create_all_vm_statistics(self) -> None:
        """Создаёт статистику потребления ресурсов
        каждой ВМ, каждого vApp, каждого vDC."""
        bulk_vm_statistics = {}
        for vm_resource in self._iterate_vms_resources():
            vm_id = extract_id(vm_resource.attrib['id'])
            vm_name = extract_id(vm_resource.attrib['name'])
            try:
                vm_statistics = self.vm_get_current_usage(
                    vm_id=vm_id
                )
            except VMPowerStateException:
                continue
            vm_model = await self._vm_repository.get_or_create(
                vm_id=vm_id,
                title=vm_name
            )
            bulk_vm_statistics[vm_model.id] = vm_statistics
        if bulk_vm_statistics:
            await self._vm_repository.bulk_create_statistics(bulk_vm_statistics)


class VCDController:
    """Контроллер управления сервисом `VCDService`.
    Обрабатывает входные данные и вызывает методы
    сервиса, передавая необходимые данные."""

    def __init__(
            self,
            *,
            vcd_service: VCDService,
    ) -> None:
        self._vcd_service = vcd_service
        self.job_types = {
            JobTypeEnum.VM_CREATE.value: self.vm_create,
            JobTypeEnum.VM_POWER_ON.value: self.vm_power_on,
            JobTypeEnum.VM_POWER_OFF.value: self.vm_power_off,
            JobTypeEnum.VM_POWER_RESET.value: self.vm_power_reset,
            JobTypeEnum.VM_CREATE_SNAPSHOT.value: self.vm_create_snapshot,
            JobTypeEnum.VM_GET_POWER_STATUS.value: self.vm_get_power_status,
            JobTypeEnum.VM_GET_CURRENT_USAGE.value: self.vm_get_current_usage,
            JobTypeEnum.VM_GET_CONSOLE_URL.value: self.vm_get_console_url,
            JobTypeEnum.VM_SET_CPU.value: self.vm_set_cpu,
            JobTypeEnum.VM_SET_RAM.value: self.vm_set_ram,
            JobTypeEnum.VM_SET_HDD.value: self.vm_set_hdd,
        }

    async def call_job_type_handler(
            self, params: VCDQueryParamsSchema
    ) -> str | None:
        """Вызывает обработчик `JOB_TYPE`."""
        job_type_handler: Callable = self.job_types[params.job_type]
        await self._vcd_service.setup_client()
        return await job_type_handler(params)

    async def vm_create(self, params: VCDQueryParamsSchema) -> None:
        """Создаёт ВМ."""
        logger.debug('VM creating')
        await self._vcd_service.vm_create(
            template_id=params.template_id,
            vm_title=params.vm_title,
            os_password=params.os_password,
            vdc_title=params.vdc_title,
            vapp_title=params.vapp_title
        )

    async def vm_set_cpu(self, params: VCDQueryParamsSchema) -> None:
        """Устанавливает значение vCPU ВМ."""
        self._vcd_service.vm_set_cpu(
            vm_id=params.vm_id,
            cpu=params.cpu
        )

    async def vm_set_ram(self, params: VCDQueryParamsSchema) -> None:
        """Устанавливает значение vRAM ВМ."""
        self._vcd_service.vm_set_ram(
            vm_id=params.vm_id,
            ram=params.ram
        )

    async def vm_set_hdd(self, params: VCDQueryParamsSchema) -> None:
        """Устанавливает значение vHDD ВМ."""
        self._vcd_service.vm_set_hdd(
            vm_id=params.vm_id,
            hdd=params.hdd,
            disk_number=params.disk_number
        )

    async def vm_power_off(self, params: VCDQueryParamsSchema) -> None:
        """Выключает ВМ."""
        logger.debug('VM powering off')
        self._vcd_service.vm_power_off(vm_id=params.vm_id)

    async def vm_power_on(self, params: VCDQueryParamsSchema) -> None:
        """Включает ВМ."""
        logger.debug('VM powering on')
        self._vcd_service.vm_power_on(vm_id=params.vm_id)

    async def vm_power_reset(self, params: VCDQueryParamsSchema) -> None:
        """Сброс ВМ по питанию."""
        logger.debug('VM resetting power')
        self._vcd_service.vm_power_reset(vm_id=params.vm_id)

    async def vm_create_snapshot(self, params: VCDQueryParamsSchema) -> None:
        """Создаёт снэпшот ВМ."""
        logger.debug('VM creating snapshot')
        self._vcd_service.vm_create_snapshot(vm_id=params.vm_id)

    async def vm_get_power_status(self, params: VCDQueryParamsSchema) -> str:
        """Получение статуса ВМ."""
        logger.debug('VM getting power status')
        return self._vcd_service.vm_get_power_status(vm_id=params.vm_id)

    async def vm_get_console_url(self, params: VCDQueryParamsSchema) -> str:
        """Получение ссылки на консоль ВМ."""
        logger.debug('VM getting console url')
        return self._vcd_service.vm_get_console_url(vm_id=params.vm_id)

    async def vm_get_current_usage(self, params: VCDQueryParamsSchema) -> list[dict]:
        """Получает текущее использование VCDQueryParamsSchema ВМ."""
        logger.debug('VM getting current usage')
        return self._vcd_service.vm_get_current_usage(vm_id=params.vm_id)
