"""cr_settings.py: bootstrapper module that loads configuration data.

This kind of sucks since the configuration directory is hard-coded in
and not automatically setup by the program.

"""

import os
import yaml

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "cr_download")
CONFIG_FILE = "config.yaml"

def load_config():
    """load the (YAML-based) config file
    """
    filepath = os.path.join(CONFIG_DIR, CONFIG_FILE)
    with open(filepath, "r") as config_file:
        config_data = yaml.load(config_file)
    return config_data

DATA = load_config()
