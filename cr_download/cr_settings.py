import os
import yaml

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "cr_download")
CONFIG_FILE = "config.yaml"

def load_config():
    filepath = os.path.join(CONFIG_DIR, CONFIG_FILE)
    with open(filepath, "r") as fp:
        config_data = yaml.load(fp)
    return config_data

DATA = load_config()
