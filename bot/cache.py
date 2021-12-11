import discord
import json
import logging

from airtable import find_user, update_user, get_user_record
from enum import Enum
from config import Redis, YES_EMOJI, NO_EMOJI, INFO_EMBED_COLOR, get_list_of_emojis
from typing import Dict, Optional

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def build_cache_value(thread, step, guild_id, message_id="", **kwargs):
    return json.dumps(
        {
            "thread": thread,
            "step": step,
            "guild_id": guild_id,
            "message_id": message_id,
            **kwargs,
        }
    )


# enums for thread keys
# enum for step keys
class ThreadKeys(Enum):
    ONBOARDING = "onboarding"
    UPDATE_PROFILE = "update_profile"


class StepKeys(Enum):
    USER_DISPLAY_CONFIRM = "user_display_confirm"
    USER_DISPLAY_CONFIRM_EMOJI = "user_display_confirm_emoji"
    USER_DISPLAY_SUBMIT = "user_display_submit"
    ADD_USER_TWITTER = "add_user_twitter"
    ONBOARDING_CONGRATS = "onboarding_congrats"
    ADD_USER_WALLET_ADDRESS = "add_user_wallet_address"
    ADD_USER_DISCOURSE = "add_user_discourse"
    SELECT_GUILD_EMOJI = "select_guild_emoji"
    USER_UPDATE_FIELD_SELECT = "user_update_select"
    UPDATE_PROFILE_FIELD_EMOJI = "update_profile_field_emoji"
    UPDATE_FIELD = "update_field"
    CONGRATS_UPDATE_FIELD = "congrats_update_field"


class BaseThread:
    def __init__(self, user_id, current_step, message_id, guild_id):
        # Check here that get is not null
        if not current_step:
            raise Exception(f"No step for {current_step}")
        self.user_id = user_id
        self.message_id = message_id
        self.guild_id = guild_id
        self.step = self.find_step(self.steps, current_step)

    def find_step(self, steps, name):
        if steps.current.name == name:
            return steps
        for _, step in steps.next_steps.items():
            steps = self.find_step(step, name)
            if steps:
                return steps
        return None

    async def send(self, message):
        logger.info(f"Send {self.step}")
        if self.step.current.emoji is True:
            await message.channel.send(
                "Please react with one of the above emojis to continue!"
            )
            return
        print("Previous Step")
        print(self.step.previous_step)
        if self.step.previous_step:
            print("Executing Save")
            await self.step.previous_step.save(message, self.guild_id, self.user_id)
        msg, metadata = await self.step.current.send(message, self.user_id)
        if not metadata:
            u = await Redis.get(self.user_id)
            if u:
                metadata = json.loads(u).get("metadata")

        if not self.step.next_steps:
            return await Redis.delete(self.user_id)
        return await Redis.set(
            self.user_id,
            build_cache_value(
                self.name,
                list(self.step.next_steps.values())[0].current.name,
                self.guild_id,
                msg.id,
                metadata=metadata,
            ),
        )

    # Emoji cannot follow emoji
    async def handle_reaction(self, reaction, user):
        from commands import bot

        logger.info(f"Emoji {reaction}")
        # TODO: Add some error handling
        channel = await bot.fetch_channel(reaction.channel_id)
        message = await channel.fetch_message(reaction.message_id)

        if reaction.message_id != self.message_id:
            await channel.send(
                "Emoji reaction on the wrong message., Please react to your most recent message"
            )
            return
        try:
            step_name = await self.step.current.handle_emoji(reaction)
        except Exception as e:
            logger.exception("Fiailed to handle the emoji")
            await channel.send(
                f"In order to move to the following step please react with one of the already existing emojis"
            )
            return

        if not step_name:
            step_name = list(self.step.next_steps.values())[0].current.name
        next_step = self.step.get_next_step(step_name)
        print("Next Step")
        print(next_step)
        print(not next_step)
        if not next_step:
            return await Redis.delete(self.user_id)
        self.step = next_step
        print("Sending message")
        await self.send(message)


class BaseStep:
    emoji = False

    async def save(self, message, guild_id, user_id):
        pass


