============
Introduction
============

Rapid is designed to implement the OpenStack Swift storage API while storing all files on the local filesystem. It is meant to be used for testing or possibly a low-scale storage engine, making moving to Rackspace Cloud as easy as changing a url.

.. note::
	This package is not currently ready for use by unknown users. Authentication and authorization is currently not handled at all.

Accounts, Containers and Objects
================================

OpenStack Swift defines three types of resources: accounts, containers and objects. Accounts are pretty straightforward; they are user accounts. Accounts are currently a simple relation to Django's :class:`User` model.

Containers are buckets of storage. Swift treats containers as a non-hierarchical file system of objects. There are hooks in the API, however, to treat filenames in a pseudo-hierarchical way, if they are named like ``/path/to/my/file.txt``\ . Rapid emulates this, but actually stores files hierarchically in the file system.

Objects are the files stored in containers. These files are stored as normal files in the file system, in a relative path based on the name of the object.

Authentication and Authorization
================================

Authentication is obtained by submitting a username and API key to a specific URL. Using 
`python-cloudfiles <http://github.com/rackspace/python-cloudfiles>`_\ , you need to send an alternate authentication URL:

.. code-block:: python
	
	import cloudfiles
	conn = cloudfiles.get_connection('myusername', 'myapikey', 
	                                 authurl='http://media.example.com/auth')


