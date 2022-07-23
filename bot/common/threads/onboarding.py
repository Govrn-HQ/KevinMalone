import discord
from web3 import Web3
from bot.common.graphql import (
    get_guild_by_discord_id,
    create_user as _create_user,
    create_guild_user,
    update_user_display_name,
    update_user_twitter_handle,
)
from bot.config import (
    YES_EMOJI,
    NO_EMOJI,
    SKIP_EMOJI,
    INFO_EMBED_COLOR,
)
from bot.common.threads.thread_builder import (
    BaseStep,
    StepKeys,
    Step,
    ThreadKeys,
    BaseThread,
    get_cache_metadata_key,
    write_cache_metadata,
)
from bot.exceptions import ThreadTerminatingException


def _handle_skip_emoji(raw_reaction, guild_id):
    if SKIP_EMOJI in raw_reaction.emoji.name:
        return None, True
    raise Exception("Reacted with the wrong emoji")


async def create_user(discord_id, guild_id, wallet):
    user = await _create_user(discord_id, wallet)
    await create_guild_user(user.get("id"), guild_id)


class UserDisplayConfirmationStep(BaseStep):
    """Confirm display name fetched from discord"""

    name = StepKeys.USER_DISPLAY_CONFIRM.value
    msg = "Would you like your display name to be"

    def __init__(self, bot):
        self.bot = bot

    @property
    def emojis():
        return [YES_EMOJI, NO_EMOJI]

    async def send(self, message, user_id):
        user = await self.bot.fetch_user(user_id)
        channel = message.channel
        print(dir(user))
        sent_message = await channel.send(f"{self.msg} `{user.display_name}`")
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)
        return sent_message, None


# save is a single branch so it can be one to one
# handle_emoji can branch
class UserDisplayConfirmationEmojiStep(BaseStep):
    """Emoji confirmation step of whether the Discord name should be accepted"""

    name = StepKeys.USER_DISPLAY_CONFIRM_EMOJI.value
    emoji = True

    def __init__(self, cache, bot):
        self.cache = cache
        self.bot = bot

    @property
    def emojis(self):
        return [YES_EMOJI, NO_EMOJI]

    async def handle_emoji(self, raw_reaction):
        if raw_reaction.emoji.name in self.emojis:
            if raw_reaction.emoji.name == NO_EMOJI:
                return StepKeys.USER_DISPLAY_SUBMIT.value, None
            return StepKeys.CREATE_USER_WITH_WALLET_ADDRESS.value, None
        raise Exception("Reacted with the wrong emoji")

    async def save(self, message, guild_id, user_id):
        user = await self.bot.fetch_user(user_id)
        await write_cache_metadata(
            user_id, self.cache, "display_name", user.display_name
        )


class UserDisplaySubmitStep(BaseStep):
    """Submit new display name to be saved"""

    name = StepKeys.USER_DISPLAY_SUBMIT.value

    def __init__(self, cache):
        self.cache = cache

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What would you like your display name to be?"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        display_name = message.content.strip()
        await write_cache_metadata(user_id, self.cache, "display_name", display_name)

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


class CreateUserWithWalletAddressStep(BaseStep):
    """Step to submit wallet address for the govrn profile"""

    name = StepKeys.CREATE_USER_WITH_WALLET_ADDRESS.value

    def __init__(self, cache, guild_id):
        super().__init__()
        self.cache = cache
        self.guild_id = guild_id

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What Ethereum wallet address would you like to associate with this guild?"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        wallet = message.content.strip()

        if not Web3.isAddress(wallet):
            raise ThreadTerminatingException(f"{wallet} is not a valid wallet address")

        display_name = await get_cache_metadata_key(user_id, self.cache, "display_name")
        guild = await get_guild_by_discord_id(guild_id)

        # user creation is performed when supplying wallet address since this
        # is a mandatory field for the user record
        # TODO: wrap into a single CRUD
        user = await create_user(user_id, guild.get("id"), wallet)
        user_db_id = user.get("id")
        await update_user_display_name(user_db_id, display_name)
        await write_cache_metadata(user_id, self.cache, "user_db_id", user_db_id)


class AddUserTwitterStep(BaseStep):
    """Step to submit twitter name for the govrn profile"""

    name = StepKeys.ADD_USER_TWITTER.value

    def __init__(self, guild_id, cache):
        super().__init__()
        self.guild_id = guild_id
        self.cache = cache

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What twitter handle would you like to associate with this guild!"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        twitter_handle = message.content.strip().replace("@", "")
        user_db_id = await get_cache_metadata_key(user_id, self.cache, "user_db_id")
        await update_user_twitter_handle(user_db_id, twitter_handle)

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


class CongratsStep(BaseStep):
    """Send congratulations for completing the profile"""

    name = StepKeys.ONBOARDING_CONGRATS.value

    def __init__(self, user_id, guild_id, cache):
        super().__init__()
        self.user_id = user_id
        self.guild_id = guild_id
        self.cache = cache

    async def send(self, message, user_id):
        channel = message.channel
        guild_name = await get_cache_metadata_key(user_id, self.cache, "guild_name")
        sent_message = await channel.send(
            f"Nice job! That's it for now! "
            f"Welcome and congratulations on onboarding to {guild_name}"
        )
        return sent_message, None


def get_profile_embed_from_profile_fields(guild_name, fields):
    embed = discord.Embed(
        colour=INFO_EMBED_COLOR,
        description=f"We updated your {guild_name} profile!",
    )
    embed.add_field(name="Display Name", value=fields.get("display_name"))
    embed.add_field(name="Twitter", value=fields.get("twitter"))
    embed.add_field(name="Ethereum Wallet Address", value=fields.get("wallet"))

    return embed


class Onboarding(BaseThread):
    name = ThreadKeys.ONBOARDING.value

    def _data_retrival_steps(self):
        return (
            Step(
                current=CreateUserWithWalletAddressStep(
                    cache=self.cache, guild_id=self.guild_id
                )
            )
            .add_next_step(AddUserTwitterStep(guild_id=self.guild_id, cache=self.cache))
            .add_next_step(CongratsStep(self.user_id, self.guild_id, self.cache))
        )

    def get_profile_setup_steps(self):
        data_retrival_steps = self._data_retrival_steps().build()

        custom_user_name_steps = (
            Step(current=UserDisplaySubmitStep(cache=self.cache))
            .add_next_step(data_retrival_steps)
            .build()
        )

        profile_setup_steps = (
            Step(current=UserDisplayConfirmationStep(bot=self.bot))
            .add_next_step(
                UserDisplayConfirmationEmojiStep(cache=self.cache, bot=self.bot)
            )
            .fork((custom_user_name_steps, data_retrival_steps))
        )

        return profile_setup_steps.build()

    async def get_steps(self):
        return self.get_profile_setup_steps().build()
