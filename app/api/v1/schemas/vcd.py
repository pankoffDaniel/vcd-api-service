import logging
from enum import Enum

from fastapi import Query, status

from app.core.settings import constants
from app.exceptions import (
    JobTypeException,
    QueryParamsException
)

logger = logging.getLogger(__name__)


class JobTypeEnum(Enum):
    VM_CREATE = 'NEW_VM'
    VM_SET_CPU = 'SET_VM_CPU'
    VM_SET_RAM = 'SET_VM_RAM'
    VM_SET_HDD = 'SET_VM_HDD'
    VM_POWER_ON = 'START_VM'
    VM_POWER_OFF = 'STOP_VM'
    VM_POWER_RESET = 'RESET_VM'
    VM_CREATE_SNAPSHOT = 'CREATE_SNAP'
    VM_GET_POWER_STATUS = 'GET_VM_STATUS'
    VM_GET_CURRENT_USAGE = 'GET_VM_USAGE'
    VM_GET_CONSOLE_URL = 'GET_CONSOLE_URL'


class VCDQueryParamsSchema:
    """Схема параметров запроса."""

    def __init__(
            self,
            job_type: str = Query(
                ...,
                alias='JOB_TYPE',
                description='Работа, которая должна выполниться',
            ),
            vm_id: str = Query(
                None,
                alias='VM_ID',
                description='Идентификатор ВМ из vCloud Director',
            ),
            vm_title: str = Query(
                None,
                alias='VM_TITLE',
                description='Название создаваемой ВМ',
            ),
            os_password: str = Query(
                None,
                alias='OS_PASS',
                description='Пароль, который установится для root-пользователя ОС',
            ),
            template_id: int = Query(
                None,
                alias='TEMPLATE_ID',
                description='Идентификатор шаблона создания ВМ',
            ),
            vdc_title: str = Query(
                None,
                alias='VDC_TITLE',
                description='Название vDC',
            ),
            vapp_title: str = Query(
                None,
                alias='VAPP_TITLE',
                description='Название vApp',
            ),
            cpu: int = Query(
                None,
                alias='CPU',
                description='Значение устанавливаемого CPU'
            ),
            ram: int = Query(
                None,
                alias='RAM',
                description='Значение устанавливаемого RAM'
            ),
            hdd: int = Query(
                None,
                alias='HDD',
                description='Значение устанавливаемого HDD'
            ),
            disk_number: int = Query(
                None,
                alias='DISK_NUMBER',
                description='Номер диска'
            ),
    ) -> None:
        self.job_type = job_type
        self.vm_id = vm_id
        self.vm_title = vm_title
        self.os_password = os_password
        self.template_id = template_id
        self.vdc_title = vdc_title
        self.vapp_title = vapp_title
        self.cpu = cpu
        self.ram = ram
        self.hdd = hdd
        self.disk_number = disk_number
        self._validate_job_type()

    def _validate_vm_create(self) -> None:
        """Валидация параметров для создания ВМ."""
        if not all((self.template_id, self.vm_title, self.os_password)):
            logger.error(constants.INVALID_QUERY_PARAMS_MESSAGE)
            raise QueryParamsException(
                content=constants.INVALID_QUERY_PARAMS_MESSAGE,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

    def _validate_vm_set_cpu(self) -> None:
        """Валидация параметров для установки vCPU ВМ."""
        if not self.cpu:
            logger.error(constants.INVALID_QUERY_PARAMS_MESSAGE)
            raise QueryParamsException(
                content=constants.INVALID_QUERY_PARAMS_MESSAGE,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

    def _validate_vm_set_ram(self) -> None:
        """Валидация параметров для установки vRAM ВМ."""
        if not self.ram:
            logger.error(constants.INVALID_QUERY_PARAMS_MESSAGE)
            raise QueryParamsException(
                content=constants.INVALID_QUERY_PARAMS_MESSAGE,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

    def _validate_vm_set_hdd(self) -> None:
        """Валидация параметров для установки vHDD ВМ."""
        if not self.hdd:
            logger.error(constants.INVALID_QUERY_PARAMS_MESSAGE)
            raise QueryParamsException(
                content=constants.INVALID_QUERY_PARAMS_MESSAGE,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

    def _validate_vm_id(self) -> None:
        """Валидация `vm_id` для остальных `job_type`."""
        if self.vm_id is None:
            logger.error(constants.INVALID_QUERY_PARAMS_MESSAGE)
            raise QueryParamsException(
                content=constants.INVALID_QUERY_PARAMS_MESSAGE,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

    def _validate_job_type_params(self, job_type_enum: JobTypeEnum) -> None:
        """Запускает валидаторы параметров в зависимости от `job_type`."""
        match job_type_enum:
            case JobTypeEnum.VM_CREATE:
                self._validate_vm_create()
            case JobTypeEnum.VM_SET_CPU:
                self._validate_vm_id()
                self._validate_vm_set_cpu()
            case JobTypeEnum.VM_SET_RAM:
                self._validate_vm_id()
                self._validate_vm_set_ram()
            case JobTypeEnum.VM_SET_HDD:
                self._validate_vm_id()
                self._validate_vm_set_hdd()
            case _:
                self._validate_vm_id()

    def _validate_job_type(self) -> None:
        """Валидация на существование `job_type`."""
        try:
            job_type_enum = JobTypeEnum(self.job_type)
            self._validate_job_type_params(job_type_enum)
        except ValueError:
            logger.error(constants.INVALID_JOB_TYPE_MESSAGE, {
                'job_type': self.job_type
            })
            raise JobTypeException(
                content=constants.INVALID_JOB_TYPE_MESSAGE,
                status_code=status.HTTP_400_BAD_REQUEST
            )
