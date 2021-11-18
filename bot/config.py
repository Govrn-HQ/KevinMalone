import json


def read_file():
    with open("govern_config.json") as f:
        return json.load(f)
