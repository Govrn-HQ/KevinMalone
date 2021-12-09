import json
import os

GUILD_IDS = [747131845317230695, 799328534988193793]
AIRTABLE_KEY = os.getenv("AIRTABLE_KEY")
AIRTABLE_BASE = os.getenv("AIRTABLE_BASE")


def read_file():
    with open("govrn_config.json") as f:
        return json.load(f)
