from django.conf import settings

STORAGE_URL = '/storage/v1/'
MANAGEMENT_URL = '/management/v1/'
DEFAULT_ACCOUNT = 'default'

CONTAINER_LOCATION = getattr(settings, 'CONTAINER_LOCATION', 'storage')