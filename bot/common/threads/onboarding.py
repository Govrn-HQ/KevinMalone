import constants
import discord
from common.airtable import (
    find_user,
    update_user,
    get_guild_by_guild_id,
    get_user_record,
    create_user,
)
from config import (
    YES_EMOJI,
    NO_EMOJI,
    SKIP_EMOJI,
    INFO_EMBED_COLOR,
)
from common.threads.thread_builder import (
    BaseStep,
    StepKeys,
    Step,
    ThreadKeys,
    BaseThread,
)
from common.core import bot


def _handle_skip_emoji(raw_reaction, guild_id):
    if SKIP_EMOJI in raw_reaction.emoji.name:
        return None, True
    raise Exception("Reacted with the wrong emoji")


class UserDisplayConfirmationStep(BaseStep):
    name = StepKeys.USER_DISPLAY_CONFIRM.value
    msg = "Would you like your govern display name to be"

    @property
    def emojis():
        return [YES_EMOJI, NO_EMOJI]

    async def send(self, message, user_id):
        user = await bot.fetch_user(user_id)
        channel = message.channel
        sent_message = await channel.send(f"{self.msg} `{user.display_name}`")
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)
        return sent_message, None


# save is a single branch so it can be one to one
# handle_emoji can branch and the airtable logic can handle that
class UserDisplayConfirmationEmojiStep(BaseStep):
    name = StepKeys.USER_DISPLAY_CONFIRM_EMOJI.value
    emoji = True

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
        user = await bot.fetch_user(user_id)
        record_id = await find_user(user_id, guild_id)
        await update_user(record_id, "display_name", user.name)


class UserDisplaySubmitStep(BaseStep):
    name = StepKeys.USER_DISPLAY_SUBMIT.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What would you like your display name to be?"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        record_id = await find_user(user_id, guild_id)
        await update_user(record_id, "display_name", message.content.strip())

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


class AddUserTwitterStep(BaseStep):
    name = StepKeys.ADD_USER_TWITTER.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What twitter handle would you like to associate with this guild!"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        record_id = await find_user(message.author.id, guild_id)
        await update_user(
            record_id, "twitter", message.content.strip().replace("@", "")
        )

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


class AddUserWalletAddressStep(BaseStep):
    name = StepKeys.ADD_USER_WALLET_ADDRESS.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What Ethereum wallet address would you like to associate with this guild!"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        record_id = await find_user(message.author.id, guild_id)
        await update_user(record_id, "wallet", message.content.strip())

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


class AddDiscourseStep(BaseStep):
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
    name = StepKeys.ONBOARDING_CONGRATS.value

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def send(self, message, user_id):
        channel = message.channel
        guild = await bot.fetch_guild(self.guild_id)
        sent_message = await channel.send(
            f"Congratulations on completeing onboading to {guild.name}"
        )
        return sent_message, None

    async def handle_emoji(self, raw_reaction):
        if SKIP_EMOJI in raw_reaction.emoji.name:
            channel = await bot.fetch_channel(raw_reaction.channel_id)
            guild = await bot.fetch_guild(self.guild_id)
            await channel.send(
                f"Congratulations on completeing onboading to {guild.name}"
            )
            return None, False
        raise Exception("Reacted with the wrong emoji")

    async def control_hook(self, message, user_id):
        govrn_profile = await find_user(user_id, constants.Bot.govrn_guild_id)
        if not govrn_profile:
            return StepKeys.GOVRN_PROFILE_PROMPT.value
        return StepKeys.END.value


class GovrnProfilePrompt(BaseStep):
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
    name = StepKeys.GOVRN_PROFILE_PROMPT_REJECT.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "No problem! You are free to join at any time."
        )
        return sent_message, None


class GovrnProfilePromptSuccess(BaseStep):
    name = StepKeys.GOVRN_PROFILE_PROMPT_ACCEPT.value

    def __init__(self, guild_id):
        self.guild_id = guild_id

    async def send(self, message, user_id):
        channel = message.channel
        # Get past guild and add the name
        guild_record = await get_guild_by_guild_id(self.guild_id)

        sent_message = await channel.send(
            "Would you like to reuse your profile data from "
            f"{guild_record.get('guild_name')} guild?"
        )
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)
        return sent_message, None


class GovrnProfilePromptSuccessEmoji(BaseStep):
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
            colour=INFO_EMBED_COLOR, description="We updated your Govrn Profile!",
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
            Step(current=AddUserTwitterStep())
            .add_next_step(AddUserWalletAddressStep())
            .add_next_step(AddDiscourseStep(guild_id=self.guild_id))
            .add_next_step(CongratsStep(guild_id=self.guild_id))
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
            Step(current=UserDisplayConfirmationStep())
            .add_next_step(UserDisplayConfirmationEmojiStep())
            .fork((user_display_accept, data_retrival_chain))
        )
        return steps.build()
