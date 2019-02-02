import os
import pkg_resources

CACHE_DIR = "cache"
DATA_DIR = "data"

SOUND_DIR = "sound_files"

def get_userdata_dir():
    return os.environ.get('XDG_DATA_HOME', os.path.join(
        os.path.expanduser('~'), ".local", "share",
        configuration.NAME))

def get_cache_dir():
    return os.path.join(get_userdata_dir(), CACHE_DIR)

def open_cache_file(filename, mode):
    try:
        os.makedirs(get_cache_dir())
    except os.error:
        pass

    return open(os.path.join(get_cache_dir(), filename), mode)

def cache_filename(filename):
    return os.path.join(get_cache_dir(), filename)

def resource_string(resource):
    datapath = "{data_dir}/{resource}".format(
        data_dir=DATA_DIR, resource=resource)
    return pkg_resources.resource_string(__name__, datapath)

def resource_filename(resource):
    datapath = "{dir}/{resource}".format(
        data_dir=DATA_DIR, resource=resource)
    return pkg_resources.resource_filename(__name__, datapath)
