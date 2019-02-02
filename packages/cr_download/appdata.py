"""appdata.py: module to handle local application data (mostly just a
wrapper for the pkg_resources API)

also handle local caching

"""

import os
import pkg_resources

from .name import APP_NAME

CACHE_DIR = "cache"
DATA_DIR = "data"

SOUND_DIR = "sound_files"

def get_userdata_dir():
    """get directory to store application data generated at runtime (for
    now, only cached files)

    """
    return os.environ.get('XDG_DATA_HOME', os.path.join(
        os.path.expanduser('~'), ".local", "share",
        APP_NAME))

def get_cache_dir():
    """get directory to store data cached by application
    """
    return os.path.join(get_userdata_dir(), CACHE_DIR)

def open_cache_file(filename, mode):
    """try and open a file from the cache.

    If this fails, create the cache directory and try and open the
    file there. This will still throw an exception if a nonexistant
    file is opened in read mode.

    """
    try:
        os.makedirs(get_cache_dir())
    except os.error:
        pass

    return open(os.path.join(get_cache_dir(), filename), mode)

def cache_filename(filename):
    """ get the full path of a cached file
    """
    return os.path.join(get_cache_dir(), filename)

def resource_string(resource):
    """ get data packaged with the application as a string
    """
    datapath = "{data_dir}/{resource}".format(
        data_dir=DATA_DIR, resource=resource)
    return pkg_resources.resource_string(__name__, datapath)

def resource_filename(resource):
    """get a (possibly temporary) filename for data packaged with the
    application

    """
    datapath = "{data_dir}/{resource}".format(
        data_dir=DATA_DIR, resource=resource)
    return pkg_resources.resource_filename(__name__, datapath)
