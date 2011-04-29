"""
Class-based views for handling the API calls
"""
# pylint: disable-msg=R0201,W0613,F0401,W0622
import urllib, os, uuid, datetime

from django.core import exceptions
from django.core.urlresolvers import reverse
from django.views.generic.base import View
from django.http import (HttpResponse, Http404, HttpResponseBadRequest, 
                         HttpResponseServerError)
from django.shortcuts import get_object_or_404
from django.contrib.sites.models import Site

try:
    import json
except ImportError:
    import simplejson as json

from models import Account, Container, DirectoryNotEmpty
import settings
from http import (HttpResponseCreated, HttpResponseAccepted, 
                    HttpResponseNoContent, HttpResponseConflict,
                    HttpResponseUnauthorized)

class AuthenticationView(View):
    """
    Authentication
    """
    http_method_names = ['get', ]
    
    def get(self, request):
        """Handle an authentication request"""
        
        if 'HTTP_X_AUTH_USER' in request.META and 'HTTP_X_AUTH_KEY' in request.META:
            username = request.META['HTTP_X_AUTH_USER']
            authkey = request.META['HTTP_X_AUTH_KEY']
        else:
            return HttpResponseBadRequest()
        
        try:
            account = Account.objects.get(user__username=username, 
                                          auth_key=authkey)
            account.auth_token = str(uuid.uuid4())
            account.token_expires = datetime.datetime.now() + datetime.timedelta(hours=1)
            account.save()
            response = HttpResponseNoContent()
            url = "%s%s%s" % ("http://",
                Site.objects.get_current().domain, 
                reverse('account_services', args=[account.user.username,])
            )
            response['X-Storage-Url'] = url
            response['X-CDN-Management-Url'] = ''
            response['X-Auth-Token'] = account.auth_token
            return response
        except Account.DoesNotExist:
            return HttpResponseUnauthorized()

class AccountView(View):
    """
    Basic handlers against account resources:
    
    /v1/<account>
    """
    http_method_names = ['get', 'head',]
    
    def __init__(self, *args, **kwargs):
        super(AccountView, self).__init__(*args, **kwargs)
        self.serializers = {
            'json': {
                'function': self.json_serializer, 
                'content_type': 'application/json'},
            'xml': {
                'function': self.xml_serializer, 
                'content_type': 'application/xml'},
            'default': {
                'function': self.default_serializer, 
                'content_type': 'text/plain'},
        }
    
    def xml_serializer(self, account, records):
        """Serialize a set of container records in xml"""
        wrapper = "\n".join([
            '<?xml version="1.0" encoding="UTF-8"?>',
            '', '<account name="%s">%s</account>'])
        container_record = '<container><name>%(name)s</name><count>%(count)s</count><bytes>%(bytes)s</bytes></container>'
        containers = [container_record % r for r in records]
        return wrapper % (account, "".join(containers))
    
    def json_serializer(self, account, records):
        """Serialize a set of container records in json"""
        return json.dumps(records)
    
    def default_serializer(self, account, records):
        """A default serializer for unknown formats"""
        return "\n".join([r['name'] for r in records])
    
    def get(self, request, account_name, *args, **kwargs):
        """List the containers in the account"""
        account = get_object_or_404(Account, user__username=account_name)
        format = request.GET.get('format', None)
        marker = request.GET.get('marker', None)
        limit = int(request.GET.get('limit', 10000))
        return self.list_containers(account, False, limit, marker, format)
    
    def head(self, request, account_name, *args, **kwargs):
        """Return Account Metadata"""
        account = get_object_or_404(Account, user__username=account_name)
        return self.list_containers(account, True)
    
    def list_containers(self, account, metadata_only=False, limit=10000, 
                        marker=None, format=None):
        """
        ``GET`` operations against the ``X-Storage-Url`` for an account are 
        performed to retrieve a list of existing storage containers ordered by 
        name.
        
        Possible query parameters:
        
        limit
            For an integer value *n*, limits the number of results to at most 
            *n* values.
        
        marker
            Given a string value *x*, return object names greater in value 
            than the specified marker.
        
        format
            Specify either json or xml to return the respective serialized 
            response.
        """
        containers = account.container_set.all()
        
        if metadata_only:
            response = HttpResponseNoContent()
            response['X-Account-Container-Count'] = len(containers)
            total_size = 0
            for container in containers:
                total_size += container.total_size
            response['X-Account-Total-Bytes-Used'] = total_size
            return response
        
        if marker is not None:
            containers = containers.filter(name__gt='marker')
        
        if len(containers) == 0:
            return HttpResponseNoContent()
        
        # If no format is specified, we only need the names. So return them 
        # without doing the extra work of calculating additional info
        if format is None:
            return HttpResponse(
                "\n".join([c.name for c in containers]), 
                content_type="text/plain")
        else:
            records = []
            for item in containers:
                cont_rec = {
                    'name': item.name,
                    'count': item.file_count,
                    'bytes': item.total_size,
                }
                records.append(cont_rec)
            serializer = self.serializers.get(format, self.serializers['default'])
            
            return HttpResponse(
                serializer['function'](account, records),
                content_type=serializer['content_type'])


