import asyncio
import discord
import json
import logging
import random
import re
import snscrape.modules.twitter as sntwitter
import string

from bot.config import (
    Redis,
    REQUESTED_TWEET_FMT,
    INFO_EMBED_COLOR,
    TWEET_NONCE_LEGNTH,
    TWITTER_URL_REGEXP,
)
from bot.common.bot.bot import bot
import bot.common.graphql as gql
from bot.common.threads.thread_builder import (
    BaseStep,
    StepKeys,
    write_cache_metadata,
    get_cache_metadata_key,
)
from bot.exceptions import ThreadTerminatingException

DISCORD_USER_CACHE_KEY = "discord_user_previously_exists"
USER_CACHE_KEY = "user_previously_exists"
DISCORD_DISPLAY_NAME_CACHE_KEY = "discord_display_name"
TWITTER_HANDLE_CACHE_KEY = "twitter_handle"
REQUESTED_TWEET_CACHE_KEY = "requested_tweet"

logger = logging.getLogger(__name__)


class SelectGuildEmojiStep(BaseStep):
    """A step to allow a user to select a guild

    Typically used at the beginning of threads to
    help set the guild_id value when a user interacts
    in DMs.
    """

    name = StepKeys.SELECT_GUILD_EMOJI.value
    emoji = True

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    async def handle_emoji(self, raw_reaction):
        channel = await bot.fetch_channel(raw_reaction.channel_id)
        message = await channel.fetch_message(raw_reaction.message_id)
        key_vals = await Redis.get(raw_reaction.user_id)
        if not key_vals:
            return None, None
        daos = json.loads(key_vals).get("metadata").get("daos")
        selected_guild_reaction = None
        for reaction in message.reactions:
            if reaction.count >= 2:
                selected_guild_reaction = reaction
                self.cls.guild_id = daos.get(reaction.emoji)["guild_discord_id"]
                break
        if not selected_guild_reaction:
            raise Exception("Reacted with the wrong emoji")
        return None, None


class VerifyUserTwitterStep(BaseStep):
    """Step to verify user's twitter profile"""

    name = StepKeys.VERIFY_USER_TWITTER.value

    def __init__(self, user_id, guild_id, cache):
        super().__init__()
        self.user_id = user_id
        self.guild_id = guild_id
        self.cache = cache

    async def send(self, message, user_id):
        embed_title = (
            "To verify your twitter, please tweet the below message from your"
            " selected account, and reply with the URL to the tweet"
        )
        nonce = self.get_nonce()
        requested_tweet = REQUESTED_TWEET_FMT % nonce

        # save requested tweet in cache
        await write_cache_metadata(
            user_id, self.cache, "requested_tweet", requested_tweet
        )
        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            title=embed_title,
            description=requested_tweet,
        )

        # send request to tweet a given message + nonce
        sent_message = await message.channel.send(embed=embed)
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        await self.verify_message(message)
        await self.save_authenticated_account()

    async def verify_message(self, authentication_message):
        twitter_handle = await get_cache_metadata_key(
            self.user_id, self.cache, TWITTER_HANDLE_CACHE_KEY
        )
        tweet_url = authentication_message.content.strip()
        profile, status_id = verify_twitter_url(tweet_url, twitter_handle)
        tweet = await retrieve_tweet(profile, status_id)
        requested_tweet = await get_cache_metadata_key(
            self.user_id, self.cache, "requested_tweet"
        )
        verify_tweet_text(tweet.content, requested_tweet)

    async def save_authenticated_account(self):
        # retrieve and save handle from cache into airtable
        user_record = await gql.get_user_by_discord_id(self.user_id)
        twitter_handle = await get_cache_metadata_key(
            self.user_id, self.cache, TWITTER_HANDLE_CACHE_KEY
        )
        await gql.update_user_twitter_handle(user_record["id"], twitter_handle)

    def get_nonce(self):
        return "".join(
            random.choice(string.ascii_letters) for i in range(TWEET_NONCE_LEGNTH)
        )


def verify_twitter_url(tweet_url, expected_profile):
    #  ensure the shared tweet matches the account and message
    match = re.search(TWITTER_URL_REGEXP, tweet_url)

    if match is None:
        raise ThreadTerminatingException(
            f"Tweet URL {tweet_url} was not in the expected format"
        )

    profile = match.group(1)

    if profile != expected_profile:
        errMsg = (
            f"Tweet profile {profile} does not match the supplied"
            f" handle {expected_profile}"
        )
        raise ThreadTerminatingException(errMsg)

    status_id = match.group(2)

    return profile, status_id


async def retrieve_tweet(profile, status_id):
    loop = asyncio.get_event_loop()
    scraper = sntwitter.TwitterTweetScraper(status_id)
    gen = scraper.get_items()
    try:
        tweet = await loop.run_in_executor(None, gen.__next__)
    except Exception as e:
        logger.error(
            f"unable to retrieve tweet for profile {profile}, id {status_id}: {e}"
        )
        raise e
    return tweet


def verify_tweet_text(tweet_text, expected_tweet_text):
    if tweet_text != expected_tweet_text:
        raise ThreadTerminatingException(
            f"Tweet text {tweet_text} doesn't match the verification"
            f" tweet {expected_tweet_text}"
        )