class UserDisplayConfirmationStep(BaseStep):
    name = StepKeys.USER_DISPLAY_CONFIRM.value
    msg = "Would you like your govern display name to be"

    @property
    def emojis():
        return [YES_EMOJI, NO_EMOJI]

    async def send(self, message, user_id):
        from commands import bot

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
                return StepKeys.USER_DISPLAY_SUBMIT.value
            return StepKeys.ADD_USER_TWITTER.value
        raise Exception("Reacted with the wrong emoji")

    """
    This is where I left off
    TODO: Add guild id to redis value
    then I can upate the appropriate record in
    Discord
    """

    async def save(self, message, guild_id, user_id):
        from commands import bot

        print("Updating display name")
        user = await bot.fetch_user(user_id)
        record_id = await find_user(user_id, guild_id)
        print("record")
        print(message.author.name)
        print(user)
        print(record_id)
        await update_user(record_id, "display_name", user.name)


class UserDisplaySubmitStep(BaseStep):
    name = StepKeys.USER_DISPLAY_SUBMIT.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(f"Updated display name to {message.content}")
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        from commands import bot

        user = await bot.fetch_user(user_id)
        record_id = await find_user(user_id, guild_id)
        await update_user(record_id, "display_name", message.content.strip())


class AddUserTwitterStep(BaseStep):
    name = StepKeys.ADD_USER_TWITTER.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            f"What twitter handle would you like to associate with this guild!"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        record_id = await find_user(message.author.id, guild_id)
        print("saving twitter")
        print(message)
        print(record_id)
        await update_user(
            record_id, "twitter", message.content.strip().replace("@", "")
        )


class AddUserWalletAddressStep(BaseStep):
    name = StepKeys.ADD_USER_WALLET_ADDRESS.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            f"What Ethereum wallet address would you like to associate with this guild!"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        record_id = await find_user(message.author.id, guild_id)
        print("saving wallet")
        print(message)
        print(record_id)
        await update_user(record_id, "wallet", message.content.strip())


class AddDiscourseStep(BaseStep):
    name = StepKeys.ADD_USER_DISCOURSE.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            f"What discourse handle would you like to associate with this guild!"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        record_id = await find_user(message.author.id, guild_id)
        print("saving discourse")
        print(message)
        print(record_id)
        await update_user(record_id, "discourse", message.content.strip())


class CongratsStep(BaseStep):
    name = StepKeys.ONBOARDING_CONGRATS.value

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def send(self, message, user_id):
        from commands import bot

        channel = message.channel
        guild = await bot.fetch_guild(self.guild_id)
        sent_message = await channel.send(
            f"Congratulations on completeing onboading to {guild.name}"
        )
        return sent_message, None


class SelectGuildEmojiStep(BaseStep):
    name = StepKeys.SELECT_GUILD_EMOJI.value
    emoji = True

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    async def handle_emoji(self, raw_reaction):
        # Get reaction that has two
        # Then save the key with the guild id
        from commands import bot

        channel = await bot.fetch_channel(raw_reaction.channel_id)
        message = await channel.fetch_message(raw_reaction.message_id)
        key_vals = await Redis.get(raw_reaction.user_id)
        if not key_vals:
            return
        daos = json.loads(key_vals).get("metadata").get("daos")
        selected_guild_reaction = None
        for reaction in message.reactions:
            if reaction.count >= 2:
                selected_guild_reaction = reaction
                self.cls.guild_id = daos.get(reaction.emoji)
                break
        if not selected_guild_reaction:
            raise Exception("Reacted with the wrong emoji")


# Next step send another message with the current profile
# and the following reactions to update a field
class UserUpdateFieldSelectStep(BaseStep):
    name = StepKeys.USER_UPDATE_FIELD_SELECT.value

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    async def send(self, message, user_id):
        # fetch profile
        # build embed
        # send
        print("fields")
        print(self.cls.guild_id)
        print(user_id)
        fields = await get_user_record(user_id, self.cls.guild_id)
        user = fields.get("fields")
        if not user:
            raise Exception("No user for updating field")
        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description="Please select one of the following fields to update via emoji",
        )
        # Display name
        # twitter
        # wallet
        # discourse
        emojis = get_list_of_emojis(4)
        embed.add_field(
            name=f"Display Name {emojis[0]}", value=user.get("display_name")
        )
        embed.add_field(name=f"Twitter Handle {emojis[1]}", value=user.get("twitter"))
        embed.add_field(
            name=f"Ethereum Wallet Address {emojis[2]}", value=user.get("wallet")
        )
        embed.add_field(
            name=f"Discourse Handle {emojis[3]}", value=user.get("discourse")
        )

        channel = message.channel
        sent_message = await channel.send(embed=embed)
        for emoji in emojis:
            await sent_message.add_reaction(emoji)
        return (
            sent_message,
            {
                emojis[0]: "display_name",
                emojis[1]: "twitter",
                emojis[2]: "wallet",
                emojis[3]: "discourse",
            },
        )


