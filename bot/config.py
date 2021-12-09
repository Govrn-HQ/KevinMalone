import discord
import json
import os
import aioredis

GUILD_IDS = [747131845317230695, 799328534988193793]
REDIS_HOST = os.getenv("REDIS_HOST")


def read_file():
    with open("govrn_config.json") as f:
        return json.load(f)


INFO_EMBED_COLOR = discord.Colour.blue()
Redis = aioredis.from_url(f"redis://{REDIS_HOST}")
