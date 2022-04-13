from bot import constants
from datetime import datetime, timedelta
import asyncio
import discord
import re
import twint
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from bot.common.airtable import (
    find_user,
    update_member,
    update_user,
    get_guild_by_guild_id,
    get_user_record,
    create_user,
)
from bot.config import (
    MAX_TWEET_LOOKBACK_MINUTES,
    MAX_TWEETS_TO_RETRIEVE,
    YES_EMOJI,
    NO_EMOJI,
    SKIP_EMOJI,
    INFO_EMBED_COLOR,
    REQUESTED_TWEET,
    TWITTER_URL_REGEXP,
    REQUESTED_SIGNED_MESSAGE,
    WALLET_VERIFICATION_INSTRUCTIONS,
)
from bot.common.threads.thread_builder import (
    BaseStep,
    StepKeys,
    Step,
    ThreadKeys,
    BaseThread,
    get_cache_metadata,
    write_cache_metadata,
)
from bot.exceptions import ThreadTerminatingException

TWITTER_HANDLE_STORAGE_KEY = "twitter"
WALLET_STORAGE_KEY = "wallet"


def _handle_skip_emoji(raw_reaction, guild_id):
    if SKIP_EMOJI in raw_reaction.emoji.name:
        return None, True
    raise Exception("Reacted with the wrong emoji")


class UserDisplayConfirmationStep(BaseStep):
    """Confirm display name fetched from discord"""

    name = StepKeys.USER_DISPLAY_CONFIRM.value
    msg = "Would you like your Govrn display name to be"

    def __init__(self, bot):
        self.bot = bot

    @property
    def emojis():
        return [YES_EMOJI, NO_EMOJI]

    async def send(self, message, user_id):
        user = await self.bot.fetch_user(user_id)
        channel = message.channel
        sent_message = await channel.send(f"{self.msg} `{user.display_name}`")
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)
        return sent_message, None


# save is a single branch so it can be one to one
# handle_emoji can branch and the airtable logic can handle that
class UserDisplayConfirmationEmojiStep(BaseStep):
    """Emoji confirmation step of whether the Discord name should be accepted"""

    name = StepKeys.USER_DISPLAY_CONFIRM_EMOJI.value
    emoji = True

    def __init__(self, bot):
        self.bot = bot

    @property
    def emojis(self):
        return [YES_EMOJI, NO_EMOJI]

    async def handle_emoji(self, raw_reaction):
        if raw_reaction.emoji.name in self.emojis:
            if raw_reaction.emoji.name == NO_EMOJI:
                return StepKeys.USER_DISPLAY_SUBMIT.value, None
            return StepKeys.ADD_USER_TWITTER.value, None
        raise Exception("Reacted with the wrong emoji")

    async def save(self, message, guild_id, user_id):
        user = await self.bot.fetch_user(user_id)
        record_id = await find_user(user_id, guild_id)
        await update_user(record_id, "display_name", user.name)
        user_record = await get_user_record(user_id, guild_id)
        member_id = user_record.get("fields").get("Members")[0]
        await update_member(member_id, "Name", user.name)


class UserDisplaySubmitStep(BaseStep):
    """Submit new display name to be saved"""

    name = StepKeys.USER_DISPLAY_SUBMIT.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What would you like your display name to be?"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        record_id = await find_user(user_id, guild_id)
        val = message.content.strip()
        await update_user(record_id, "display_name", val)
        user_record = await get_user_record(user_id, guild_id)
        member_id = user_record.get("fields").get("Members")[0]
        await update_member(member_id, "Name", val)

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


class AddUserAccount:
    """Prompts user for an account name."""

    def __init__(
        self,
        cache,
        get_account_descriptor,
        sanititze_account_input,
        get_account_storage_key,
    ):
        self.cache = cache
        self.get_account_descriptor = get_account_descriptor
        self.sanitize_account_input = sanititze_account_input
        self.get_account_storage_key = get_account_storage_key

    async def send(self, message):
        channel = message.channel
        sent_message = await channel.send(
            f"What {self.get_account_descriptor()}"
            " would you like to associate with this guild?"
        )
        return sent_message, None

    async def save(self, message, user_id):
        metadata_key = self.get_account_storage_key()
        account_name = self.sanitize_account_input(message)
        await write_cache_metadata(user_id, self.cache, metadata_key, account_name)


