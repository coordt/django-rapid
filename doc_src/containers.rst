==========
Containers
==========

Containers are implemented as directories in the file system. There is a default storage directory to handle creating a new container via the API, however you may have containers anywhere the web server has access.

Creating a container from the admin
===================================

1. Go to the Django Admin and click "+ Add" button to the right of the Containers app.

2. Enter a name for the account

3. Enter a full path that is local to the server. Rapid will store all files uploaded relative to this directory. Existing files, if any, are served as if they had been uploaded via the API.

4. Select the account that has access to this container.

5. Save.

Creating a container from the API
=================================

#. Make sure an account has been set up. For this example, we'll use the account ``joecool`` and create a container named ``movies``\ .

#. Make sure that your :ref:`container_location` setting is set. The example application sets it to a directory named ``storage`` within the project directory:
   
   .. code-block:: python
   
   	CONTAINER_LOCATION = os.path.join(PROJ_ROOT, 'storage')
   	if not os.path.exists(CONTAINER_LOCATION):
   	    os.makedirs(CONTAINER_LOCATION)
   
   Without this setting, Rapid has no idea where to store the files.

#. To create the container, from the command line type:
   
   .. code-block:: bash
   
   	curl -X PUT -D - http://localhost:8000/v1/joecool/movies
   
   And you should see output like::
   
   	HTTP/1.0 201 CREATED
   	Date: Fri, 29 Apr 2011 00:35:12 GMT
   	Server: WSGIServer/0.1 Python/2.7
   	Content-Type: text/html; charset=utf-8
   
   The directory created is at ``storage/joecool/movies/``
