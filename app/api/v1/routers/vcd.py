import json
import logging

from fastapi import APIRouter, Depends, Response

from app.api.v1.schemas.vcd import VCDQueryParamsSchema
from app.core.settings import constants
from app.core.settings.constants import INCOMING_REQUEST_MESSAGE
from app.providers.stubs import (
    VCDControllerStub
)
from app.service import VCDController

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/')
async def vcd(
        params: VCDQueryParamsSchema = Depends(),
        vcd_controller: VCDController = Depends(VCDControllerStub)
) -> Response:
    logger.info(INCOMING_REQUEST_MESSAGE, {
        k: v for k, v in params.__dict__.items() if v is not None
    })
    response = await vcd_controller.call_job_type_handler(params)
    if response is None:
        return Response(constants.JOB_TYPE_WAS_SENT)
    if isinstance(response, str):
        return Response(response)
    return Response(json.dumps(response))