class ContainerView(View):
    """
    Basic handlers for container requests:
    
    /v1/<account>/<container>
    """
    http_method_names = ['get', 'put', 'delete', 'head',]
    
    def __init__(self, *args, **kwargs):
        super(ContainerView, self).__init__(*args, **kwargs)
        
        self.serializers = {
            'json': {
                'function': self.json_serializer, 
                'content_type': 'application/json'},
            'xml': {
                'function': self.xml_serializer, 
                'content_type': 'application/xml'},
            'default': {
                'function': self.default_serializer, 
                'content_type': 'text/plain'},
        }
    
    def xml_serializer(self, container, records):
        """Serialize a set of container records in xml"""
        wrapper = "".join([
            '<?xml version="1.0" encoding="UTF-8"?>\n\n',
            '<container name="%s">%s</container>'])
        container_record = ''.join([
            '<object>',
            '<name>%(name)s</name>',
            '<bytes>%(bytes)s</bytes>',
            '<hash>%(hash)s</hash>',
            '<content_type>%(content_type)s</content_type>',
            '<last_modified>%(last_modified)s</last_modified>',
            '</object>'])
        objs = [container_record % r for r in records]
        return wrapper % (container.name, "\n".join(objs))

    def json_serializer(self, container, records):
        """Serialize a set of container records in json"""
        return json.dumps(records)
    
    def default_serializer(self, container, records):
        """A default serializer for unknown formats"""
        return "\n".join([r['name'] for r in records])
    
    def get(self, request, account_name, container_name, *args, **kwargs):
        """List the objects in the container"""
        account = get_object_or_404(Account, user__username=account_name)
        try:
            container = account.container_set.get(name=container_name)
        except exceptions.DoesNotExist:
            return HttpResponseNoContent()
        format = request.GET.get('format', None)
        marker = request.GET.get('marker', None)
        limit = int(request.GET.get('limit', 10000))
        prefix = request.GET.get('prefix', None)
        path = request.GET.get('path', None)
        delimiter = request.GET.get('delimiter', None)
        
        return self.list_container_objects(container, account, limit, marker, 
                                            format, prefix, path, delimiter)
    
    def head(self, request, account_name, container_name, *args, **kwargs):
        """
        HEAD operations against a storage container are used to determine the 
        number of objects, and the total bytes of all objects stored in the 
        container. Since the storage system is designed to store large amounts 
        of data, care should be taken when representing the total bytes 
        response as an integer; when possible, convert it to a 64-bit unsigned 
        integer if your platform supports that primitive type.
        """
        account = get_object_or_404(Account, user__username=account_name)
        try:
            container = account.container_set.get(name=container_name)
        except exceptions.DoesNotExist:
            raise Http404()
        response = HttpResponseNoContent()
        response['X-Container-Object-Count'] = container.file_count
        response['X-Container-Bytes-Used'] = container.total_size
        return response
    
    def put(self, request, account_name, container_name, *args, **kwargs):
        """
        Create the container.
        
        Containers are storage compartments for your data. The URL encoded 
        name must be less than 256 bytes and cannot contain a forward slash 
        ('/') character.
        """
        account = get_object_or_404(Account, user__username=account_name)
        try:
            container = account.container_set.get(name=container_name) # pylint: disable-msg=W0612
            return HttpResponseAccepted()
        except Container.DoesNotExist:
            pass
        
        if '/' in container_name:
            msg = 'Forward slash ("/") characters are not allowed in container names'
            return HttpResponseConflict(msg)
        
        if len(urllib.quote(container_name)) > 255:
            return HttpResponse('Container name length of %d longer than %d' % (
                len(urllib.quote(container_name)), 255))
        
        try:
            path = os.path.join(settings.CONTAINER_LOCATION, account_name, container_name)
            os.makedirs(path)
            Container.objects.create(
                name=container_name, 
                path=path, 
                account=account)
            return HttpResponseCreated()
        except OSError, err:
            return HttpResponseServerError(err.message)
    
    def delete(self, request, account_name, container_name, *args, **kwargs):
        """
        DELETE operations against a storage container are used to permanently 
        remove that container. The container must be empty before it can be 
        deleted.
        
        No content is returned. A status code of 204 (No Content) indicates 
        success, 404 (Not Found) is returned if the requested container was 
        not found, and a 409 (Conflict) if the container is not empty. No 
        response body will be generated.
        """
        account = get_object_or_404(Account, user__username=account_name)
        try:
            container = account.container_set.get(name=container_name)
        except Container.DoesNotExist:
            raise Http404()
        
        if container.file_count:
            return HttpResponseConflict('Container not empty')
        
        container.delete()
        return HttpResponseNoContent()
    
    def list_container_objects(self, container, account, limit=10000, 
            marker=None, format=None, prefix='', path=None, delimiter=None):
        """
        ``GET`` operations against a storage container name are performed to 
        retrieve a list of objects stored in the container. Additionally, there 
        are a number of optional query parameters that can be used to refine the 
        list results.
        
        A request with no query parameters will return the full list of object 
        names stored in the container, up to 10,000 names. Optionally specifying 
        the query parameters will filter the full list and return a subset of 
        objects.
        
        Query Parameters
        
        limit
            For an integer value *n*, limits the number of results to at most 
            *n* values.
        
        marker
            Given a string value *x*, return object names greater in value 
            than the specified marker.
        
        prefix
            For a string value *x*, causes the results to be limited to object 
            names beginning with the substring *x*.
        
        format
            Specify either json or xml to return the respective serialized 
            response.
        
        path
            For a string value *x*, return the object names nested in the 
            pseudo path.
        
        delimiter
            For a character *c*, return all the object names nested in the 
            container (without the need for the directory marker objects).
        """
        objs = container.storage_objects(limit, marker, prefix, path, delimiter)
        
        if format is None:
            return HttpResponse(
                "\n".join([path and o.name or o.full_name for o in objs]), 
                content_type="text/plain")
        else:
            records = []
            for item in objs:
                cont_rec = {
                    'name': path and item.name or item.full_name,
                    'hash': item.hash,
                    'bytes': item.bytes,
                    'content_type': item.content_type,
                    'last_modified': item.last_modified.isoformat(),
                }
                records.append(cont_rec)
            serializer = self.serializers.get(format, 
                                              self.serializers['default'])
            
            return HttpResponse(
                serializer['function'](container, records),
                content_type=serializer['content_type'])


