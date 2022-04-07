import discord
import json
import aioredis
from bot import constants

GUILD_IDS = [747131845317230695, 799328534988193793]
REDIS_URL = constants.Bot.redis_url
AIRTABLE_KEY = constants.Bot.airtable_key
AIRTABLE_BASE = constants.Bot.airtable_base

YES_EMOJI = "\U0001F44D"
NO_EMOJI = "\U0001F44E"
SKIP_EMOJI = "\U000023ED"

ALIEN_EMOJI = "\U0001F47D"
ALIEN_MONSTER_EMOJI = "\U0001F47E"
ROBOT_EMOJI = "\U0001F916"
GHOST_EMOJI = "\U0001F47B"
CLOWN_EMOJI = "\U0001F921"

REPORTING_FORM_FMT = "https://report.govrn.app/#/contribution/%s"

emojis = [ALIEN_EMOJI, ALIEN_MONSTER_EMOJI, ROBOT_EMOJI, GHOST_EMOJI, CLOWN_EMOJI]


def get_list_of_emojis(num):
    return emojis[0:num]


INFO_EMBED_COLOR = discord.Colour.blue()
Redis = aioredis.from_url(f"{REDIS_URL}")
