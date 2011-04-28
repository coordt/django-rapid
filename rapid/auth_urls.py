from django.conf.urls.defaults import *

from views import AuthenticationView

urlpatterns = patterns('',
    url(r'^auth$', 
        AuthenticationView.as_view(), 
        name='authentication'),
)