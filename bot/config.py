import json

GUILD_IDS = [747131845317230695]


def read_file():
    with open("govern_config.json") as f:
        return json.load(f)
