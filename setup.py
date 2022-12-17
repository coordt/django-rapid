import os
from setuptools import setup, find_packages

def read_file(filename):
    """Read a file into a string"""
    path = os.path.abspath(os.path.dirname(__file__))
    filepath = os.path.join(path, filename)
    try:
        return open(filepath).read()
    except IOError:
        return ''
    
def get_readme():
    """Return the README file contents. Supports text,rst, and markdown"""
    return next(
        (
            read_file(name)
            for name in ('README', 'README.rst', 'README.md')
            if os.path.exists(name)
        ),
        '',
    )

# Use the docstring of the __init__ file to be the description
DESC = " ".join(__import__('rapid').__doc__.splitlines()).strip()

setup(
    name = "rapid",
    version = __import__('rapid').get_version().replace(' ', '-'),
    url = 'http://github.com/washingtontimes/rapid',
    author = 'coordt',
    author_email = 'coreyoordt@gmail.com',
    description = DESC,
    long_description = get_readme(),
    packages = find_packages(),
    include_package_data = True,
    install_requires = read_file('requirements.txt'),
    classifiers = [
        'License :: OSI Approved :: Apache Software License',
        'Framework :: Django',
    ],
)
