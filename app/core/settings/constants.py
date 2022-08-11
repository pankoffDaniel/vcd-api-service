import os.path

PRODUCTION_CONFIG_PATH = os.path.join(
    'app', 'core', 'settings', 'config.toml'
)
DEVELOPMENT_CONFIG_PATH = os.path.join(
    'app', 'core', 'settings', 'config.dev.toml'
)
INCOMING_REQUEST_MESSAGE = 'Incoming request with query params'
JOB_TYPE_WAS_SENT = 'DONE'
INVALID_JOB_TYPE_MESSAGE = 'Invalid job type'
INVALID_VM_CONSOLE_PARAMS_MESSAGE = 'Invalid console query params'
INTERNAL_SERVER_ERROR_MESSAGE = 'INTERNAL SERVER ERROR'
VCD_JWT_EXPIRED_MESSAGE = 'vCloud Director API JWT expired'
INVALID_FORMAT_VCD_JWT_MESSAGE = 'Invalid format vCloud Director JWT'
VDC_RESOURCE_NOT_FOUND_MESSAGE = 'vDC Resource not found'
VAPP_RESOURCE_NOT_FOUND_MESSAGE = 'vApp Resource not found'
TEMPLATE_CATALOG_NOT_FOUND_MESSAGE = 'Catalog of templates not found'
INVALID_QUERY_PARAMS_MESSAGE = 'Invalid query params'
VM_DISK_NOT_FOUND_MESSAGE = 'VM disk not found'
ANOTHER_VM_CREATING_MESSAGE = 'Another VM creating'