class ObjectView(View):
    """
    Basic handlers for object requests:
    
    /v1/<account>/<container>/<object>
    """
    http_method_names = ['get', 'post', 'put', 'delete', 'head',]
    
    def get(self, request, account_name, container_name, object_name, 
            *args, **kwargs):
        """Retrieve an object in the container"""
        from django.views.static import serve
        
        account = get_object_or_404(Account, user__username=account_name)
        try:
            container = account.container_set.get(name=container_name)
        except exceptions.DoesNotExist:
            raise Http404()
        
        return serve(request, object_name, document_root=container.path)
    
    def put(self, request, account_name, container_name, object_name, 
            *args, **kwargs):
        """Create/Update object"""
        account = get_object_or_404(Account, user__username=account_name)
        try:
            container = account.container_set.get(name=container_name)
        except exceptions.DoesNotExist:
            raise Http404()
        
        sobj = container.get_storage_object(object_name)
        
        if 'HTTP_X_COPY_FROM' in request.META:
            scontainer_name, s_object_name = request.META['HTTP_COPY_FROM'].lstrip('/').split('/', 1)
            try:
                scontainer = account.container_set.get(name=scontainer_name)
            except exceptions.DoesNotExist:
                raise Http404()
            source_sobj = scontainer.get_storage_object(s_object_name)
            
            sobj.write(source_sobj.read())
        else:
            sobj.write(request.raw_post_data)
        return HttpResponseNoContent()
    
    def delete(self, request, account_name, container_name, object_name, 
            *args, **kwargs):
        """
        DELETE operations against a storage container are used to permanently 
        remove that container. The container must be empty before it can be 
        deleted.
        
        No content is returned. A status code of 204 (No Content) indicates 
        success, 404 (Not Found) is returned if the requested container was 
        not found, and a 409 (Conflict) if the container is not empty. No 
        response body will be generated.
        """
        account = get_object_or_404(Account, user__username=account_name)
        try:
            container = account.container_set.get(name=container_name)
        except Container.DoesNotExist:
            raise Http404()
        
        s_obj = container.get_storage_object(object_name)
        
        if not s_obj.exists:
            raise Http404()
        try:
            s_obj.delete()
        except DirectoryNotEmpty:
            return HttpResponseConflict('Directory Not Empty')
        
        return HttpResponseNoContent()
    
    def head(self, request, account_name, container_name, object_name, 
            *args, **kwargs):
        """
        HEAD operations on an object are used to retrieve object metadata and 
        other standard HTTP headers.
        """
        account = get_object_or_404(Account, user__username=account_name)
        try:
            container = account.container_set.get(name=container_name)
        except exceptions.DoesNotExist:
            raise Http404()
        
        s_obj = container.get_storage_object(object_name)
        
        if not s_obj.exists:
            raise Http404()
        
        response = HttpResponseNoContent()
        response['ETag'] = s_obj.hash
        # TODO: Django overrides this value anyway
        #response['Content-Length'] = s_obj.bytes
        response['Content-Type'] = s_obj.content_type
        
        timefmt = '%a, %d %b %Y %H:%M:%S %Z'
        response['Last-Modified'] = s_obj.last_modified.strftime(timefmt)
        return response
    
    def post(self, request, account_name, *args, **kwargs):
        """
        POST operations against an object name are used to set and overwrite 
        arbitrary key/value metadata. You cannot use the POST operation to 
        change any of the object's other headers such as Content-Type, ETag, 
        etc. It is not used to upload storage objects (see PUT).
        
        Currently ignored.
        """
        return HttpResponseAccepted()
    