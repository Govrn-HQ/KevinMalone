import discord
import json

GUILD_IDS = [747131845317230695, 799328534988193793]


def read_file():
    with open("govrn_config.json") as f:
        return json.load(f)


INFO_EMBED_COLOR = discord.blue
