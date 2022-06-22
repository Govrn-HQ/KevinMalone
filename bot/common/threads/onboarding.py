import discord
from bot.common.airtable import (
    find_user,
    update_user,
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
)


def _handle_skip_emoji(raw_reaction, guild_id):
    if SKIP_EMOJI in raw_reaction.emoji.name:
        return None, True
    raise Exception("Reacted with the wrong emoji")


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
        print(user_id)
        record = await find_user(user_id)
        await update_user(record.get("id"), "display_name", user.display_name)


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
        record_id = await find_user(user_id)
        val = message.content.strip()
        await update_user(record_id, "display_name", val)

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


class AddUserTwitterStep(BaseStep):
    """Step to submit twitter name for the govrn profile"""

    name = StepKeys.ADD_USER_TWITTER.value

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What twitter handle would you like to associate with this guild!"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        record_id = await find_user(message.author.id)
        await update_user(
            record_id, "twitter", message.content.strip().replace("@", "")
        )

    async def handle_emoji(self, raw_reaction):
        return _handle_skip_emoji(raw_reaction, self.guild_id)


# class AddUserWalletAddressStep(BaseStep):
#     """Step to submit wallet address for the govrn profile"""
#
#     name = StepKeys.ADD_USER_WALLET_ADDRESS.value
#
#     def __init__(self, guild_id):
#         super().__init__()
#         self.guild_id = guild_id
#
#     async def send(self, message, user_id):
#         channel = message.channel
#         sent_message = await channel.send(
#           "What Ethereum wallet address would you like to associate with this guild!"
#         )
#         return sent_message, None
#
#     async def save(self, message, guild_id, user_id):
#         record_id = await find_user(message.author.id)
#         await update_user(record_id, "wallet", message.content.strip())
#
#     async def handle_emoji(self, raw_reaction):
#         return _handle_skip_emoji(raw_reaction, self.guild_id)


# class AddDiscourseStep(BaseStep):
#     """Step to submit discourse username for the govrn profile"""
#
#     name = StepKeys.ADD_USER_DISCOURSE.value
#
#     def __init__(self, guild_id):
#         super().__init__()
#         self.guild_id = guild_id
#
#     async def send(self, message, user_id):
#         channel = message.channel
#         sent_message = await channel.send(
#             "What discourse handle would you like to associate with this guild!"
#         )
#         return sent_message, None
#
#     async def save(self, message, guild_id, user_id):
#         record_id = await find_user(message.author.id)
#         await update_user(record_id, "discourse", message.content.strip())
#
#     async def handle_emoji(self, raw_reaction):
#         return _handle_skip_emoji(raw_reaction, self.guild_id)


class CongratsStep(BaseStep):
    """Send congratulations for completing the profile"""

    name = StepKeys.ONBOARDING_CONGRATS.value

    def __init__(self, user_id, guild_id, bot):
        super().__init__()
        self.user_id = user_id
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
            next_step = None
            channel = await self.bot.fetch_channel(raw_reaction.channel_id)
            guild = await self.bot.fetch_guild(self.guild_id)
            await channel.send(
                f"Congratulations on completeing onboarding to {guild.name}"
            )
            govrn_profile = await find_user(self.user_id)
            if govrn_profile:
                next_step = StepKeys.END.value
            return next_step, False
        raise Exception("Reacted with the wrong emoji")

    async def control_hook(self, message, user_id):
        govrn_profile = await find_user(user_id)
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
            return StepKeys.REUSE_GUILD_PROFILE_FOR_GOVRN_PROMPT.value, None
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


