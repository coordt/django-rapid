==========
Containers
==========

Containers are implemented as directories in the file system. There is a default storage directory to handle creating a new container via the API, however you may have containers anywhere the web server has access.

create a new storage object:

so = StorageObject(container, 'relative/path/filename.txt')
so.write(file_like_object)

get a new storage object:

so = StorageObject(container, 'relative/path/filename.txt')
if so.exists:
    so.read()