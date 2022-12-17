import os
import datetime
import mimetypes

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from django.db import models
from django.contrib.auth.models import User

class DirectoryNotEmpty(Exception):
    """Exception when trying to delete a non-empty directory"""
    pass

class StorageObject(object):
    """
    An abstract way to get files/objects in a container (file system)
    """
    def __init__(self, container, path):
        """
        Instantiate a storage object.
        """
        self.path = os.path.join(container.path, path.lstrip('.'))
        self.name = ''
        self.full_name = ''
        self.isdir = False
        self.bytes = 0
        self.last_modified = None
        self.container = container
        if self.exists:
            head, tail = os.path.split(self.path)
            stat_info = os.stat(self.path)
            self.isdir = os.path.isdir(self.path)
            self.bytes = 0 if self.isdir else stat_info[7]
            self.last_modified = datetime.datetime.fromtimestamp(stat_info[9])
            if tail:
                self.name = tail
            elif head:
                self.name = head.split('/')[-1]
            self.full_name = self.path.replace(self.container.path, '', 1)
    
    def compute_md5sum(self):
        """
        Given an open file object, returns the md5 hexdigest of the data.
        """
        if self.isdir:
            return ''
        checksum = md5()
        fobj = None
        try:
            fobj = open(self.path)
            while buff := fobj.read(4096):
                checksum.update(buff)
            fobj.seek(0)
        except IOError:
            pass
        finally:
            if fobj:
                fobj.close()
        return checksum.hexdigest()
    
    def delete(self):
        """
        Delete the file. Raise an exception if it is a non-empty dir
        """
        if self.isdir:
            if len(os.listdir(self.path)) != 0:
                raise DirectoryNotEmpty()
            else:
                os.rmdir(self.path)
        else:
            os.remove(self.path)
    
    @property
    def hash(self):
        """Return an md5sum"""
        if not hasattr(self, '_hash'):
            self._hash = self.compute_md5sum()
        return self._hash
    
    @property
    def content_type(self):
        """Determine the content type"""
        if not hasattr(self, '_content_type'):
            if self.isdir:
                return 'application/directory'
            ctype, encoding = mimetypes.guess_type(self.path)
            self._content_type = ctype or 'application/octet-stream'
        return self._content_type
    
    @property
    def exists(self):
        """
        Does the file exist?
        """
        return os.path.exists(self.path)
    
    def write(self, content):
        """
        Set the contents of the file to ``content``
        """
        os.makedirs(os.path.dirname(self.path))
        myfile = open(self.path, 'wb')
        myfile.write(content)
    
    def read(self, num_bytes=None):
        """
        Read form the file and return the results
        """
        output = ''
        try:
            thefile = open(self.path)
            output = thefile.read(num_bytes) if num_bytes is not None else thefile.read()
        finally:
            thefile.close()
        return output
    
    def __repr(self):
        return self.name
    
    def __str__(self):
        return self.name
    
    def __unicode__(self):
        return self.name


class Account(models.Model):
    """
    Generic way to manage an "account"
    """
    user = models.ForeignKey(User)
    auth_key = models.CharField(
        blank=True, 
        max_length=255,
        help_text="The API key used to get an auth token.")
    auth_token = models.CharField(
        blank=True, 
        max_length=255,
        help_text="A temporary token for API calls that expires at Token Expires.")
    token_expires = models.DateTimeField(
        blank=True, 
        default=datetime.datetime.now,
        help_text="When the Auth Token")

class Container(models.Model):
    """
    A container name-directory path mapping
    """
    
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    account = models.ForeignKey(Account)
    is_public = models.BooleanField(default=False)
    is_cdn_enabled = models.BooleanField(default=False)
    cdn_url = models.CharField(blank=True, max_length=255)
    cdn_ttl = models.IntegerField(blank=True, null=True)
    cdn_log_retention = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('account', 'name')
    
    @property
    def total_size(self):
        """
        Get the total space occupied by this container
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.path):
            for name in filenames:
                fileptr = os.path.join(dirpath, name)
                total_size += os.path.getsize(fileptr)
        return total_size
    
    @property
    def file_count(self):
        """
        Recursively count the number of files within a path
        """
        return sum(
            len(filenames) for dirpath, dirnames, filenames in os.walk(self.path)
        )
    
    def storage_objects(self, limit=10000, marker=None, prefix='', path=None, 
                        delimiter=''):
        """
        Return a list of storage objects based on the criteria
        
        limit
            For an integer value *n*, limits the number of results to at most *n* 
            values, or 10000.
        
        marker
            Given a string value *x*, return object names greater in value than 
            the specified marker.
        
        prefix
            For a string value *x*, causes the results to be limited to object 
            names beginning with the substring *x*. 
        
        path
            For a string value *x*, return the object names nested in the pseudo 
            path. Delimiter is set to '/'.
        
        delimiter
            For a character *c*, return all the object names nested in the 
            container (without the need for the directory marker objects).
        
        Starting point:
        
        container path + prefix/path + marker(if marker > prefix)
        """
        if path is not None:
            prefix = path = path.lstrip('.')
            if path:
                prefix = path = path.rstrip('/') + '/'
            delimiter = '/'
        elif delimiter and not prefix:
            prefix = ''
        if marker and marker > prefix:
            marker_path = os.path.join(self.path, marker)
            start_path = f'{os.path.dirname(marker_path)}/'
        else:
            start_path = prefix and os.path.join(self.path, prefix) or self.path
            marker_path = start_path
        results = []

        for dirpath, dirnames, filenames in os.walk(start_path, topdown=False):
            if len(results) >= limit:
                break
            if os.path.commonprefix([self.path, dirpath]) != self.path:
                break
            filesanddirs = filenames + dirnames
            filesanddirs.sort()
            for item in filesanddirs:
                if os.path.join(dirpath, item) <= marker_path:
                    continue
                if item.startswith('.'):
                    continue
                relpath = os.path.join(dirpath.replace(self.path, '', 1), item)
                results.append(StorageObject(self, relpath))
                if len(results) >= limit:
                    break
        return results
    
    def get_storage_object(self, object_path):
        """
        Turn a relative object path into a StorageObject
        """
        return StorageObject(container=self, path=object_path)
    
    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name


from django.db.models.signals import post_delete
from django.dispatch import receiver

@receiver(post_delete, sender=Container)
def remove_container_path(sender, instance, *args, **kwargs):
    """
    After the container is gone, remove the empty directory
    """
    os.rmdir(instance.path)

