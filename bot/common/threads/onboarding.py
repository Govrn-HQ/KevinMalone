import constants
from common.airtable import find_user, update_user
from config import (
    YES_EMOJI,
    NO_EMOJI,
    SKIP_EMOJI,
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
            # Trigger govrn onboarding thread
            # If they want the same fields handle in emoji
            # not throw them back in the onboarding flow
            # this will have the filled in fields as metadata and have one step
            # then through them back into the onboarding thread if they opt to
            #
            # TODO we should also send prompt
            # This will no longer happen in the congrats step
            # But will move in the step above
            return StepKeys.GOVRN_PROFILE_PROMPT.value
        return StepKeys.END.value


## Make sure to pass the metadata to all steps
class GovrnProfilePrompt:
    name = StepKeys.GOVRN_PROFILE_PROMPT.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            f"Would you like to be onboarded to the govrn guild as well?"
        )
        return sent_message, None


class GovrnProfilePromptEmoji:
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


class GovrnProfilePromptReject:
    name = StepKeys.GOVRN_PROFILE_PROMPT_REJECT.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "No problem! You are free to join at any time."
        )
        return sent_message, None


class GovrnProfilePromptSuccess:
    name = StepKeys.GOVRN_PROFILE_PROMPT_ACCEPT.value

    async def send(self, message, user_id):
        channel = message.channel
        # Get past guild and add the name
        sent_message = await channel.send(
            "Would you like to reuse your profile data from x guild?"
        )
        return sent_message, None


class GovrnProfilePromptSuccessEmoji:
    name = StepKeys.GOVRN_PROFILE_PROMPT_ACCEPT_EMOJI.value

    @property
    def emojis(self):
        return [YES_EMOJI, NO_EMOJI]

    async def handle_emoji(self, raw_reaction):
        if raw_reaction.emoji.name in self.emojis:
            if raw_reaction.emoji.name == NO_EMOJI:
                return StepKeys.GOVRN_PROFILE_PROMPT_REJECT.value, None
            return StepKeys.GOVRN_PROFILE_PROMPT_ACCEPT.value, None
        raise Exception("Reacted with the wrong emoji")


class GovrnProfilePromptReuse:
    name = StepKeys.GOVRN_PROFILE_REUSE.value

    async def send(self, message, user_id):
        channel = message.channel
        # Get past guild and add the name
        # TODO: Add embed
        sent_message = await channel.send(
            "We added your data to your govrn profile! It lookes like embed!"
        )
        return sent_message, None


### Threads ###

## TODO will circular references cause an infinite recursion
class Onboarding(BaseThread):
    name = ThreadKeys.ONBOARDING.value

    def _govrn_oboard_steps(self):
        success = (
            Step(current=GovrnProfilePromptSuccess())
            .fork(Step(current=GovrnProfilePromptReuse()), self._data_retrival_steps())
            .build()
        )
        reject = Step(current=GovrnProfilePromptReject()).build()
        steps = Step(current=GovrnProfilePrompt()).fork(success, reject)
        return steps.build()

    def _data_retrival_steps(self):
        return (
            Step(current=AddUserTwitterStep())
            .add_next_step(AddUserWalletAddressStep())
            .add_next_step(AddDiscourseStep(guild_id=self.guild_id))
            .add_next_step(CongratsStep(guild_id=self.guild_id))
            .build()
        )

    @property
    def steps(self):
        data_retrival_chain = self._data_retrival_steps.add_next_step(
            self._govrn_oboard_steps()
        ).build()

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
