from django.conf import settings

CONTAINER_LOCATION = getattr(settings, 'CONTAINER_LOCATION', 'storage')