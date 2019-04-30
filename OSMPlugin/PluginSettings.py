
from __future__ import with_statement

import os
import json


def load():
    path = os.path.dirname(os.path.abspath(__file__)) + '\config.json'

    if not os.path.isfile(path):
        create_default_settings_file()

    with open(path) as json_data_file:
        data = json.load(json_data_file)

    return data

def get(key):
    if key in DATA:
        return DATA[key]

def set(key, value):
    if key in DATA:
        DATA[key] = value
        _save(DATA)

# def create_default_settings_file():
#     settings = {
#         "host": "",
#         "port": "",
#         "dbname": "",
#         "user": "",
#         "password": "",
#
#         "municipios": {
#             "table_name": "",
#             "geocodigo_field": "",
#             "geom_field": ""
#         },
#         "cete_table": "",
#         "osm_table": "",
#
#         "geocod": "",
#         "buffers_size": ""
#     }
#
#     _save(settings)

def create_default_settings_file():
    settings = {
        "connection_info": {
            "host": "",
            "port": "",
            "dbname": "",
            "user": "",
            "password": ""
        },
        "municipios_info": {
            "table_name": "",
            "name_field": "",
            "geocodigo_field": "",
            "geom_field": ""
        },
        "cete_info": {
            "table_name": "",
            "id_field": "",
            "name_field": "",
            "geom_field": ""
        },
        "osm_info": {
            "table_name": "",
            "id_field": "",
            "name_field": "",
            "geom_field": ""
        },
        "config_info": {
            "buffer_size": 15,
            "only_one_layer": True
        },
        "table_data": []
    }

    _save(settings)

def _save(settings):
    with open(PATH, 'w') as file_:
        json.dump(settings, file_)

PATH = os.path.dirname(os.path.abspath(__file__)) + '\config.json'
DATA = load()