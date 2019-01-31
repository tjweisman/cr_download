"""cr_settings.py: bootstrapper module that loads configuration data.

"""

import os
import os.path as path
import yaml

import pkg_resources
from  pkg_resources import Requirement

NAME = "cr_download"
DIST_REQUIREMENT = Requirement.parse(NAME.replace("_", "-"))

_XDG_CONFIG_HOME = (os.environ.get('XDG_CONFIG_HOME')
                    or path.join(path.expanduser("~"), ".config"))

CONFIG_DIR = path.join(_XDG_CONFIG_HOME, NAME)
CONFIG_FILE = "config.yaml"

CONFIG_PATH = path.join(CONFIG_DIR, CONFIG_FILE)

def _get_default_config():
    return pkg_resources.resource_string(DIST_REQUIREMENT,
                                         "share/" + CONFIG_FILE)

def _save_default_config(config_info):
    try:
        os.makedirs(CONFIG_DIR)
    except os.error:
        pass

    with open(CONFIG_PATH, "w") as config_file:
        config_file.write(config_info)

def _load_config():
    try:
        with open(CONFIG_PATH, "r") as config_file:
            config_data = yaml.load(config_file)
    except(IOError, FileNotFoundError):
        config_info = _get_default_config().decode('utf-8')
        config_data = yaml.load(config_info)
        _save_default_config(config_info)

    return config_data

def update_config(updated_data):
    """update the local config file with a dict of new values to store

    """
    global data

    for key in updated_data:
        data[key] = updated_data[key]

    _save_default_config(yaml.dump(data))

data = _load_config()
