import discord
import json
import os
import aioredis
import constants

GUILD_IDS = [747131845317230695, 799328534988193793]
REDIS_HOST = constants.Bot.redis_host
AIRTABLE_KEY = constants.Bot.airtable_key
AIRTABLE_BASE = constants.Bot.airtable_base

YES_EMOJI = "\U0001F44D"
NO_EMOJI = "\U0001F44E"
SKIP_EMOJI = "\U000023ED"


def read_file():
    with open("govrn_config.json") as f:
        return json.load(f)


INFO_EMBED_COLOR = discord.Colour.blue()
Redis = aioredis.from_url(f"redis://{REDIS_HOST}")