class UpdateProfileFieldEmojiStep(BaseStep):
    name = StepKeys.UPDATE_PROFILE_FIELD_EMOJI.value
    emoji = True

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    async def handle_emoji(self, raw_reaction):
        # Get reaction that has two
        # Then save the key with the guild id
        key_vals = await Redis.get(raw_reaction.user_id)
        if not key_vals:
            return
        values = json.loads(key_vals)
        values["metadata"] = {
            "field": values.get("metadata").get(raw_reaction.emoji.name)
        }
        await Redis.set(
            raw_reaction.user_id,
            build_cache_value(**values),
        )


class UpdateFieldStep(BaseStep):
    name = StepKeys.UPDATE_FIELD.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(f"What value would you like to use instead")
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        key_vals = await Redis.get(user_id)
        if not key_vals:
            return
        metadata = json.loads(key_vals).get("metadata")
        print("Metadata")
        print(metadata)
        field = metadata.get("field")
        if not field:
            raise Exception("No field present to update")
        record_id = await find_user(user_id, guild_id)
        await update_user(record_id, field, message.content.strip())


class CongratsFieldUpdateStep(BaseStep):
    name = StepKeys.CONGRATS_UPDATE_FIELD.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(f"Thank you! Your profile has been updated")
        return sent_message, None


@dataclass
class Step:
    current: BaseStep
    next_steps: Optional[Dict[str, BaseStep]] = field(default_factory=dict)
    previous_step: Optional[BaseStep] = field(default=None)

    def add_next_step(self, step):
        step.previous_step = self.current
        self.next_steps[step.current.name] = step
        return self

    def get_next_step(self, key):
        step = self.next_steps.get(key, "")
        if step == "":
            raise Exception(
                f"Not a valid next step! current {self.current.name} and next: {key}"
            )
        return step


# from message
# check user
# if user has key
# Pass into function that parses and picks the appropriate class
# This class will take the users input and then, store and respond
# Each thread should have a step parser that picks the appropriate step
# And each step should point to the next step
class Onboarding(BaseThread):
    name = ThreadKeys.ONBOARDING.value

    def __init__(self, user_id, current_step, message_id, guild_id):
        # Check here that get is not null
        if not current_step:
            raise Exception(f"No step for {current_step}")
        self.user_id = user_id
        self.message_id = message_id
        self.guild_id = guild_id
        self.step = self.find_step(self.steps, current_step)

    @property
    def steps(self):
        congrats = Step(current=CongratsStep(guild_id=self.guild_id))
        discourse = Step(current=AddDiscourseStep()).add_next_step(congrats)
        fetch_address = Step(current=AddUserWalletAddressStep()).add_next_step(
            discourse
        )
        data_retrival_chain = Step(current=AddUserTwitterStep()).add_next_step(
            fetch_address
        )
        user_display_accept = Step(current=UserDisplaySubmitStep()).add_next_step(
            data_retrival_chain
        )
        user_display_confirm_emoji = (
            Step(current=UserDisplayConfirmationEmojiStep())
            .add_next_step(user_display_accept)
            .add_next_step(data_retrival_chain)
        )
        steps = Step(current=UserDisplayConfirmationStep()).add_next_step(
            user_display_confirm_emoji
        )
        return steps


class UpdateProfile(BaseThread):
    name = ThreadKeys.UPDATE_PROFILE.value

    @property
    def steps(self):
        congrats = Step(current=CongratsFieldUpdateStep())
        update_field_step = Step(current=UpdateFieldStep()).add_next_step(congrats)
        update_profile_field_emoji = Step(
            current=UpdateProfileFieldEmojiStep(cls=self)
        ).add_next_step(update_field_step)
        user_update_field_select = Step(
            current=UserUpdateFieldSelectStep(cls=self)
        ).add_next_step(update_profile_field_emoji)
        steps = Step(current=SelectGuildEmojiStep(cls=self)).add_next_step(
            user_update_field_select
        )
        return steps


def get_thread(user_id, key):
    val = json.loads(key)
    thread = val.get("thread")
    step = val.get("step")
    message_id = val.get("message_id")
    guild_id = val.get("guild_id")
    if thread == ThreadKeys.ONBOARDING.value:
        return Onboarding(user_id, step, message_id, guild_id)
    elif thread == ThreadKeys.UPDATE_PROFILE.value:
        return UpdateProfile(user_id, step, message_id, guild_id)
    raise Exception("Unknown Thread!")
