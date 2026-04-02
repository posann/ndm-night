import os
import json

def load_config(config_file):
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config
        except:
            pass
    return {}

def save_config(config_file, downloads_data=None):
    config = {
        'downloads': downloads_data or []
    }
    with open(config_file, 'w') as f:
        json.dump(config, f)
