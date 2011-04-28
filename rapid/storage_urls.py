from django.conf.urls.defaults import *

from views import AccountView, ContainerView, ObjectView

urlpatterns = patterns('',
    url(r'^v1/([-a-zA-Z0-9_]+)$', 
        AccountView.as_view(), 
        name='account_services'),
    url(r'^v1/([-a-zA-Z0-9_]+)/([-a-zA-Z0-9_%]+)$', 
        ContainerView.as_view(), 
        name='container_services'),
    url(r'^v1/([-a-zA-Z0-9_]+)/([-a-zA-Z0-9_%]+)/(.*)$', 
        ObjectView.as_view(), 
        name='object_services'),
)