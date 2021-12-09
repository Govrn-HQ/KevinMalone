import discord
import json
import os
import redis

GUILD_IDS = [747131845317230695, 799328534988193793]
REDIS_HOST = os.getenv("REDIS_HOST")


def read_file():
    with open("govrn_config.json") as f:
        return json.load(f)


INFO_EMBED_COLOR = discord.Colour.blue()
Redis = redis.Redis(host=REDIS_HOST, port=6379, db=0)
