import yaml
from typing import List, Dict
from itertools import tee, filterfalse

def load_config(config_path: str):
    '''Opens the YAML config file at the given path. '''
    try:
        with open(config_path, 'r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return config
    except FileNotFoundError:
        raise Exception(f'Config file not found at path {config_path}.')
    except Exception as e:
        raise e

def check_config(config: Dict, top_level_key: str, config_keys: List[str], obj=None):
    '''config should be a dictionary containing settings.
    top_level_key should be a top-level key in config, corresponding to a particular set of keys/values. 
    config_keys should be a list of keys to check for in section.
    obj should be an optional reference to the Python object to which to add the config keys/values as attributes. Otherwise, they are returned as a dict.'''
    try:
        if top_level_key not in config:
            raise Exception(f'{config_path} should contain a dictionary of settings, stored under the {top_level_key} key.')
        config_keys = set(config_keys)
        # Test for the presence of the required API settings
        if not config_keys <= set(config[top_level_key].keys()):
            raise Exception(f'One or more LibCal API settings missing from {config_path}')
        # For convenience, convert to class attributes
        if obj:
            for c in config_keys:
                setattr(obj, c, config[top_level_key][c])
            return obj
        else:
            return config[top_level_key]
    except Exception as e:
        raise Exception("Error loading configuration.") from e

def partition(pred, iterable):
    '''Use a predicate to partition entries into false entries and true entries. From itertools recipes'''
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)