class PromptForAccountVerification:
    """Prompts user for authenticated message"""

    def __init__(self, get_account_verification_prompts):
        self.get_account_verification_prompts = get_account_verification_prompts

    async def prompt(self, message):
        channel = message.channel
        verification_embeds = self.get_account_verification_prompts()
        last_sent = None
        for verification_embed in verification_embeds:
            last_sent = await channel.send(embed=verification_embed)
        return last_sent


class VerifyAccount:
    """Verififes the response to the authentication prompt for a given account"""

    def __init__(self, verify_account, save_authenticated_account):
        self.verify_account = verify_account
        self.save_authenticated_account = save_authenticated_account

    async def verify(self, message):
        # this should throw if the verification fails
        await self.verify_account(message)
        # account can be retrieved from metadata
        await self.save_authenticated_account()

        return message, None


class AddUserTwitterStep(BaseStep):
    """Step to submit twitter name for the govrn profile"""

    name = StepKeys.ADD_USER_TWITTER.value

    def __init__(self, cache):
        super().__init__()
        self.add_user_account = AddUserAccount(
            cache,
            self.get_account_descriptor,
            self.sanitize_account_input,
            self.get_account_storage_key,
        )

    async def send(self, message, user_id):
        return await self.add_user_account.send(message)

    async def save(self, message, guild_id, user_id):
        await self.add_user_account.save(message, user_id)

    def get_account_descriptor(self):
        return "twitter handle"

    def sanitize_account_input(self, message):
        return message.content.strip().replace("@", "")

    def get_account_storage_key(self):
        return TWITTER_HANDLE_STORAGE_KEY


class PromptUserTweetStep(BaseStep):
    """Prompts user to share a URL to a tweet sent from their account"""

    name = StepKeys.PROMPT_USER_TWEET.value

    def __init__(self):
        super().__init__()

        self.prompt_for_verification = PromptForAccountVerification(
            self.get_account_verification_prompts
        )

    async def send(self, message, user_id):
        return await self.prompt_for_verification.prompt(message), None

    def get_account_verification_prompts(self):
        embed_title = (
            "To verify your twitter, please tweet the below message from your"
            " selected account, and reply with the URL to the tweet"
        )
        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            title=embed_title,
            description=REQUESTED_TWEET,
        )
        return [embed]


class VerifyUserTwitterStep(BaseStep):
    """Step to verify user's twitter profile"""

    trigger = True
    name = StepKeys.VERIFY_USER_TWITTER.value

    def __init__(self, user_id, guild_id, cache):
        super().__init__()
        self.user_id = user_id
        self.guild_id = guild_id
        self.cache = cache
        self.verify_account = VerifyAccount(
            self.verify_message, self.save_authenticated_account
        )

    async def send(self, message, user_id):
        return await self.verify_account.verify(message)

    async def verify_message(self, authentication_message):
        twitter_handle = await get_cache_metadata(
            self.user_id, self.cache, TWITTER_HANDLE_STORAGE_KEY
        )
        tweet_url = authentication_message.content.strip()
        profile, status_id = verify_twitter_url(tweet_url, twitter_handle)
        tweet_text = await retrieve_tweet(profile, status_id)
        verify_tweet_text(tweet_text, REQUESTED_TWEET)

    async def save_authenticated_account(self):
        # retrieve and save handle from cache into airtable
        record_id = await find_user(self.user_id, self.guild_id)
        twitter_handle = await get_cache_metadata(
            self.user_id, self.cache, TWITTER_HANDLE_STORAGE_KEY
        )
        await update_user(record_id, "twitter", twitter_handle)


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
    tweets = []
    kmalone_tweet = None

    def _retrieve_tweet():
        try:
            since = datetime.now() - timedelta(minutes=MAX_TWEET_LOOKBACK_MINUTES)
            c = twint.Config()
            c.Username = profile
            c.Limit = MAX_TWEETS_TO_RETRIEVE
            c.Since = since.strftime("%Y-%m-%d %H:%M:%S")
            c.Store_object = True
            c.Store_object_tweets_list = tweets
            twint.run.Search(c)
        except Exception as e:
            raise ThreadTerminatingException(
                f"Error in retrieving tweet {status_id} from {profile}: {e}"
            )

        return tweets

    tweets = await loop.run_in_executor(None, _retrieve_tweet)

    for tweet in tweets:
        if str(tweet.id) == status_id:
            kmalone_tweet = tweet.tweet
            break

    if kmalone_tweet is None:
        err_msg = (
            f"Could not find tweet with supplied id {status_id} in {profile}'s"
            f" twitter history. Please make sure that you tweeted in the last"
            f" {MAX_TWEET_LOOKBACK_MINUTES} minutes, and the verification tweet is"
            f" among your {MAX_TWEETS_TO_RETRIEVE} most recent."
        )
        raise ThreadTerminatingException(err_msg)

    return kmalone_tweet


