import discord
import aioredis
from bot import constants

GUILD_IDS = [747131845317230695, 799328534988193793]
REDIS_URL = constants.Bot.redis_url
AIRTABLE_KEY = constants.Bot.airtable_key
AIRTABLE_BASE = constants.Bot.airtable_base

REQUESTED_TWEET_FMT = "Kevin Malone told me to tweet this number {} on {}"
TWITTER_URL_REGEXP = r"^https://twitter.com/(.+)/status/([0-9]+)"
MAX_TWEETS_TO_RETRIEVE = 5
MAX_TWEET_LOOKBACK_MINUTES = 10

REQUESTED_SIGNED_MESSAGE = "Kevin Malone told me to sign this"
WALLET_VERIFICATION_INSTRUCTIONS = (
    "To verify you have access to the wallet at your address, follow these steps:"
    "\n1: Navigate to myetherwallet.com/wallet/sign"
    "\n2: When prompted, connect with your metamask wallet in the browser"
    "\n3: Copy and paste the message below into the 'Signature' box"
    "\n4: Click the 'Sign' button"
    "\n5: Approve the metamask notification and sign the message"
    "\n6: Copy the long string right after 'sig' (without quotes)"
    "\n7: Paste that string into this conversation to verify ownership"
)

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