# class ReuseGuildProfileForGovrnPrompt(BaseStep):
#     """Ask user whether they want to reuse their guild profile"""
#
#     name = StepKeys.REUSE_GUILD_PROFILE_FOR_GOVRN_PROMPT.value
#
#     def __init__(self, guild_id):
#         self.guild_id = guild_id
#
#     async def send(self, message, user_id):
#         channel = message.channel
#         # Get past guild and add the name
#         record = await get_guild_by_guild_id(self.guild_id)
#         fields = record
#
#         sent_message = await channel.send(
#             "Would you like to reuse your profile data from "
#             f"{fields.get('guild_name')} guild?"
#         )
#         await sent_message.add_reaction(YES_EMOJI)
#         await sent_message.add_reaction(NO_EMOJI)
#         return sent_message, None
#
#
# class ReuseGuildProfileForGovrnEmoji(BaseStep):
#     """Handle user reaction to whether they want to reuse their profile"""
#
#     name = StepKeys.REUSE_GUILD_PROFILE_FOR_GOVRN_EMOJI.value
#
#     def __init__(self, parent):
#         self.parent = parent
#
#     @property
#     def emojis(self):
#         return [YES_EMOJI, NO_EMOJI]
#
#     async def handle_emoji(self, raw_reaction):
#         if raw_reaction.emoji.name in self.emojis:
#             await create_user(self.parent.user_id, constants.Bot.govrn_guild_id)
#             if NO_EMOJI in raw_reaction.emoji.name:
#                 self.parent.guild_id = constants.Bot.govrn_guild_id
#                 return StepKeys.USER_DISPLAY_SUBMIT.value, None
#             return StepKeys.REUSE_GUILD_PROFILE_FOR_GOVRN.value, None
#         raise Exception("Reacted with the wrong emoji")
#
#
# class ReuseGuildProfileForGovrnStep(BaseStep):
#     """Update the user's Govrn profile with information from the current profile"""
#
#     name = StepKeys.REUSE_GUILD_PROFILE_FOR_GOVRN.value
#
#     def __init__(self, guild_id):
#         self.guild_id = guild_id
#
#     async def send(self, message, user_id):
#         channel = message.channel
#
#         fields = await copy_user_profile_to_guild(
#             user_id, self.guild_id, constants.Bot.govrn_guild_id
#         )
#         embed = get_profile_embed_from_profile_fields("Govrn", fields)
#         sent_message = await channel.send(embed=embed)
#         return sent_message, None
#
#
# class CheckForGovrnProfile(BaseStep):
#     """Checks if a user_id already has a Govrn profile"""
#
#     name = StepKeys.CHECK_FOR_GOVRN_PROFILE.value
#
#     def __init__(self, guild_id):
#         self.guild_id = guild_id
#
#     async def send(self, message, user_id):
#         return None, None
#
#     async def control_hook(self, message, user_id):
#         # Check if the user has a Govrn profile, returning
#         # the StepKey for prompting to reuse the Govrn profile
#         # if they do, and the user display prompt if not
#         current_profile = await get_user_record(user_id)
#         if (
#             current_profile is not None
#             and int(constants.Bot.govrn_guild_id) != self.guild_id
#         ):
#             return StepKeys.REUSE_GOVRN_PROFILE_FOR_GUILD_PROMPT.value
#         return StepKeys.USER_DISPLAY_CONFIRM.value
#
#
# class ReuseGovrnProfileForGuildPrompt(BaseStep):
#     """Ask user whether they want to reuse their Govrn profile for the guild"""
#
#     name = StepKeys.REUSE_GOVRN_PROFILE_FOR_GUILD_PROMPT.value
#
#     def __init__(self, guild_id):
#         self.guild_id = guild_id
#
#     async def send(self, message, user_id):
#         channel = message.channel
#         record = await get_guild_by_guild_id(constants.Bot.govrn_guild_id)
#         fields = record
#
#         sent_message = await channel.send(
#             "It looks like you've already completed onboarding to Govrn!"
#             " Nice! Would you like to reuse your profile data"
#             f" for {fields.get('guild_name')} guild?"
#         )
#         await sent_message.add_reaction(YES_EMOJI)
#         await sent_message.add_reaction(NO_EMOJI)
#         return sent_message, None
#
#
# class ReuseGovrnProfileForGuildEmoji(BaseStep):
#     """Handle user reaction to whether they want to reuse their Govrn profile"""
#
#     name = StepKeys.REUSE_GOVRN_PROFILE_FOR_GUILD_EMOJI.value
#
#     def __init__(self, parent):
#         self.parent = parent
#
#     @property
#     def emojis(self):
#         return [YES_EMOJI, NO_EMOJI]
#
#     async def handle_emoji(self, raw_reaction):
#         if raw_reaction.emoji.name in self.emojis:
#             # await create_user(self.parent.user_id, self.parent.guild_id)
#             if NO_EMOJI in raw_reaction.emoji.name:
#                 self.parent.guild_id = constants.Bot.govrn_guild_id
#                 return StepKeys.USER_DISPLAY_CONFIRM.value, None
#             return StepKeys.REUSE_GOVRN_PROFILE_FOR_GUILD.value, None
#         raise Exception("Reacted with the wrong emoji")
#
#
# class ReuseGovrnProfileForGuild(BaseStep):
#     name = StepKeys.REUSE_GOVRN_PROFILE_FOR_GUILD.value
#
#     def __init__(self, guild_id):
#         self.guild_id = guild_id
#
#     async def send(self, message, user_id):
#         channel = message.channel
#         record = await get_guild_by_guild_id(self.guild_id)
#         guild_fields = record
#         guild_name = guild_fields.get("guild_name")
#
#         user_fields = await copy_user_profile_to_guild(
#             user_id, constants.Bot.govrn_guild_id, self.guild_id
#         )
#         embed = get_profile_embed_from_profile_fields(guild_name, user_fields)
#         sent_message = await channel.send(embed=embed)
#
#         return sent_message, None