def verify_tweet_text(tweet_text, expected_tweet_text):
    if tweet_text != expected_tweet_text:
        raise ThreadTerminatingException(
            f"Tweet text {tweet_text} doesn't match the verification"
            f" tweet {expected_tweet_text}"
        )


class AddUserWalletAddressStep(BaseStep):
    """Step to submit wallet address for the govrn profile"""

    name = StepKeys.ADD_USER_WALLET_ADDRESS.value

    def __init__(self, cache):
        super().__init__()
        self.add_user_account = AddUserAccount(
            cache,
            self.get_account_descriptor,
            self.sanitize_account_input,
            self.get_account_storage_key,
        )

    async def send(self, message, user_id):
        return await self.add_user_account.send(message)

    async def save(self, message, guild_id, user_id):
        await self.add_user_account.save(message, user_id)

    def get_account_descriptor(self):
        return "Ethereum wallet address"

    def sanitize_account_input(self, message):
        stripped_message = message.content.strip()
        if not Web3.isAddress(stripped_message):
            raise ThreadTerminatingException(
                f"Supplied address {stripped_message} is not a valid ethereum address"
            )

        return stripped_message

    def get_account_storage_key(self):
        return WALLET_STORAGE_KEY

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


class PromptUserWalletMessageSignatureStep(BaseStep):
    """Prompts the user to sign a message with their specified wallet"""

    name = StepKeys.PROMPT_USER_WALLET_ADDRESS.value

    def __init__(self):
        super().__init__()
        self.prompt_for_verification = PromptForAccountVerification(
            self.get_account_verification_prompts
        )

    async def send(self, message, user_id):
        return await self.prompt_for_verification.prompt(message), None

    def get_account_verification_prompts(self):
        instructions_embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            title="Verification instructions",
            description=WALLET_VERIFICATION_INSTRUCTIONS,
        )

        prompt = discord.Embed(
            colour=INFO_EMBED_COLOR,
            title="Please sign the below message with your wallet",
            description=REQUESTED_SIGNED_MESSAGE,
        )
        return [instructions_embed, prompt]


class VerifyUserWalletMessageSignatureStep(BaseStep):
    """Verifies the message supplied by the user was signed by their specified wallet"""

    trigger = True
    name = StepKeys.VERIFY_USER_WALLET_ADDRESS.value

    def __init__(self, user_id, guild_id, cache):
        super().__init__()
        self.user_id = user_id
        self.guild_id = guild_id
        self.cache = cache
        self.verify_account = VerifyAccount(
            self.verify_message, self.save_authenticated_account
        )

    async def send(self, message, user_id):
        return await self.verify_account.verify(message)

    async def verify_message(self, authentication_message):
        address = await get_cache_metadata(self.user_id, self.cache, WALLET_STORAGE_KEY)
        stripped_supplied_signature = authentication_message.content.strip()

        try:
            int(stripped_supplied_signature, 16)
        except ValueError:
            raise ThreadTerminatingException("The response wasn't a correct signature!")

        requested_msg_hex = encode_defunct(text=REQUESTED_SIGNED_MESSAGE)
        recovered_address = Account.recover_message(
            requested_msg_hex, signature="0x" + stripped_supplied_signature
        )

        if address != recovered_address:
            raise ThreadTerminatingException(
                "Recovered address from message & signature doesn't match supplied."
                " Make sure there's no extra line when pasting the message into"
                " myetherwallet.com's signature box."
            )

    async def save_authenticated_account(self):
        #  retrieve and save handle from cache into airtable
        record_id = await find_user(self.user_id, self.guild_id)
        wallet_address = await get_cache_metadata(
            self.user_id, self.cache, WALLET_STORAGE_KEY
        )
        await update_user(record_id, WALLET_STORAGE_KEY, wallet_address)


