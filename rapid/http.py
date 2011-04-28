from django.http import HttpResponse

class HttpResponseCreated(HttpResponse):
    status_code = 201

class HttpResponseAccepted(HttpResponse):
    status_code = 202

class HttpResponseNoContent(HttpResponse):
    status_code = 204

class HttpResponseUnauthorized(HttpResponse):
    status_code = 401

class HttpResponseConflict(HttpResponse):
    status_code = 409
