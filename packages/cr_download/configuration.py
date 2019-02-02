"""cr_settings.py: bootstrapper module that loads configuration data.

"""

import os
import os.path as path
import pkg_resources
from pathlib import Path

from ruamel.yaml import YAML

from . import appdata
from .name import APP_NAME

yaml = YAML(typ="safe")

_XDG_CONFIG_HOME = (os.environ.get('XDG_CONFIG_HOME')
                    or path.join(path.expanduser("~"), ".config"))

CONFIG_DIR = path.join(_XDG_CONFIG_HOME, APP_NAME)
CONFIG_FILE = "config.yaml"

CONFIG_PATH = path.join(CONFIG_DIR, CONFIG_FILE)

CONFIG_EXCLUDES = ["writeable_data"]

class Configuration:
    """Provide a namespace for program configuration."""
    def __init__(self, init_data):
        self.writeable_data = {}
        if init_data:
            self.update(init_data, writeable=True)


    def update(self, update_data, writeable=False):
        """update the contents of the program configuration.

        If writeable is specified, then updates will be saved to the
        user's default config file next time that file is regenerated

        """

        to_update = {k:v for k, v in update_data.items()
                     if k not in CONFIG_EXCLUDES}
        self.__dict__.update(to_update)

        if writeable:
            self.writeable_data.update(to_update)

    def save_default(self):
        """save some of the configuration data to the user's default config
        file"""
        _save_default_config(self.writeable_data)

def _get_default_config():
    res_str = appdata.resource_string(CONFIG_FILE)
    return Configuration(yaml.load(res_str.decode('utf-8')))

def _save_default_config(config_dict):
    try:
        os.makedirs(CONFIG_DIR)
    except os.error:
        pass

    yaml.dump(config_dict, Path(CONFIG_PATH))

def _load_config():
    config = _get_default_config()
    try:
        with open(CONFIG_PATH, "r") as config_file:
            config.update(yaml.load(config_file))
    except(IOError, FileNotFoundError):
        config.save_default()

    return config

data = _load_config()