class AddDiscourseStep(BaseStep):
    """Step to submit discourse username for the govrn profile"""

    name = StepKeys.ADD_USER_DISCOURSE.value

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What discourse handle would you like to associate with this guild!"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        record_id = await find_user(message.author.id, guild_id)
        await update_user(record_id, "discourse", message.content.strip())

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


class CongratsStep(BaseStep):
    """Send congratulations for completing the profile"""

    name = StepKeys.ONBOARDING_CONGRATS.value

    def __init__(self, guild_id, bot):
        super().__init__()
        self.guild_id = guild_id
        self.bot = bot

    async def send(self, message, user_id):
        channel = message.channel
        guild = await self.bot.fetch_guild(self.guild_id)
        sent_message = await channel.send(
            f"Congratulations on completeing onboarding to {guild.name}"
        )
        return sent_message, None

    async def handle_emoji(self, raw_reaction):
        if SKIP_EMOJI in raw_reaction.emoji.name:
            channel = await self.bot.fetch_channel(raw_reaction.channel_id)
            guild = await self.bot.fetch_guild(self.guild_id)
            await channel.send(
                f"Congratulations on completeing onboarding to {guild.name}"
            )
            return None, False
        raise Exception("Reacted with the wrong emoji")

    async def control_hook(self, message, user_id):
        govrn_profile = await find_user(user_id, constants.Bot.govrn_guild_id)
        if not govrn_profile:
            return StepKeys.GOVRN_PROFILE_PROMPT.value
        return StepKeys.END.value


class GovrnProfilePrompt(BaseStep):
    """Ask whether user wants to join the Govrn guild"""

    name = StepKeys.GOVRN_PROFILE_PROMPT.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "Would you like to be onboarded to the govrn guild as well?"
        )
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)
        return sent_message, None


class GovrnProfilePromptEmoji(BaseStep):
    """Accept user emoji reaction to whether they want to join Govrn"""

    name = StepKeys.GOVRN_PROFILE_PROMPT_EMOJI.value

    @property
    def emojis(self):
        return [YES_EMOJI, NO_EMOJI]

    async def handle_emoji(self, raw_reaction):
        if raw_reaction.emoji.name in self.emojis:
            if raw_reaction.emoji.name == NO_EMOJI:
                return StepKeys.GOVRN_PROFILE_PROMPT_REJECT.value, None
            return StepKeys.GOVRN_PROFILE_PROMPT_ACCEPT.value, None
        raise Exception("Reacted with the wrong emoji")


class GovrnProfilePromptReject(BaseStep):
    """Handle situation where does not want to join the govrn guild"""

    name = StepKeys.GOVRN_PROFILE_PROMPT_REJECT.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "No problem! You are free to join at any time."
        )
        return sent_message, None


class GovrnProfilePromptSuccess(BaseStep):
    """Ask user whether they want to reuse their guild profile"""

    name = StepKeys.GOVRN_PROFILE_PROMPT_ACCEPT.value

    def __init__(self, guild_id):
        self.guild_id = guild_id

    async def send(self, message, user_id):
        channel = message.channel
        # Get past guild and add the name
        record = await get_guild_by_guild_id(self.guild_id)
        fields = record.get("fields")

        sent_message = await channel.send(
            "Would you like to reuse your profile data from "
            f"{fields.get('guild_name')} guild?"
        )
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)
        return sent_message, None


