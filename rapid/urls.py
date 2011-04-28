from auth_urls import urlpatterns as auth_urlpatterns
from storage_urls import urlpatterns as storage_urlpatterns

urlpatterns = auth_urlpatterns + storage_urlpatterns