def get_profile_embed_from_profile_fields(guild_name, fields):
    embed = discord.Embed(
        colour=INFO_EMBED_COLOR,
        description=f"We updated your {guild_name} profile!",
    )
    embed.add_field(name="Display Name", value=fields.get("display_name"))
    embed.add_field(name="Twitter", value=fields.get("twitter"))
    embed.add_field(name="Ethereum Wallet Address", value=fields.get("wallet"))
    # embed.add_field(name="Discourse Handle", value=fields.get("discourse"))

    return embed


# This assumes that a user already has an entry in both from_guild and to_guild
# async def copy_user_profile_to_guild(user_id, from_guild_id, to_guild_id):
#     current_profile = await get_user_record(user_id)
#
#     new_profile = await get_user_record(user_id)
#     record_id = new_profile.get("id")
#     await update_user_display_name(
#         record_id, "display_name", new_profile.get("display_name")
#     )
#     # await update_user(record_id, "twitter", new_profile.get("twitter"))
#     user_record = await update_user(record_id, "discourse", fields.get("discourse"))
#
#     return fields


# Threads #


class Onboarding(BaseThread):
    name = ThreadKeys.ONBOARDING.value

    # def _govrn_oboard_steps(self):
    #     success = (
    #         Step(current=ReuseGuildProfileForGovrnPrompt(guild_id=self.guild_id))
    #         .add_next_step(ReuseGuildProfileForGovrnEmoji(parent=self))
    #         .fork(
    #             [
    #                 Step(current=ReuseGuildProfileForGovrnStep(guild_id=self.guild_id)),
    #                 Step(current=UserDisplaySubmitStep())
    #                 .add_next_step(self._data_retrival_steps().build())
    #                 .build(),
    #             ]
    #         )
    #         .build()
    #     )
    #     reject = Step(current=GovrnProfilePromptReject())
    #     steps = (
    #         Step(current=GovrnProfilePrompt())
    #         .add_next_step(GovrnProfilePromptEmoji())
    #         .fork([success, reject])
    #     )
    #     return steps

    # def _govrn_profile_reuse_steps(self):
    #     reuse_govrn_profile_steps = (
    #         Step(current=ReuseGovrnProfileForGuild(self.guild_id))
    #         .add_next_step(CongratsStep(self.user_id, self.guild_id, self.bot))
    #         .build()
    #     )
    #     create_new_govrn_profile_steps = self._non_govrn_profile_reuse_steps()

    #     reuse_govrn_profile_choice = (
    #         Step(current=ReuseGovrnProfileForGuildPrompt(self.guild_id))
    #         .add_next_step(ReuseGovrnProfileForGuildEmoji(self))
    #         .fork([reuse_govrn_profile_steps, create_new_govrn_profile_steps])
    #     )

    #     return reuse_govrn_profile_choice.build()

    def _data_retrival_steps(self):
        return (
            Step(current=AddUserTwitterStep(guild_id=self.guild_id))
            # .add_next_step(AddUserWalletAddressStep(guild_id=self.guild_id))
            # .add_next_step(AddDiscourseStep(self.guild_id))
            .add_next_step(CongratsStep(self.user_id, self.guild_id, self.bot))
        )

    def _non_govrn_profile_reuse_steps(self):
        data_retrival_steps = self._data_retrival_steps().build()

        custom_user_name_steps = (
            Step(current=UserDisplaySubmitStep())
            .add_next_step(data_retrival_steps)
            .build()
        )

        non_govrn_profile_reuse_steps = (
            Step(current=UserDisplayConfirmationStep(bot=self.bot))
            .add_next_step(UserDisplayConfirmationEmojiStep(bot=self.bot))
            .fork((custom_user_name_steps, data_retrival_steps))
        )

        return non_govrn_profile_reuse_steps.build()

    async def get_steps(self):
        # govrn_reuse_steps = self._govrn_profile_reuse_steps()
        non_govrn_reuse_steps = self._non_govrn_profile_reuse_steps()

        steps = non_govrn_reuse_steps

        return steps.build()