class GovrnProfilePromptSuccessEmoji(BaseStep):
    """Handle user reaction to whether they want to reuse their profile"""

    name = StepKeys.GOVRN_PROFILE_PROMPT_ACCEPT_EMOJI.value

    def __init__(self, parent):
        self.parent = parent

    @property
    def emojis(self):
        return [YES_EMOJI, NO_EMOJI]

    async def handle_emoji(self, raw_reaction):
        if raw_reaction.emoji.name in self.emojis:
            await create_user(self.parent.user_id, constants.Bot.govrn_guild_id)
            if NO_EMOJI in raw_reaction.emoji.name:
                self.parent.guild_id = constants.Bot.govrn_guild_id
                return StepKeys.USER_DISPLAY_SUBMIT.value, None
            return StepKeys.GOVRN_PROFILE_REUSE.value, None
        raise Exception("Reacted with the wrong emoji")


class GovrnProfilePromptReuse(BaseStep):
    name = StepKeys.GOVRN_PROFILE_REUSE.value

    def __init__(self, guild_id):
        self.guild_id = guild_id

    async def send(self, message, user_id):
        channel = message.channel
        current_profile = await get_user_record(user_id, self.guild_id)
        fields = current_profile.get("fields")

        govrn_profile = await get_user_record(user_id, constants.Bot.govrn_guild_id)
        record_id = govrn_profile.get("id")
        await update_user(record_id, "display_name", fields.get("display_name"))
        await update_user(record_id, "twitter", fields.get("twitter"))
        await update_user(record_id, "wallet", fields.get("wallet"))
        await update_user(record_id, "discourse", fields.get("discourse"))

        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description="We updated your Govrn Profile!",
        )
        embed.add_field(name="Display Name", value=fields.get("display_name"))
        embed.add_field(name="Twitter", value=fields.get("twitter"))
        embed.add_field(name="Ethereum Wallet Address", value=fields.get("wallet"))
        embed.add_field(name="Discourse Handle", value=fields.get("discourse"))

        sent_message = await channel.send(embed=embed)
        return sent_message, None


# Threads #


class Onboarding(BaseThread):
    name = ThreadKeys.ONBOARDING.value

    def _govrn_oboard_steps(self):
        success = (
            Step(current=GovrnProfilePromptSuccess(guild_id=self.guild_id))
            .add_next_step(GovrnProfilePromptSuccessEmoji(parent=self))
            .fork(
                [
                    Step(current=GovrnProfilePromptReuse(guild_id=self.guild_id)),
                    Step(current=UserDisplaySubmitStep())
                    .add_next_step(self._data_retrival_steps().build())
                    .build(),
                ]
            )
            .build()
        )
        reject = Step(current=GovrnProfilePromptReject())
        steps = (
            Step(current=GovrnProfilePrompt())
            .add_next_step(GovrnProfilePromptEmoji())
            .fork([success, reject])
        )
        return steps

    def _data_retrival_steps(self):
        return (
            Step(current=AddUserTwitterStep(self.cache))
            .add_next_step(PromptUserTweetStep())
            .add_next_step(
                VerifyUserTwitterStep(self.user_id, self.guild_id, self.cache)
            )
            .add_next_step(AddUserWalletAddressStep(self.cache))
            .add_next_step(PromptUserWalletMessageSignatureStep())
            .add_next_step(
                VerifyUserWalletMessageSignatureStep(
                    self.user_id, self.guild_id, self.cache
                )
            )
            .add_next_step(AddDiscourseStep(guild_id=self.guild_id))
            .add_next_step(CongratsStep(guild_id=self.guild_id, bot=self.bot))
        )

    async def get_steps(self):
        data_retrival_chain = (
            self._data_retrival_steps()
            .add_next_step(self._govrn_oboard_steps().build())
            .build()
        )

        user_display_accept = (
            Step(current=UserDisplaySubmitStep())
            .add_next_step(data_retrival_chain)
            .build()
        )
        steps = (
            Step(current=UserDisplayConfirmationStep(bot=self.bot))
            .add_next_step(UserDisplayConfirmationEmojiStep(bot=self.bot))
            .fork((user_display_accept, data_retrival_chain))
        )
        return steps.build()
